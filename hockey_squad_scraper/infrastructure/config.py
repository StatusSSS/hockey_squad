from dataclasses import dataclass
from dotenv import load_dotenv
from typing import Tuple
import os

load_dotenv()

@dataclass(frozen=True)
class Settings:
    db_host: str = os.getenv("DB_HOST")
    db_port: int = int(os.getenv("DB_PORT", 3306))
    db_user: str = os.getenv("DB_USER")
    db_pass: str = os.getenv("DB_PASS")
    db_name: str = os.getenv("DB_NAME")
    db_ssl_ca: str | None = os.getenv("DB_SSL_CA")

    initial_delay_range: Tuple[int, int] = (
        int(os.getenv("INITIAL_DELAY_MIN")),
        int(os.getenv("INITIAL_DELAY_MAX")),
    )
    request_delay: float = 1
    error_delay: int = 60
    main_loop_delay: int = 3600
    max_retries: int = 5



