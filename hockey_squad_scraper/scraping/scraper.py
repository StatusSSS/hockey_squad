from __future__ import annotations


from typing import Dict, List, Set, Optional, Any

from bs4 import BeautifulSoup
from tqdm import tqdm

from hockey_squad_scraper.infrastructure.logger import logger
from hockey_squad_scraper.infrastructure.http_client import HttpClient
from hockey_squad_scraper.repositories.teams_repo import TeamsRepo
from hockey_squad_scraper.repositories.countries_repo import CountriesRepo
from hockey_squad_scraper.repositories.players_repo import PlayersRepo
from hockey_squad_scraper.infrastructure.db import DB


class SquadScraper:
    """
    Парсит страничку Flashscore для каждой команды и
    синхронизирует составы с БД через PlayersRepo.
    """

    NATIONAL_TEAM_FLAGS = {
        "fl_02",
        "fl_1",
        "fl_2",
        "fl_290",
        "fl_292",
        "fl_3",
        "fl_4",
        "fl_450",
        "fl_451",
        "fl_453",
        "fl_5",
        "fl_6",
        "fl_7",
        "fl_8",
    }


    def __init__(
        self,
        db: DB,
        http: HttpClient,
        teams_repo: TeamsRepo,
        players_repo: PlayersRepo,
        countries_repo: CountriesRepo,
        cfg,
    ):
        """Добавляет инициализацию зависимостей и конфигурации"""
        self.db = db
        self.http = http
        self.teams = teams_repo
        self.players = players_repo
        self.countries = countries_repo
        self.cfg = cfg


    def run_one_cycle(self) -> None:
        """Добавляет одиночный цикл парсинга всех команд и фиксации изменений"""
        for team in tqdm(self.teams.list_teams(), desc="Teams"):
            try:
                self._process_team(team)
            except Exception as exc:
                logger.opt(exception=exc).warning("Team {} failed – skipped", team['id'])


    def _process_team(self, team: Dict[str, Any]) -> None:
        """Добавляет полный процесс обработки одной команды: загрузка HTML, синхронизация игроков"""
        url = f"https://www.flashscore.com/team/{team['fl_slug']}/{team['fl_id']}/squad/"
        logger.debug("Scrapping: {}", url)
        self.any_updates = False

        soup = BeautifulSoup(self.http.get(url), "lxml")

        is_club = self._determine_if_club(soup)
        self._update_team_national_status(team, is_club)

        current_ids = self._get_current_squad_ids(team["id"], is_club)
        actual_ids: Set[int] = set()


        for table in soup.select("div#overall-all-table div.lineupTable"):
            position = self._get_position_from_table(table)
            if position == "coach":
                continue
            for pdata in self._extract_players_from_table(table, position, team):
                pid = self._process_player_record(pdata, team["id"], is_club)
                if pid:
                    actual_ids.add(pid)


        self._remove_players_not_in_squad(current_ids, actual_ids, is_club)


        if self.any_updates:
            self.db.conn.commit()
            logger.info("Committed squad changes for team {}", team["id"])


    def _determine_if_club(self, soup: BeautifulSoup) -> bool:
        """Добавляет определение, является ли команда клубом или сборной"""
        flag_spans = soup.select("span.breadcrumb__flag")
        if not flag_spans:
            return True
        classes = flag_spans[0].get("class", [])
        return not any(cls in self.NATIONAL_TEAM_FLAGS for cls in classes)

    def _update_team_national_status(self, team: Dict[str, Any], is_club: bool) -> None:
        """Добавляет обновление статуса команды (клуб/сборная) в базе данных"""
        if is_club and team["is_national"] == 1:
            sql = "UPDATE hockey_teams SET is_national=0, updated_at=NOW() WHERE id=%s"
            self.db.cur.execute(sql, (team["id"],))
            self.any_updates = True
            team["is_national"] = 0
        elif not is_club and team["is_national"] == 0:
            sql = "UPDATE hockey_teams SET is_national=1, updated_at=NOW() WHERE id=%s"
            self.db.cur.execute(sql, (team["id"],))
            self.any_updates = True
            team["is_national"] = 1


    def _get_position_from_table(self, table) -> Optional[str]:
        """Добавляет извлечение позиции игрока из заголовка таблицы"""
        header = table.select("div.lineupTable__title")
        if not header:
            return None
        text = header[0].text.strip().lower()
        if "goalkeeper" in text:
            return "goalkeeper"
        if "defender" in text:
            return "defender"
        if "forward" in text:
            return "forward"
        if "coach" in text:
            return "coach"
        return None

    def _extract_players_from_table(
        self, table, position: str, team: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Добавляет извлечение списка игроков из таблицы конкретной позиции"""
        players = []
        for row in table.select("div.lineupTable__row"):
            player = {
                "position": position,
                "team_id": team["id"],
                "number": self._extract_player_number(row),
                **self._extract_player_info(row),
            }
            if player.get("fl_id"):
                players.append(player)
        return players

    def _extract_player_number(self, row) -> Optional[int]:
        """Добавляет извлечение игрового номера игрока"""
        cell = row.select("div.lineupTable__cell.lineupTable__cell--jersey")
        if not cell:
            return None
        text = cell[0].text.strip()
        return int(text) if text.isdigit() else None


    def _extract_player_info(self, row) -> Dict[str, Any]:
        """Добавляет извлечение основной информации об игроке (имя, страна, id)"""
        cell_wrap = row.select("div.lineupTable__cell.lineupTable__cell--player")
        if not cell_wrap:
            return {}
        cell = cell_wrap[0]
        link = cell.select("a")
        if not link:
            return {}
        link = link[0]

        country_id = self._extract_player_country(cell)
        name, first_name, last_name = self._parse_player_name(link.text.strip())

        return {
            "name": name,
            "first_name": first_name,
            "last_name": last_name,
            "fl_id": link["href"].split("/")[-2],
            "fl_slug": link["href"].split("/")[-3],
            "country_id": country_id,
        }

    def _extract_player_country(self, cell) -> Optional[int]:
        """Добавляет извлечение идентификатора страны игрока"""
        flag = cell.select("div.lineupTable__cell--flag")
        if not flag:
            return None
        country_name = flag[0].get("title")
        return self.countries.get_id(country_name)

    @staticmethod
    def _parse_player_name(name: str) -> tuple[str, Optional[str], Optional[str]]:
        """Добавляет парсинг полного имени игрока на краткую форму и отдельные части"""
        if name.count(" ") == 1:
            last, first = name.split()
            return f"{first[0]}. {last}", first, last
        return name, None, None


    def _get_current_squad_ids(self, team_id: int, is_club: bool) -> Set[int]:
        """Добавляет получение текущего набора ID игроков команды из кеша"""
        ids: Set[int] = set()
        for pid, p in self.players.cache.items():
            if is_club and p["team_id"] == team_id:
                ids.add(pid)
            elif not is_club and p["national_team_id"] == team_id:
                ids.add(pid)
        return ids

    def _process_player_record(
        self, pdata: Dict[str, Any], team_id: int, is_club: bool
    ) -> Optional[int]:
        """Добавляет обработку записи игрока: обновление или создание"""
        existing = self.players.find_by_fl_id(pdata["fl_id"])
        if existing:
            return self._update_existing_player(existing, pdata, team_id, is_club)
        return self._create_new_player(pdata, team_id, is_club)


    def _update_existing_player(
        self,
        player: Dict[str, Any],
        new: Dict[str, Any],
        team_id: int,
        is_club: bool,
    ) -> int:
        """Добавляет обновление существующего игрока в репозитории"""
        pid = player["id"]
        fields: Dict[str, Any] = {}


        if is_club and player["team_id"] != team_id:
            fields["team_id"] = team_id
        elif not is_club and player["national_team_id"] != team_id:
            fields["national_team_id"] = team_id


        for f in ("position", "number", "country_id", "first_name", "last_name"):
            if new.get(f) is not None and str(player.get(f)) != str(new[f]):
                fields[f] = new[f]

        if fields:
            self.players.update_player(pid, fields)
            self.any_updates = True
        return pid

    def _create_new_player(
        self, pdata: Dict[str, Any], team_id: int, is_club: bool
    ) -> int:
        """Добавляет создание нового игрока и его переводов в репозитории"""
        base = {
            "name": pdata["name"],
            "fl_id": pdata["fl_id"],
            "position": pdata["position"],
            "number": pdata["number"],
            "country_id": pdata["country_id"],
            "fl_slug": pdata["fl_slug"],
            "first_name": pdata["first_name"],
            "last_name": pdata["last_name"],
            "team_id": team_id if is_club else None,
            "national_team_id": None if is_club else team_id,
        }

        pid = self.players.insert_player(base)
        self.players.insert_translation(
            pid, pdata["name"], pdata["first_name"], pdata["last_name"]
        )
        self.any_updates = True
        return pid


    def _remove_players_not_in_squad(
        self, current_ids: Set[int], actual_ids: Set[int], is_club: bool
    ) -> None:
        """Добавляет удаление игроков, которых больше нет в составе на Flashscore"""
        diff = current_ids - actual_ids
        field = "team_id" if is_club else "national_team_id"
        for pid in diff:
            self.players.clear_team_link(pid, field)
            self.any_updates = True
