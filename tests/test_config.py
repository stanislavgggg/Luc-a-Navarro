from bot.config import _normalize_db_url


def test_railway_urls_get_asyncpg_driver():
    assert _normalize_db_url("postgres://u:p@h:5432/db") == "postgresql+asyncpg://u:p@h:5432/db"
    assert _normalize_db_url("postgresql://u:p@h:5432/db") == "postgresql+asyncpg://u:p@h:5432/db"
    assert _normalize_db_url("sqlite+aiosqlite:///x.db") == "sqlite+aiosqlite:///x.db"
