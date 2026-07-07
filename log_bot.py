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

# ── منافذ باقي البوتات (تحديث شامل حقيقي من زر واحد) ────
CONTACT_INTERNAL_PORT = int(os.environ.get("CONTACT_INTERNAL_PORT", 10002))
STEALTH_INTERNAL_PORT = int(os.environ.get("STEALTH_INTERNAL_PORT", 10003))
CONTACT_INTERNAL_URL  = f"http://localhost:{CONTACT_INTERNAL_PORT}"
STEALTH_INTERNAL_URL  = f"http://localhost:{STEALTH_INTERNAL_PORT}"

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
    try:
        bot_texts_sheet = spreadsheet.worksheet("bot_texts")
    except Exception:
        bot_texts_sheet = None
    logger.info("✅ Google Sheets متصل")
except Exception as e:
    logger.critical(f"❌ Google Sheets: {e}")
    users_sheet = None
    bot_texts_sheet = None

# ─────────────────────────────────────────────────────
# نصوص بوت اللوج — تُقرأ من bot_texts (مفاتيح تبدأ بـ log_)
# ─────────────────────────────────────────────────────
LOG_TEXTS: dict = {}

DEFAULT_LOG_TEXTS = {
    "log_رسالة_البدء": (
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
        "`/status` — حالة البوت والـ cache\n"
    ),
    "log_جاري_تحديث_النصوص":       "⏳ جاري تحديث النصوص...",
    "log_جاري_تحديث_المستخدمين":   "⏳ جاري تحديث المستخدمين...",
    "log_جاري_تحديث_AI":           "⏳ جاري تحديث مزودي AI...",
    "log_جاري_تحديث_البيانات":     "⏳ جاري تحديث بيانات الشيت...",
    "log_جاري_التحديث_الكامل":     "⏳ جاري التحديث الكامل...",
    "log_تم_تحديث_مستخدمي_اللوج":  "✅ تم تحديث قائمة مستخدمي اللوج\n👁 عدد المستخدمين: {count}",
    "log_جاري_جلب_الحالة":         "⏳ جاري جلب الحالة...",
}

def load_log_texts():
    """يقرأ نصوص بوت اللوج من صفحة bot_texts (مفاتيح تبدأ بـ log_) — عربي فقط، بدون لون."""
    global LOG_TEXTS
    if not bot_texts_sheet:
        LOG_TEXTS = dict(DEFAULT_LOG_TEXTS)
        return
    try:
        loaded = {}
        for row in bot_texts_sheet.get_all_values():
            if len(row) >= 2 and row[0].strip().startswith("log_"):
                val = row[1].strip()
                if val:
                    loaded[row[0].strip()] = val
        for k, v in DEFAULT_LOG_TEXTS.items():
            if k not in loaded:
                loaded[k] = v
        LOG_TEXTS = loaded
        logger.info(f"✅ نصوص بوت اللوج محمّلة: {len(LOG_TEXTS)} مفتاح")
    except Exception as e:
        logger.warning(f"load_log_texts: {e}")
        LOG_TEXTS = dict(DEFAULT_LOG_TEXTS)

def ltx(key, **fmt):
    """يجلب نص بوت اللوج ويطبّق format إن وُجد."""
    text = LOG_TEXTS.get(key, DEFAULT_LOG_TEXTS.get(key, key))
    if fmt:
        try:
            text = text.format(**fmt)
        except Exception:
            pass
    return text

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
# إرسال أمر لأي بوت عبر HTTP الداخلي
# ─────────────────────────────────────────────────────
def _send_cmd(cmd: str, url: str = INTERNAL_URL) -> str:
    """يرسل أمر لبوت معيّن (افتراضياً البوت الأساسي) ويرجع الرد"""
    try:
        resp = _requests.post(
            url,
            data={"cmd": cmd, "secret": INTERNAL_SECRET},
            timeout=10
        )
        return resp.text
    except Exception as e:
        return f"❌ فشل الاتصال: {e}"

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
    bot.send_message(message.chat.id, ltx("log_رسالة_البدء"), parse_mode="Markdown")

@bot.message_handler(commands=["refresh_texts"], func=_log_only)
def cmd_refresh_texts(message):
    msg = bot.send_message(message.chat.id, ltx("log_جاري_تحديث_النصوص"))
    load_log_texts()  # تحديث نصوص بوت اللوج نفسه
    r_study   = _send_cmd("refresh_texts", INTERNAL_URL)
    r_contact = _send_cmd("refresh_texts", CONTACT_INTERNAL_URL)
    r_stealth = _send_cmd("refresh_texts", STEALTH_INTERNAL_URL)
    result = (f"*البوت الرئيسي:*\n{r_study}\n\n"
              f"*بوت التواصل:*\n{r_contact}\n\n"
              f"*بوت ستيلث:*\n{r_stealth}")
    bot.edit_message_text(result, message.chat.id, msg.message_id, parse_mode="Markdown")

@bot.message_handler(commands=["refresh_users"], func=_log_only)
def cmd_refresh_users(message):
    msg = bot.send_message(message.chat.id, ltx("log_جاري_تحديث_المستخدمين"))
    result = _send_cmd("refresh_users")
    bot.edit_message_text(result, message.chat.id, msg.message_id)

@bot.message_handler(commands=["refresh_ai"], func=_log_only)
def cmd_refresh_ai(message):
    msg = bot.send_message(message.chat.id, ltx("log_جاري_تحديث_AI"))
    r_study   = _send_cmd("refresh_ai", INTERNAL_URL)
    r_stealth = _send_cmd("refresh_ai", STEALTH_INTERNAL_URL)
    result = f"*البوت الرئيسي:*\n{r_study}\n\n*بوت ستيلث:*\n{r_stealth}"
    bot.edit_message_text(result, message.chat.id, msg.message_id, parse_mode="Markdown")

@bot.message_handler(commands=["refresh_data"], func=_log_only)
def cmd_refresh_data(message):
    msg = bot.send_message(message.chat.id, ltx("log_جاري_تحديث_البيانات"))
    result = _send_cmd("refresh_data")
    bot.edit_message_text(result, message.chat.id, msg.message_id)

@bot.message_handler(commands=["refresh_all"], func=_log_only)
def cmd_refresh_all(message):
    msg = bot.send_message(message.chat.id, ltx("log_جاري_التحديث_الكامل"))
    load_log_texts()  # تحديث نصوص بوت اللوج نفسه
    _load_log_users()  # تحديث مستخدمي اللوج أيضاً ضمن التحديث الشامل
    r_study   = _send_cmd("refresh_all", INTERNAL_URL)
    r_contact = _send_cmd("refresh_all", CONTACT_INTERNAL_URL)
    r_stealth = _send_cmd("refresh_all", STEALTH_INTERNAL_URL)
    result = (f"*البوت الرئيسي:*\n{r_study}\n\n"
              f"*بوت التواصل:*\n{r_contact}\n\n"
              f"*بوت ستيلث:*\n{r_stealth}")
    bot.edit_message_text(result, message.chat.id, msg.message_id, parse_mode="Markdown")

@bot.message_handler(commands=["refresh_log_users"], func=_log_only)
def cmd_refresh_log_users(message):
    _load_log_users()
    bot.send_message(message.chat.id, ltx("log_تم_تحديث_مستخدمي_اللوج", count=len(_log_users)))

@bot.message_handler(commands=["status"], func=_log_only)
def cmd_status(message):
    msg = bot.send_message(message.chat.id, ltx("log_جاري_جلب_الحالة"))
    r_study   = _send_cmd("status", INTERNAL_URL)
    r_contact = _send_cmd("status", CONTACT_INTERNAL_URL)
    r_stealth = _send_cmd("status", STEALTH_INTERNAL_URL)
    result = f"{r_study}\n\n{r_contact}\n\n{r_stealth}\n\n*بوت اللوج:*\n👁 مستخدمو اللوج: {len(_log_users)}"
    bot.edit_message_text(result, message.chat.id, msg.message_id,
                          parse_mode="Markdown")

# ─────────────────────────────────────────────────────
# تشغيل
# ─────────────────────────────────────────────────────
def run():
    load_log_texts()
    _load_log_users()
    logger.info("✅ بوت اللوج يعمل")
    bot.infinity_polling()

if __name__ == "__main__":
    run()
