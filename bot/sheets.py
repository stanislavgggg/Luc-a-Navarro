"""Отправка лидов в Google Sheets через веб-приложение Apps Script (apps_script/Code.gs).

Колонки строки совпадают со схемой таблицы «Quiz leads» (timestamp, lead_id, quiz_id, geo, phone,
whatsapp_consent, consent, consent_text_version, utm_*, brand ...). Скрипт сам сопоставляет поля с заголовками
листа, лишние поля отбрасываются, дубликаты по номеру пропускаются.
"""
from __future__ import annotations

import asyncio
import json
import logging

import aiohttp

from .config import Config
from .db import Database

log = logging.getLogger(__name__)

QUIZ_ID = "es_tg_chollos_bot"
_tasks: set[asyncio.Task] = set()  # держим ссылки, иначе фоновые задачи могут быть собраны GC


def lead_row(u, cfg: Config) -> dict:
    """u: строка из таблицы users."""
    answers = {
        "channel": "telegram_bot",
        "source": u.source,
        "telegram_id": u.telegram_id,
        "username": u.username,
        "first_name": u.first_name,
        "phone_valid": bool(u.phone_valid),
    }
    return {
        "timestamp": u.consent_at.isoformat() if u.consent_at else "",
        "lead_id": f"tg_{u.telegram_id}",
        "quiz_id": QUIZ_ID,
        "geo": u.phone_region or "",
        "phone": u.phone_e164,
        "whatsapp_consent": True,
        "answers_json": json.dumps(answers, ensure_ascii=False),
        "consent": True,
        "consent_text_version": u.consent_version or "",
        "utm_source": "telegram",
        "utm_campaign": u.source or "",
        "brand": cfg.brand_name,
        # поля ниже попадут только в запасной лист, если в целевом листе таких заголовков нет
        "telegram_id": u.telegram_id,
        "username": u.username or "",
        "first_name": u.first_name or "",
        "source": u.source or "",
    }


async def post_rows(cfg: Config, rows: list[dict], attempts: int = 3) -> dict | None:
    if not cfg.sheets_webhook_url or not rows:
        return None
    payload = {"secret": cfg.sheets_secret, "rows": rows}
    timeout = aiohttp.ClientTimeout(total=30)
    for attempt in range(1, attempts + 1):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Apps Script отвечает редиректом 302, aiohttp сам его проходит: запись к этому моменту уже выполнена
                async with session.post(cfg.sheets_webhook_url, data=json.dumps(payload), allow_redirects=True) as resp:
                    text = await resp.text()
            data = json.loads(text)
            if data.get("ok"):
                return data
            log.error("sheets webhook отказал: %s", data)
            return None  # ошибка логики (секрет, формат): повторять бессмысленно
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError):
            log.warning("sheets webhook: попытка %s/%s не удалась", attempt, attempts, exc_info=attempt == attempts)
            if attempt < attempts:
                await asyncio.sleep(2 * attempt)
    return None


async def sync_user(db: Database, cfg: Config, telegram_id: int) -> None:
    u = await db.get_user(telegram_id)
    if u is None or not u.phone_e164:
        return
    res = await post_rows(cfg, [lead_row(u, cfg)])
    if res is not None:
        await db.mark_synced([telegram_id])
        log.info("lead synced user=%s added=%s skipped=%s tab=%s", telegram_id, res.get("added"), res.get("skipped"), res.get("tab"))
    else:
        log.error("lead NOT synced user=%s (останется в базе, отправится командой /resync)", telegram_id)


def schedule_sync(db: Database, cfg: Config, telegram_id: int) -> None:
    """Фоновая отправка: человек не ждёт ответа Google."""
    if not cfg.sheets_webhook_url:
        return
    task = asyncio.create_task(sync_user(db, cfg, telegram_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def resync_all(db: Database, cfg: Config, batch: int = 50) -> tuple[int, int]:
    """Отправляет всё, что ещё не ушло. Возвращает (отправлено, не удалось)."""
    pending = await db.unsynced()
    ok = failed = 0
    for i in range(0, len(pending), batch):
        chunk = pending[i : i + batch]
        res = await post_rows(cfg, [lead_row(u, cfg) for u in chunk])
        if res is None:
            failed += len(chunk)
        else:
            await db.mark_synced([u.telegram_id for u in chunk])
            ok += len(chunk)
    return ok, failed
