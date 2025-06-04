from __future__ import annotations

from typing import Dict, Optional, Any
from hockey_squad_scraper.infrastructure.db import DB



class PlayersRepo:
    """
    Держит кэш текущих игроков + all CRUD-операции.
    • При изменениях в базе кэш автоматически обновляется
    """

    def __init__(self, db: DB):
        self.db = db
        self.cache: Dict[int, Dict[str, Any]] = {}
        self.refresh_cache()


    def refresh_cache(self) -> None:
        """Загрузить всех игроков в память (как было в _get_current_players)."""
        sql = """
            SELECT id, team_id, national_team_id, fl_id, position,
                   number, country_id, first_name, last_name
            FROM hockey_players
        """
        self.db.cur.execute(sql)
        self.cache = {row["id"]: row for row in self.db.cur.fetchall()}


    def find_by_fl_id(self, fl_id: str) -> Optional[Dict[str, Any]]:
        """
        Быстрый поиск игрока: сначала в кэше, потом (на всякий случай)
        в базе. Повторяет логику _find_existing_player.
        """
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
        """Обновить произвольные поля игрока."""
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
        """Добавить нового игрока и вернуть его id (как в _create_new_player)."""
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
        """
        Убрать привязку игрока к club/national (как _remove_player_from_squad).
        `field` = 'team_id' или 'national_team_id'.
        """
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
        """
        Добавить строку в hockey_player_translations.
        Аналог куска из _create_new_player.
        """
        sql = """
            INSERT INTO hockey_player_translations
                   (hockey_player_id, locale, title, first_name, last_name, locale_enabled)
            VALUES (%s, 'ru', %s, %s, %s, 1)
        """
        self.db.cur.execute(sql, (player_id, title_ru, first_name, last_name))