from __future__ import annotations

from typing import Dict, Optional, Any
from hockey_squad_scraper.infrastructure.db import DB



class PlayersRepo:
    """
    Репозиторий игроков: хранит кэш и предоставляет CRUD-операции
    """

    def __init__(self, db: DB):
        self.db = db
        self.cache: Dict[int, Dict[str, Any]] = {}
        self.refresh_cache()


    def refresh_cache(self) -> None:
        """Обновляет кэш: загружеает всех игроков из БД в память."""

        sql = """
            SELECT id, team_id, national_team_id, fl_id, position,
                   number, country_id, first_name, last_name
            FROM hockey_players
        """
        self.db.cur.execute(sql)
        self.cache = {row["id"]: row for row in self.db.cur.fetchall()}


    def find_by_fl_id(self, fl_id: str) -> Optional[Dict[str, Any]]:
        """Возвращает игрока по fl_id: сперва ищет в кэше, затем в БД"""

        for row in self.cache.values():
            if row["fl_id"] == fl_id:
                return row

        sql = """
            SELECT id, team_id, national_team_id, fl_id, position, number,
                   country_id, first_name, last_name
            FROM hockey_players
            WHERE fl_id = %s
            LIMIT 1
        """
        self.db.cur.execute(sql, (fl_id,))
        row = self.db.cur.fetchone()
        if row:
            self.cache[row["id"]] = row
        return row


    def update_player(self, player_id: int, fields: Dict[str, Any]) -> None:
        """Обновляет указанные поля игрока и перезагрузить кэш."""

        if not fields:
            return
        sets, values = [], []
        for col, val in fields.items():
            sets.append(f"{col} = %s")
            values.append(val)
        values.append(player_id)
        sql = f"UPDATE hockey_players SET {', '.join(sets)}, updated_at = NOW() WHERE id = %s"
        self.db.cur.execute(sql, values)
        self.refresh_cache()

    def insert_player(self, data: Dict[str, Any]) -> int:
        """Создает нового игрока и вернуть его id."""

        cols, values = zip(*[(k, v) for k, v in data.items() if v is not None])
        placeholders = ", ".join(["%s"] * len(values))
        sql = f"""
            INSERT INTO hockey_players ({', '.join(cols)}, created_at, updated_at)
            VALUES ({placeholders}, NOW(), NOW())
        """
        self.db.cur.execute(sql, values)
        player_id = self.db.cur.lastrowid
        self.refresh_cache()
        return player_id

    def clear_team_link(self, player_id: int, field: str) -> None:
        """Сбросить связь с командой/сборной у игрока."""

        sql = f"UPDATE hockey_players SET {field} = NULL, updated_at = NOW() WHERE id = %s"
        self.db.cur.execute(sql, (player_id,))
        self.refresh_cache()

    def insert_translation(
            self,
            player_id: int,
            title_ru: str,
            first_name: Optional[str],
            last_name: Optional[str],
    ) -> None:
        """Добавляет русскую локализацию имени и фамилии игрока."""

        sql = """
            INSERT INTO hockey_player_translations
                   (hockey_player_id, locale, title, first_name, last_name, locale_enabled)
            VALUES (%s, 'ru', %s, %s, %s, 1)
        """
        self.db.cur.execute(sql, (player_id, title_ru, first_name, last_name))