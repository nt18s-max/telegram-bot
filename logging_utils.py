import logging
from datetime import datetime

import requests as _requests

import config

logger = logging.getLogger("StudyTestBot")

_ICONS = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🚨"}


def _get_log_recipient_ids():
    try:
        from sheets.users_repo import get_log_user_ids
        return get_log_user_ids()
    except Exception:
        return []


def send_to_log_bot(text: str, parse_mode: str = "Markdown"):
    if not config.LOG_BOT_TOKEN:
        return
    for uid in _get_log_recipient_ids():
        try:
            _requests.post(
                f"https://api.telegram.org/bot{config.LOG_BOT_TOKEN}/sendMessage",
                json={"chat_id": uid, "text": text, "parse_mode": parse_mode},
                timeout=5,
            )
        except Exception:
            pass


def tg_log(level: str, msg: str, uid: int = None):
    now = datetime.now(config.YEMEN_TZ).strftime("%Y-%m-%d %H:%M:%S")

    user_block = ""
    if uid:
        try:
            from sheets.users_repo import get_user_record
            rec = get_user_record(uid)
            if rec:
                icon = "👑" if rec["owner"] else ("⭐" if rec["admin"] else ("👤" if rec["allowed"] else "❌"))
                ph_line = f"\n📞 {rec['phone']}" if rec["phone"] else ""
                user_block = f"{icon} {rec['name']}\n🆔 `{uid}`{ph_line}\n\n"
        except Exception:
            pass

    text = f"{_ICONS.get(level, '📋')} *{level}*\n`{now}`\n\n{user_block}{msg}"
    send_to_log_bot(text)
    getattr(logger, level.lower(), logger.info)(msg)


def log_info(m, uid=None):
    tg_log("INFO", m, uid)


def log_warning(m, uid=None):
    tg_log("WARNING", m, uid)


def log_error(m, uid=None):
    tg_log("ERROR", m, uid)


def log_critical(m, uid=None):
    tg_log("CRITICAL", m, uid)
