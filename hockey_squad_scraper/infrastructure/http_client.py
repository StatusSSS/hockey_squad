import time
import random
import requests
from typing import Optional

from hockey_squad_scraper.infrastructure.config import Settings
from hockey_squad_scraper.infrastructure.proxies import build
from hockey_squad_scraper.infrastructure.logger import logger

FL_WEB_HEADERS = {
    'accept':
        'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
        'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7,es;q=0.6',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=0, i',
    'referer': 'https://www.flashscore.com/hockey/',
    'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent':
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
}

MAX_RETRIES = 5
INITIAL_DELAY_RANGE = (10, 20)



class HttpClient:
    """
    Мини-обёртка над requests:
      • один метод get()
      • прокси из .env
      • хедеры Flashscore
      • MAX_RETRIES + задержка между запросами
    """

    def __init__(self, cfg: Settings):
        self.cfg: Settings = cfg
        self.proxies: Optional[dict] = build(cfg.proxy_raw)
        delay = random.randint(*INITIAL_DELAY_RANGE)
        logger.info(
            "HttpClient init: proxy {}, initial delay {}s",
            "ON" if self.proxies else "OFF",
            delay,
        )
        time.sleep(delay)

    def get(self, url: str, *, timeout: int = 30) -> str:
        """
        Скачивает HTML как текст.
        • бросает RuntimeError после MAX_RETRIES неудач
        • делает cfg.request_delay паузу ПОСЛЕ успешного запроса
        """
        last_exc: Exception | None = None
        logger.debug("GET {} (timeout={}s)", url, timeout)
        for _ in range(MAX_RETRIES):
            try:
                resp = requests.get(
                    url,
                    timeout=timeout,
                    headers=FL_WEB_HEADERS
                )
                resp.raise_for_status()

                logger.info("{} {}", url, resp.status_code)

                time.sleep(0.05)
                return resp.text
            except Exception as exc:
                last_exc = exc
                logger.warning("GET {} failed (timeout={}s): {}", url, timeout, exc)
                time.sleep(1)

        logger.opt(exception=last_exc).exception("GET {} aborted after {} retries", url, MAX_RETRIES)
        raise RuntimeError(f"GET {url!r} failed") from last_exc