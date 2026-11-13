from __future__ import annotations

import html
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

OFFERS_PATH = Path(__file__).resolve().parent.parent / "offers.json"
PLACEHOLDER_CODE = "EDITA-ESTE-CODIGO"


def load_offers() -> dict:
    """Читаем при каждом запросе: правишь offers.json, перезапуск не нужен (после деплоя файла)."""
    with OFFERS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def warn_if_placeholder() -> None:
    try:
        offers = load_offers()
    except Exception:
        log.exception("Не удалось прочитать offers.json")
        return
    if offers.get("welcome_coupon", {}).get("code") == PLACEHOLDER_CODE:
        log.warning("offers.json содержит заглушку вместо реального купона: замени её до запуска трафика")


def format_coupon(coupon: dict) -> str:
    parts = [f"🎟️ <b>{html.escape(coupon.get('title', 'Cupón'))}</b>"]
    if coupon.get("code"):
        parts.append(f"Código: <code>{html.escape(coupon['code'])}</code>")
    if coupon.get("description"):
        parts.append(html.escape(coupon["description"]))
    return "\n".join(parts)


def format_deals(deals: list[dict]) -> str:
    blocks = []
    for d in deals:
        lines = [f"🔥 <b>{html.escape(d.get('title', ''))}</b>"]
        if d.get("description"):
            lines.append(html.escape(d["description"]))
        if d.get("code"):
            lines.append(f"Código: <code>{html.escape(d['code'])}</code>")
        if d.get("url"):
            lines.append(html.escape(d["url"]))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
