from __future__ import annotations

import time

from hockey_squad_scraper.infrastructure.config import Settings
from hockey_squad_scraper.infrastructure.db import DB
from hockey_squad_scraper.infrastructure.http_client import HttpClient
from hockey_squad_scraper.repositories.countries_repo import CountriesRepo
from hockey_squad_scraper.repositories.players_repo import PlayersRepo
from hockey_squad_scraper.repositories.teams_repo import TeamsRepo
from hockey_squad_scraper.scraping.scraper import SquadScraper
from hockey_squad_scraper.infrastructure.logger import logger




def main() -> None:
    cfg = Settings()


    db = DB(cfg)
    http = HttpClient(cfg)

    teams_repo = TeamsRepo(db)
    players_repo = PlayersRepo(db)
    countries_repo = CountriesRepo(db)

    scraper = SquadScraper(
        db=db,
        http=http,
        teams_repo=teams_repo,
        players_repo=players_repo,
        countries_repo=countries_repo,
        cfg=cfg,
    )

    logger.info("Scraper started - loop delay: {}s", cfg.main_loop_delay)

    while True:
        try:
            scraper.run_one_cycle()
            time.sleep(cfg.main_loop_delay)
        except KeyboardInterrupt:
            logger.info("[STOP] interrupted by user")
            break
        except Exception as exc:
            logger.opt(exception=exc).error("Unhandled exception — sleeping {} s", cfg.error_delay)
            time.sleep(cfg.error_delay)
            db.reconnect()


if __name__ == "__main__":
    main()
