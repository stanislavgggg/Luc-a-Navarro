from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv опционален
    pass

log = logging.getLogger(__name__)

# Версия текста согласия. Меняешь текст согласия в texts.py, увеличь версию:
# в базе будет видно, на какую редакцию согласился каждый человек.
CONSENT_VERSION = "2026-11-v1"


def _csv(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def _normalize_db_url(url: str) -> str:
    # Railway отдаёт postgres:// или postgresql://, а SQLAlchemy async нужен драйвер asyncpg
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: frozenset[int]
    brand_name: str
    privacy_url: str
    persona_name: str
    persona_photo: str
    whatsapp_number: str
    database_url: str
    allowed_regions: frozenset[str] = field(default_factory=frozenset)


def load_config() -> Config:
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN не задан")

    cfg = Config(
        bot_token=token,
        admin_ids=frozenset(int(x) for x in _csv(os.environ.get("ADMIN_IDS", "")) if x.lstrip("-").isdigit()),
        brand_name=os.environ.get("BRAND_NAME", "Chollos Hoy").strip(),
        privacy_url=os.environ.get("PRIVACY_URL", "").strip(),
        persona_name=os.environ.get("PERSONA_NAME", "Lucía").strip(),
        persona_photo=os.environ.get("PERSONA_PHOTO", "assets/persona.jpg").strip(),
        whatsapp_number=os.environ.get("WHATSAPP_NUMBER", "").strip(),
        database_url=_normalize_db_url(os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./data.db").strip()),
        allowed_regions=frozenset(x.upper() for x in _csv(os.environ.get("ALLOWED_REGIONS", ""))),
    )

    if not cfg.privacy_url:
        log.warning("PRIVACY_URL пуст: в тексте согласия не будет ссылки на политику конфиденциальности (нужна по RGPD)")
    if not cfg.admin_ids:
        log.warning("ADMIN_IDS пуст: команды /stats, /export и /broadcast никому не доступны")
    return cfg
