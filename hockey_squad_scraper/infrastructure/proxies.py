import random
from pathlib import Path
from typing import List, Optional

PROXY_FILE = Path(__file__).resolve().parents[1] / "proxies.txt"


def _parse(proxy_raw: str) -> dict[str, str]:
    """'host:port:user:pass' → requests-совместимый dict."""
    host, port, user, pwd = proxy_raw.split(":")
    url = f"http://{user}:{pwd}@{host}:{port}"
    return {"http": url, "https": url}


class ProxyPool:
    """Достаёт случайный прокси из файла и умеет выдавать следующий при ошибке."""

    def __init__(self, file_path: Path | str = PROXY_FILE) -> None:
        self.file_path = Path(file_path)
        self._load()

    def _load(self) -> None:
        with self.file_path.open() as f:
            lines = [l.strip() for l in f if l.strip()]
        if not lines:
            raise RuntimeError(f"{self.file_path} пустой")
        random.shuffle(lines)
        self._pool: List[str] = lines

    def next(self) -> dict[str, str]:
        if not self._pool:
            self._load()
        return _parse(self._pool.pop())
