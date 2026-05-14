# ====================================================
# log_bot.py — بوت اللوج المستقل
# يستقبل رسائل اللوج من study_test_bot
# ويرسل أوامر التحديث عبر HTTP endpoint داخلي
# يتفاعل فقط مع من log=TRUE في الشيت
# cache مستقل للمستخدمين — يدوي فقط
# ====================================================

import os
import time
import threading
import logging
import requests as _requests
import telebot
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

LOG_BOT_TOKEN    = os.environ.get("STUDY_BOT_LOG_TOKEN", "")
SHEET_KEY        = os.environ.get("SHEET_KEY", "")
INTERNAL_PORT    = int(os.environ.get("INTERNAL_PORT", 10001))
INTERNAL_SECRET  = os.environ.get("INTERNAL_SECRET", "study_bot_secret_2025")
INTERNAL_URL     = f"http://localhost:{INTERNAL_PORT}"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("LogBot")

if not LOG_BOT_TOKEN:
    logger.critical("❌ STUDY_BOT_LOG_TOKEN غير موجود — log_bot لن يشتغل")
    exit(1)

bot = telebot.TeleBot(LOG_BOT_TOKEN)

# ─────────────────────────────────────────────────────
# Google Sheets
# ─────────────────────────────────────────────────────
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
try:
    gcreds = os.environ.get("GOOGLE_CREDENTIALS")
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(gcreds), scope)
    client       = gspread.authorize(creds)
    spreadsheet  = client.open_by_key(SHEET_KEY)
    users_sheet  = spreadsheet.worksheet("المستخدمين")
    logger.info("✅ Google Sheets متصل")
except Exception as e:
    logger.critical(f"❌ Google Sheets: {e}")
    users_sheet = None

# ─────────────────────────────────────────────────────
# Cache مستخدمي اللوج — يدوي فقط
# ─────────────────────────────────────────────────────
_log_users: list = []   # IDs من log=TRUE
_loaded = False

def _load_log_users():
    """يقرأ الشيت مرة ويخزن IDs — يُستدعى يدوياً فقط"""
    global _log_users, _loaded
    if not users_sheet:
        return
    try:
        ids = []
        for row in users_sheet.get_all_values()[1:]:
            uid_str = row[2].strip().lstrip("'") if len(row) > 2 else ""
            if uid_str.isdigit() and (row[7].strip().upper() if len(row) > 7 else "") == "TRUE":
                ids.append(int(uid_str))
        _log_users = ids
        _loaded    = True
        logger.info(f"✅ log users: {len(ids)} مستخدم")
    except Exception as e:
        logger.warning(f"_load_log_users: {e}")

def get_log_users() -> list:
    global _loaded
    if not _loaded:
        _load_log_users()
    return _log_users

def is_log_user(uid: int) -> bool:
    return uid in get_log_users()

# ─────────────────────────────────────────────────────
# إرسال أمر للبوت الأساسي عبر HTTP
# ─────────────────────────────────────────────────────
def _send_cmd(cmd: str) -> str:
    """يرسل أمر للبوت الأساسي ويرجع الرد"""
    try:
        resp = _requests.post(
            INTERNAL_URL,
            data={"cmd": cmd, "secret": INTERNAL_SECRET},
            timeout=10
        )
        return resp.text
    except Exception as e:
        return f"❌ فشل الاتصال بالبوت: {e}"

# ─────────────────────────────────────────────────────
# فلتر: فقط مستخدمو اللوج
# ─────────────────────────────────────────────────────
def _log_only(message):
    return is_log_user(message.from_user.id)

def _log_only_call(call):
    return is_log_user(call.from_user.id)

# ─────────────────────────────────────────────────────
# الأوامر
# ─────────────────────────────────────────────────────
@bot.message_handler(commands=["start", "help"], func=_log_only)
def cmd_start(message):
    bot.send_message(message.chat.id,
        "🤖 *بوت اللوج — لوحة التحكم*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "الأوامر المتاحة:\n\n"
        "🔄 *تحديث البوت الأساسي:*\n"
        "`/refresh_texts` — نصوص وأزرار الواجهة\n"
        "`/refresh_users` — صلاحيات المستخدمين\n"
        "`/refresh_ai` — مزودي الذكاء الاصطناعي\n"
        "`/refresh_data` — بيانات الشيت (محاضرات...)\n"
        "`/refresh_all` — تحديث كامل لكل شيء\n\n"
        "🔄 *تحديث بوت اللوج:*\n"
        "`/refresh_log_users` — تحديث قائمة مستخدمي اللوج\n\n"
        "📊 *معلومات:*\n"
        "`/status` — حالة البوت والـ cache\n",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["refresh_texts"], func=_log_only)
def cmd_refresh_texts(message):
    msg = bot.send_message(message.chat.id, "⏳ جاري تحديث النصوص...")
    result = _send_cmd("refresh_texts")
    bot.edit_message_text(result, message.chat.id, msg.message_id)

@bot.message_handler(commands=["refresh_users"], func=_log_only)
def cmd_refresh_users(message):
    msg = bot.send_message(message.chat.id, "⏳ جاري تحديث المستخدمين...")
    result = _send_cmd("refresh_users")
    bot.edit_message_text(result, message.chat.id, msg.message_id)

@bot.message_handler(commands=["refresh_ai"], func=_log_only)
def cmd_refresh_ai(message):
    msg = bot.send_message(message.chat.id, "⏳ جاري تحديث مزودي AI...")
    result = _send_cmd("refresh_ai")
    bot.edit_message_text(result, message.chat.id, msg.message_id)

@bot.message_handler(commands=["refresh_data"], func=_log_only)
def cmd_refresh_data(message):
    msg = bot.send_message(message.chat.id, "⏳ جاري تحديث بيانات الشيت...")
    result = _send_cmd("refresh_data")
    bot.edit_message_text(result, message.chat.id, msg.message_id)

@bot.message_handler(commands=["refresh_all"], func=_log_only)
def cmd_refresh_all(message):
    msg = bot.send_message(message.chat.id, "⏳ جاري التحديث الكامل...")
    result = _send_cmd("refresh_all")
    bot.edit_message_text(result, message.chat.id, msg.message_id)

@bot.message_handler(commands=["refresh_log_users"], func=_log_only)
def cmd_refresh_log_users(message):
    _load_log_users()
    bot.send_message(message.chat.id,
        f"✅ تم تحديث قائمة مستخدمي اللوج\n"
        f"👁 عدد المستخدمين: {len(_log_users)}")

@bot.message_handler(commands=["status"], func=_log_only)
def cmd_status(message):
    msg = bot.send_message(message.chat.id, "⏳ جاري جلب الحالة...")
    result = _send_cmd("status")
    result += f"\n\n*بوت اللوج:*\n👁 مستخدمو اللوج: {len(_log_users)}"
    bot.edit_message_text(result, message.chat.id, msg.message_id,
                          parse_mode="Markdown")

# ─────────────────────────────────────────────────────
# تشغيل
# ─────────────────────────────────────────────────────
def run():
    _load_log_users()
    logger.info("✅ بوت اللوج يعمل")
    bot.infinity_polling()

if __name__ == "__main__":
    run()
