from __future__ import annotations

from typing import Dict, List, Any
from hockey_squad_scraper.infrastructure.db import DB


class TeamsRepo:
    """Читает список команд"""
    def __init__(self, db: DB):
        self.db = db


    def list_teams(self) -> List[Dict[str, Any]]:
        """Вернуть все команды (club + national)."""
        sql = """
            SELECT t.id               AS id,
                   t.fl_id            AS fl_id,
                   c.id               AS our_primary_competition,
                   t.is_national,
                   t.fl_slug
            FROM hockey_teams t
            LEFT JOIN hockey_team_to_competitions ttc
                   ON ttc.team_id = t.id AND ttc.is_primary = 1
            LEFT JOIN hockey_competitions c ON c.id = ttc.competition_id
        """
        self.db.cur.execute(sql)
        return self.db.cur.fetchall()
