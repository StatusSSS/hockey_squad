import random
import time
from typing import Optional

import requests
from requests.exceptions import ProxyError, ConnectTimeout, SSLError, HTTPError, ReadTimeout

from hockey_squad_scraper.infrastructure.config import Settings
from hockey_squad_scraper.infrastructure.proxies import ProxyPool
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


class HttpClient:
    """
    GET с прокси-ротацией:
    """

    def __init__(self, cfg: Settings, proxy_pool: Optional[ProxyPool] = None) -> None:
        self.cfg = cfg
        self.pool = proxy_pool or ProxyPool()
        self.proxies = self.pool.next()
        delay = random.randint(*self.cfg.initial_delay_range)
        io, hi = self.cfg.initial_delay_range
        if io < 0 or hi < 0 or io > hi:
            raise ValueError("Initial_delay_range должен быть парой неотрицательных чисел MIN <= MAX")
        logger.info("Proxy ON, initial delay {}s", delay)
        time.sleep(delay)

    def _rotate_proxy(self) -> None:
        self.proxies = self.pool.next()
        logger.info("Switched proxy → {}", self.proxies["http"])

    def get(self, url: str, *, timeout: int = 30) -> str:
        last_exc: Exception | None = None
        attempts_left = self.cfg.max_retries

        while attempts_left:
            logger.debug("GET {} via {} (timeout={}s)", url, self.proxies["http"], timeout)
            try:
                resp = requests.get(
                    url,
                    timeout=timeout,
                    headers=FL_WEB_HEADERS,
                )
                resp.raise_for_status()
                logger.info("{} {}", url, resp.status_code)
                time.sleep(self.cfg.request_delay)
                return resp.text

            except (ProxyError, ConnectTimeout, SSLError, HTTPError, ReadTimeout) as exc:
                last_exc = exc
                logger.warning("Proxy failed: {} → rotating", exc)
                self._rotate_proxy()
                attempts_left -= 1
                time.sleep(1)

        logger.opt(exception=last_exc).exception(
            "GET {} aborted after {} retries", url, self.cfg.max_retries
        )
        raise RuntimeError(f"GET {url!r} failed") from last_exc
