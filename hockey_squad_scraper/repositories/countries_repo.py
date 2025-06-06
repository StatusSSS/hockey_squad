from __future__ import annotations

from typing import Dict, Optional
from hockey_squad_scraper.infrastructure.db import DB


class CountriesRepo:
    def __init__(self, db: DB):
        self.db = db
        self.map: Dict[str, int] = {}
        self.refresh()

    def refresh(self) -> None:
        """Обновитляет кэш стран из таблицы `countries`."""
        sql = "SELECT id, common_title FROM countries"
        self.db.cur.execute(sql)
        self.map = {row["common_title"]: row["id"] for row in self.db.cur.fetchall()}

    def get_id(self, title: str) -> Optional[int]:
        """Возвращает id страны по названию или None, если не найдено."""
        return self.map.get(title)
