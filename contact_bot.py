# ====================================================
# contact_bot.py — بوت التواصل
# ====================================================
import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import os
import gspread
from google.oauth2.service_account import Credentials

from telegram import Update, BotCommand, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler,
)

load_dotenv()

# ── إعدادات ───────────────────────────────────────────
CONTACT_BOT_TOKEN = os.getenv("CONTACT_BOT_TOKEN")
DB_FILE           = "contact_bot_data.json"
TIMEZONE          = "Asia/Riyadh"

logging.basicConfig(level=logging.INFO)
NAME, MESSAGE = range(2)

# ── النصوص الافتراضية ─────────────────────────────────
DEFAULT_TEXTS = {
    "welcome":            "أهلاً وسهلاً! 😊 وصلت الصح، اكتب لنا وبنرد عليك بأسرع وقت ممكن!\n\nما اسمك الكريم؟",
    "ask_message":        "شكراً {name} 😊\n\nاكتب رسالتك كاملة وسنوصلها فوراً:",
    "sent_success":       "تم استلام رسالتك بنجاح ✅\nفريقنا سيرد عليك في أقرب وقت ممكن، شكراً لصبرك! 🙏",
    "away_reply":         "شكراً على تواصلك! 🙏\nنحن حالياً غير متاحين، لكن رسالتك وصلتنا وسنرد عليك {return_time}",
    "blocked":            "عذراً، لا يمكنك إرسال رسائل حالياً.",
    "cancel":             "تم إلغاء الرسالة 👍\nإذا احتجت شيء اكتب /start",
    "reply_received":     "📨 رد من الإدارة:\n\n{message}",
    "block_success":      "✅ تم حظر المستخدم {user_id}",
    "unblock_success":    "✅ تم فك حظر المستخدم {user_id}",
    "already_blocked":    "⚠️ هذا المستخدم محظور مسبقاً",
    "not_blocked":        "⚠️ هذا المستخدم غير محظور",
    "away_on":            "✅ وضع الغياب مفعّل. وقت الرجوع: {return_time}",
    "away_off":           "✅ تم إيقاف وضع الغياب",
    "reply_sent":         "✅ تم إرسال الرد للمستخدم!",
    "reply_usage":        "الاستخدام: /reply [user_id] [الرسالة]",
    "stats_text": (
        "📊 إحصائيات البوت\n"
        "━━━━━━━━━━━━━━\n"
        "📅 اليوم: {today} رسالة\n"
        "📆 هذا الأسبوع: {week} رسالة\n"
        "🗓️ هذا الشهر: {month} رسالة\n"
        "📬 الإجمالي: {total} رسالة"
    ),
    "owner_notification": (
        "📩 رسالة تواصل جديدة!\n"
        "━━━━━━━━━━━━━━\n"
        "👤 الاسم: {name}\n"
        "🔗 الحساب: {profile_link}\n"
        "📱 ID: {user_id}\n"
        "⏰ الوقت: {time}\n"
        "━━━━━━━━━━━━━━\n"
        "💬 الرسالة:\n{message}\n"
        "━━━━━━━━━━━━━━\n"
        "🔁 للرد: /reply {user_id} رسالتك"
    ),
}

# ── نصوص ثنائية اللغة (ar/en) ─────────────────────────
# يُملأ من load_texts()، المفتاح = اسم النص، القيمة = {"ar": ..., "en": ...}
TEXTS_BILINGUAL: dict[str, dict] = {}

# ── TEXTS أحادي اللغة (للتوافق مع باقي الكود) ───────────
TEXTS: dict[str, str] = {}

# ── ألوان الأزرار من عمود D في الشيت ──────────────────
# القيم المقبولة: danger (أحمر)، success (أخضر)، primary (أزرق)، فارغ (شفاف/افتراضي)
BUTTON_STYLES: dict[str, str] = {}
_VALID_STYLES = {"danger", "success", "primary"}

# ── لغة كل مستخدم ─────────────────────────────────────
user_lang: dict[int, str] = {}

def _get_text(key: str, lang: str = "ar") -> str:
    """يجلب النص بالعربي أو الإنجليزي مع fallback للافتراضي."""
    if key in TEXTS_BILINGUAL:
        entry = TEXTS_BILINGUAL[key]
        text = entry.get(lang) or entry.get("ar") or ""
        if text:
            return text
    # fallback → القيمة الأحادية اللغة القديمة
    if key in TEXTS:
        return TEXTS[key]
    # fallback → الافتراضي
    return DEFAULT_TEXTS.get(key, key)

def tx(key: str, uid: int = None, **fmt) -> str:
    """اختصار: يجلب النص بلغة المستخدم ويطبّق format إن وُجد."""
    lang = user_lang.get(uid, "ar") if uid else "ar"
    text = _get_text(key, lang)
    if fmt:
        try:
            text = text.format(**fmt)
        except Exception:
            pass
    return text

# ── تحميل النصوص من الشيت ─────────────────────────────
def load_texts() -> None:
    """
    يقرأ من صفحة bot_texts:
      العمود A = المفتاح
      العمود B = النص العربي
      العمود C = النص الإنجليزي (اختياري)
      العمود D = لون الزر (danger/success/primary/فارغ)

    يملأ TEXTS_BILINGUAL و TEXTS و BUTTON_STYLES.
    """
    global TEXTS_BILINGUAL, TEXTS, BUTTON_STYLES
    try:
        creds_json = os.getenv("GOOGLE_CREDENTIALS")
        sheet_key  = os.getenv("SHEET_KEY")
        creds = Credentials.from_service_account_info(
            json.loads(creds_json),
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )
        ws   = gspread.authorize(creds).open_by_key(sheet_key).worksheet("bot_texts")
        rows = ws.get_all_values()

        bilingual = {}
        mono      = {}
        styles    = {}

        for row in rows:
            # نتجاهل صفوف الهيدر أو الفارغة
            if not row or not row[0].strip():
                continue
            key    = row[0].strip()
            ar_val = row[1].strip() if len(row) > 1 else ""
            en_val = row[2].strip() if len(row) > 2 else ""
            # عمود D — لون الزر (اختياري)
            style  = row[3].strip().lower() if len(row) > 3 else ""

            # نخزّن فقط المفاتيح المعروفة لبوت التواصل
            if key not in DEFAULT_TEXTS:
                continue

            bilingual[key] = {
                "ar": ar_val or DEFAULT_TEXTS.get(key, ""),
                "en": en_val or ar_val or DEFAULT_TEXTS.get(key, ""),
            }
            # TEXTS الأحادي → العربي (للتوافق مع الكود القديم)
            mono[key] = ar_val or DEFAULT_TEXTS.get(key, "")
            # حفظ اللون فقط إذا كان صالحاً
            if style in _VALID_STYLES:
                styles[key] = style

        # أي مفتاح غير موجود في الشيت → القيمة الافتراضية
        for k, v in DEFAULT_TEXTS.items():
            if k not in bilingual:
                bilingual[k] = {"ar": v, "en": v}
            if k not in mono:
                mono[k] = v

        TEXTS_BILINGUAL = bilingual
        TEXTS           = mono
        BUTTON_STYLES   = styles
        print(f"✅ نصوص بوت التواصل تحملت من bot_texts ({len(bilingual)} مفتاح، {len(styles)} زر ملوّن)")

    except Exception as e:
        print(f"⚠️ خطأ في تحميل نصوص بوت التواصل: {e} — سيتم استخدام الافتراضي")
        TEXTS_BILINGUAL = {k: {"ar": v, "en": v} for k, v in DEFAULT_TEXTS.items()}
        TEXTS           = dict(DEFAULT_TEXTS)
        BUTTON_STYLES   = {}

# ── Google Sheets — جلب الأدمن ────────────────────────
def _get_users_sheet():
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    sheet_key  = os.getenv("SHEET_KEY")
    creds = Credentials.from_service_account_info(
        json.loads(creds_json),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    return gspread.authorize(creds).open_by_key(sheet_key).worksheet("المستخدمين")

def get_contact_bot_admins() -> list:
    """يجلب IDs اللي عندهم TRUE في عمود bot 2 (I) من شيت المستخدمين."""
    try:
        rows = _get_users_sheet().get_all_values()
        admins = []
        empty_streak = 0
        for row in rows[1:]:
            if not row or not any(c.strip() for c in row):
                empty_streak += 1
                if empty_streak >= 5:
                    break
                continue
            empty_streak = 0
            uid_str  = row[2].strip().lstrip("'") if len(row) > 2 else ""
            bot2_val = row[8].strip().upper()      if len(row) > 8 else "FALSE"
            if uid_str.isdigit() and bot2_val == "TRUE":
                admins.append(int(uid_str))
        return admins
    except Exception as e:
        logging.warning(f"get_contact_bot_admins خطأ: {e}")
        return []

# ── DB ────────────────────────────────────────────────
def load_db() -> dict:
    if not os.path.exists(DB_FILE):
        return {"blocked": [], "messages": [], "away": {"active": False, "return_time": ""}}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def now_str() -> str:
    return datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M")

def is_admin(update: Update) -> bool:
    return update.message.chat_id in get_contact_bot_admins()

def _make_button(text_key: str, label: str) -> KeyboardButton:
    """ينشئ KeyboardButton مع لون من الشيت إذا وُجد."""
    style = BUTTON_STYLES.get(text_key, "")
    if style in _VALID_STYLES:
        return KeyboardButton(label, style=style)
    return KeyboardButton(label)

def admin_keyboard():
    return ReplyKeyboardMarkup([
        [_make_button("reply_sent",      "↩️ /reply"),
         _make_button("block_success",   "🚫 /block")],
        [_make_button("unblock_success", "✅ /unblock"),
         _make_button("stats_text",      "📊 /stats")],
        [_make_button("away_on",         "🌙 /away"),
         _make_button("away_off",        "☀️ /back")],
    ], resize_keyboard=True)

# ── Handlers ──────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if is_admin(update):
        await update.message.reply_text("👑 لوحة التحكم:", reply_markup=admin_keyboard())
        return ConversationHandler.END
    db = load_db()
    if uid in db["blocked"]:
        await update.message.reply_text(tx("blocked", uid))
        return ConversationHandler.END
    await update.message.reply_text(tx("welcome", uid))
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    db  = load_db()
    if uid in db["blocked"]:
        await update.message.reply_text(tx("blocked", uid))
        return ConversationHandler.END
    context.user_data["name"] = update.message.text
    await update.message.reply_text(tx("ask_message", uid, name=update.message.text))
    return MESSAGE

async def get_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db   = load_db()
    user = update.message.from_user
    uid  = user.id
    name = context.user_data.get("name", "غير معروف")
    msg  = update.message.text
    time_str = now_str()

    db["messages"].append({
        "user_id":  uid,
        "username": user.username or "",
        "name":     name,
        "message":  msg,
        "time":     time_str,
    })
    save_db(db)

    profile_link = (
        f"[@{user.username}](t.me/{user.username})"
        if user.username
        else f"[فتح الحساب](tg://user?id={uid}) _(بدون يوزر)_"
    )

    notification = tx("owner_notification").format(
        name=name, profile_link=profile_link,
        user_id=uid, time=time_str, message=msg,
    )

    for admin_id in get_contact_bot_admins():
        try:
            await context.bot.send_message(
                chat_id=admin_id, text=notification, parse_mode="Markdown")
        except Exception as e:
            logging.warning(f"فشل إرسال إشعار لـ {admin_id}: {e}")

    if db["away"]["active"]:
        await update.message.reply_text(
            tx("away_reply", uid, return_time=db["away"]["return_time"]))
    else:
        await update.message.reply_text(tx("sent_success", uid))
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    await update.message.reply_text(tx("cancel", uid))
    return ConversationHandler.END

async def block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not context.args:
        await update.message.reply_text("الاستخدام: /block [user_id]")
        return
    user_id = int(context.args[0])
    db = load_db()
    if user_id in db["blocked"]:
        await update.message.reply_text(TEXTS["already_blocked"])
        return
    db["blocked"].append(user_id)
    save_db(db)
    await update.message.reply_text(TEXTS["block_success"].format(user_id=user_id))

async def unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not context.args:
        await update.message.reply_text("الاستخدام: /unblock [user_id]")
        return
    user_id = int(context.args[0])
    db = load_db()
    if user_id not in db["blocked"]:
        await update.message.reply_text(TEXTS["not_blocked"])
        return
    db["blocked"].remove(user_id)
    save_db(db)
    await update.message.reply_text(TEXTS["unblock_success"].format(user_id=user_id))

async def set_away(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    return_time = " ".join(context.args) if context.args else "قريباً"
    db = load_db()
    db["away"] = {"active": True, "return_time": return_time}
    save_db(db)
    await update.message.reply_text(TEXTS["away_on"].format(return_time=return_time))

async def remove_away(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    db = load_db()
    db["away"] = {"active": False, "return_time": ""}
    save_db(db)
    await update.message.reply_text(TEXTS["away_off"])

async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if len(context.args) < 2:
        await update.message.reply_text(TEXTS["reply_usage"])
        return
    user_id   = int(context.args[0])
    reply_msg = " ".join(context.args[1:])
    await context.bot.send_message(
        chat_id=user_id,
        text=TEXTS["reply_received"].format(message=reply_msg),
    )
    await update.message.reply_text(TEXTS["reply_sent"])

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    db        = load_db()
    msgs      = db["messages"]
    now       = datetime.now(ZoneInfo(TIMEZONE))
    today     = now.strftime("%Y-%m-%d")
    week_ago  = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    await update.message.reply_text(TEXTS["stats_text"].format(
        today=sum(1 for m in msgs if m["time"][:10] == today),
        week =sum(1 for m in msgs if m["time"][:10] >= week_ago),
        month=sum(1 for m in msgs if m["time"][:10] >= month_ago),
        total=len(msgs),
    ))

# ── تشغيل ─────────────────────────────────────────────
def run():
    load_texts()

    async def post_init(application):
        await application.bot.set_my_commands([
            BotCommand("start",  "ارسل رسالة"),
            BotCommand("cancel", "إلغاء الرسالة"),
        ])

    app = ApplicationBuilder().token(CONTACT_BOT_TOKEN).post_init(post_init).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("reply",   reply_to_user))
    app.add_handler(CommandHandler("block",   block_user))
    app.add_handler(CommandHandler("unblock", unblock_user))
    app.add_handler(CommandHandler("away",    set_away))
    app.add_handler(CommandHandler("back",    remove_away))
    app.add_handler(CommandHandler("stats",   stats))

    print("✅ بوت التواصل شغال...")
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app.run_polling()

if __name__ == "__main__":
    run()
