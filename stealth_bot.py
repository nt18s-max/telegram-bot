import os
import time
import json
import threading
import telebot
import gspread
import requests as _requests
from oauth2client.service_account import ServiceAccountCredentials
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ===================== إعدادات =====================
TOKEN     = os.environ.get("STEALTH_BOT_TOKEN")
SHEET_KEY = os.environ.get("SHEET_KEY")
LOG_TOKEN = os.environ.get("STUDY_BOT_LOG_TOKEN", "")

bot = telebot.TeleBot(TOKEN)

# ===================== Google Sheets =====================
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    gcreds = os.environ.get("GOOGLE_CREDENTIALS")
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(gcreds), scope)
    client           = gspread.authorize(creds)
    spreadsheet      = client.open_by_key(SHEET_KEY)
    users_sheet      = spreadsheet.worksheet("المستخدمين")
    try:    bot_texts_sheet    = spreadsheet.worksheet("bot_texts")
    except: bot_texts_sheet    = None
    try:    ai_providers_sheet = spreadsheet.worksheet("ai_providers")
    except: ai_providers_sheet = None
except Exception as e:
    print(f"❌ خطأ Google Sheets: {e}")
    users_sheet = bot_texts_sheet = ai_providers_sheet = None

# ===================== أعمدة الشيت =====================
COL_ID      = 2   # C
COL_FAKE_AI = 12  # M

# ===================== اللوج =====================
def tg_log(level: str, msg: str):
    if not LOG_TOKEN:
        return
    icons = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌"}
    text  = f"{icons.get(level,'📋')} *[stealth_bot] {level}*\n{msg}"
    try:
        _requests.post(
            f"https://api.telegram.org/bot{LOG_TOKEN}/sendMessage",
            json={"chat_id": LOG_TOKEN, "text": text, "parse_mode": "Markdown"},
            timeout=5
        )
    except:
        pass

# ===================== نصوص البوت — من الشيت فقط =====================
REQUIRED_KEYS = [
    "stealth_welcome",        "stealth_ai_error",        "stealth_no_visible",
    "stealth_set_visible",    "stealth_clear_visible",   "stealth_no_hidden",
    "stealth_no_users",       "stealth_target_set",      "stealth_target_none",
    "stealth_send_fail",      "stealth_help_note",       "stealth_help_owner",
    "stealth_help_user",      "stealth_choose_user",     "stealth_hide_hint",
    "stealth_qhide_hint",     "stealth_setvisible_hint", "stealth_no_target",
    "stealth_ai_off_timed",   "stealth_ai_off_idle",     "stealth_ai_on",
    "stealth_settings_title", "stealth_settings_ai",     "stealth_settings_visible",
    "stealth_ai_on_status",   "stealth_ai_off_status",   "stealth_visible_none",
    "stealth_incoming_msg",   "stealth_refresh_done",    "stealth_reenc_not_found",
    "stealth_media_sent",
]

BOT_TEXTS: dict = {}

def load_bot_texts():
    global BOT_TEXTS
    if not bot_texts_sheet:
        tg_log("ERROR", "stealth_bot: bot_texts_sheet غير متاح")
        return
    try:
        loaded = {}
        for row in bot_texts_sheet.get_all_values():
            if len(row) >= 2 and row[0].strip().startswith("stealth_"):
                val = row[1].strip()
                if val:
                    loaded[row[0].strip()] = val
        BOT_TEXTS = loaded
        missing = [k for k in REQUIRED_KEYS if k not in BOT_TEXTS]
        if missing:
            tg_log("WARNING",
                   "stealth_bot: مفاتيح ناقصة:\n" +
                   "\n".join(f"• `{k}`" for k in missing))
        else:
            tg_log("INFO", f"✅ stealth bot_texts: {len(BOT_TEXTS)} مفتاح")
    except Exception as e:
        tg_log("ERROR", f"stealth_bot load_bot_texts: {e}")

def tx(key, **fmt):
    text = BOT_TEXTS.get(key)
    if text is None:
        tg_log("WARNING", f"stealth_bot: مفتاح مفقود: `{key}`")
        return f"[{key}]"
    if fmt:
        try:
            text = text.format(**fmt)
        except Exception as e:
            tg_log("WARNING", f"stealth_bot: خطأ format `{key}`: {e}")
    return text

# ===================== AI Providers =====================
AI_PROVIDERS = []

def load_ai_providers():
    global AI_PROVIDERS
    AI_PROVIDERS = []
    if not ai_providers_sheet:
        return
    try:
        for row in ai_providers_sheet.get_all_values()[1:]:
            if len(row) < 5:
                continue
            order    = row[0].strip()
            provider = row[1].strip().lower()
            api_key  = row[2].strip()
            model    = row[3].strip().lower()
            enabled  = row[4].strip().upper() == "TRUE"
            if not enabled or not api_key:
                continue
            # معالجة auto
            if model == "auto":
                if provider == "gemini":     model = "gemini-2.0-flash"
                elif provider == "openrouter": model = "mistralai/mistral-7b-instruct:free"
            AI_PROVIDERS.append({
                "order":    int(order) if order.isdigit() else 999,
                "provider": provider,
                "api_key":  api_key,
                "model":    model,
            })
        AI_PROVIDERS.sort(key=lambda x: x["order"])
        tg_log("INFO", f"✅ stealth AI: {len(AI_PROVIDERS)} مزود")
    except Exception as e:
        tg_log("ERROR", f"stealth_bot load_ai_providers: {e}")

def get_ai_reply(text: str) -> str:
    for p in AI_PROVIDERS:
        try:
            if p["provider"] == "gemini":
                url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                       f"{p['model']}:generateContent?key={p['api_key']}")
                payload = {
                    "contents": [{"parts": [{"text": text}]}],
                    "systemInstruction": {"parts": [{"text": "أنت مساعد ذكاء اصطناعي مفيد وبسيط. أجب باختصار وبالعربية."}]},
                    "generationConfig": {"maxOutputTokens": 300, "temperature": 0.7}
                }
                resp = _requests.post(url, json=payload, timeout=30)
                if resp.status_code == 200:
                    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            elif p["provider"] == "openrouter":
                headers = {
                    "Authorization": f"Bearer {p['api_key']}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": p["model"],
                    "messages": [
                        {"role": "system", "content": "أنت مساعد ذكاء اصطناعي مفيد وبسيط. أجب باختصار وبالعربية."},
                        {"role": "user",   "content": text}
                    ],
                    "max_tokens": 300
                }
                resp = _requests.post("https://openrouter.ai/api/v1/chat/completions",
                                      headers=headers, json=payload, timeout=30)
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            tg_log("WARNING", f"stealth AI ({p['provider']}): {e}")
            continue
    return tx("stealth_ai_error")

# ===================== مالك البوت =====================
def get_fake_ai_owners() -> list:
    if not users_sheet:
        return []
    try:
        owners = []
        for row in users_sheet.get_all_values()[1:]:
            if not row or not any(c.strip() for c in row):
                continue
            uid_str  = row[COL_ID].strip().lstrip("'")    if len(row) > COL_ID      else ""
            fake_val = row[COL_FAKE_AI].strip().upper()    if len(row) > COL_FAKE_AI else "FALSE"
            if uid_str.isdigit() and fake_val == "TRUE":
                owners.append(int(uid_str))
        return owners
    except Exception as e:
        tg_log("ERROR", f"stealth get_owners: {e}")
        return []

def is_owner(uid: int) -> bool:
    return uid in get_fake_ai_owners()

# ===================== الحالة =====================
ai_enabled       = {}
disable_timers   = {}
last_activity    = {}
decoded_messages = {}
known_users      = {}
active_target    = None
user_visible     = {}

INACTIVITY_TIMEOUT = 1800
HELP_DELETE_DELAY  = 180

# ===================== التشفير (يدعم العربية وكل Unicode) =====================
def encode_hidden(visible: str, secret: str) -> str:
    """
    يشفر أي نص (عربي/إنجليزي/رموز) داخل رسالة ظاهرة.
    يستخدم 16-bit لكل حرف لضمان دعم Unicode الكامل.
    """
    encoded_chars = []
    for c in secret:
        # 16-bit لدعم العربية وكل Unicode حتى U+FFFF
        bits = format(ord(c), '016b')
        for b in bits:
            encoded_chars.append('\u200b' if b == '0' else '\u200c')
    # فاصل خاص + مؤشر 16-bit
    marker = '\u200f\u200e'  # RTL + LTR mark كفاصل
    return visible + marker + ''.join(encoded_chars)

def decode_hidden(text: str):
    marker = '\u200f\u200e'
    if marker not in text:
        return None
    _, hidden_part = text.split(marker, 1)
    # استخراج الأحرف غير المرئية فقط
    bits = ''
    for c in hidden_part:
        if c == '\u200b':
            bits += '0'
        elif c == '\u200c':
            bits += '1'
    if not bits or len(bits) % 16 != 0:
        return None
    try:
        chars = [bits[i:i+16] for i in range(0, len(bits), 16)]
        result = ''.join(chr(int(b, 2)) for b in chars)
        return result if result else None
    except:
        return None

# ===================== مساعدات =====================
def cancel_timer(chat_id):
    if chat_id in disable_timers:
        disable_timers[chat_id].cancel()
        del disable_timers[chat_id]

def re_enable_ai(chat_id):
    ai_enabled[chat_id] = True

def disable_ai_timed(chat_id, seconds):
    cancel_timer(chat_id)
    ai_enabled[chat_id] = False
    t = threading.Timer(seconds, re_enable_ai, args=[chat_id])
    disable_timers[chat_id] = t
    t.start()

def update_activity(chat_id):
    last_activity[chat_id] = time.time()
    if not ai_enabled.get(chat_id, True):
        cancel_timer(chat_id)
        t = threading.Timer(INACTIVITY_TIMEOUT, re_enable_ai, args=[chat_id])
        disable_timers[chat_id] = t
        t.start()

def register_user(msg):
    chat_id = msg.chat.id
    if not is_owner(chat_id):
        known_users[chat_id] = {
            "name":     msg.from_user.full_name or "مجهول",
            "username": f"@{msg.from_user.username}" if msg.from_user.username else "بدون يوزر",
        }

def re_encode_message(chat_id, message_id, encoded_text):
    key = (chat_id, message_id)
    if key not in decoded_messages:
        return
    elapsed = time.time() - last_activity.get(chat_id, 0)
    if elapsed >= INACTIVITY_TIMEOUT:
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=encoded_text)
        except:
            pass
        decoded_messages.pop(key, None)
    else:
        remaining = INACTIVITY_TIMEOUT - elapsed
        t = threading.Timer(remaining, re_encode_message, args=[chat_id, message_id, encoded_text])
        decoded_messages[key] = (encoded_text, t)
        t.start()

def send_auto_delete(chat_id, text, delay=HELP_DELETE_DELAY, parse_mode="Markdown"):
    try:
        sent = bot.send_message(chat_id, text, parse_mode=parse_mode)
        threading.Timer(delay, lambda: bot.delete_message(chat_id, sent.message_id)).start()
    except Exception as e:
        tg_log("WARNING", f"stealth send_auto_delete: {e}")

def send_help(chat_id, owner=False):
    key  = "stealth_help_owner" if owner else "stealth_help_user"
    text = tx(key, note=tx("stealth_help_note"))
    send_auto_delete(chat_id, text)

def send_settings(chat_id):
    visible    = user_visible.get(chat_id)
    ai_status  = tx("stealth_ai_on_status") if ai_enabled.get(chat_id, True) else tx("stealth_ai_off_status")
    vis_status = f"`{visible}`" if visible else tx("stealth_visible_none")
    text = (
        f"{tx('stealth_settings_title')}\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{tx('stealth_settings_ai',      status=ai_status)}\n"
        f"{tx('stealth_settings_visible', visible=vis_status)}\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📌 {tx('stealth_setvisible_hint')}\n"
        f"📌 {tx('stealth_qhide_hint')}\n"
        "📌 `.clearvisible`"
    )
    send_auto_delete(chat_id, text)

# ===================== إرسال وسائط مشفرة كنص =====================
def encode_media_as_text(file_id: str, file_type: str, caption: str = "") -> str:
    """
    يحول file_id + نوع الوسيط + كابشن إلى نص مشفر.
    الشكل: [MEDIA:نوع:file_id:كابشن]
    """
    raw = f"[MEDIA:{file_type}:{file_id}:{caption}]"
    visible = user_visible.get("_media_visible", ".")  # نقطة كظاهر افتراضي
    return encode_hidden(visible, raw)

def decode_media(secret: str):
    """يفك تشفير الوسيط ويرجع (file_type, file_id, caption) أو None"""
    if not secret.startswith("[MEDIA:") or not secret.endswith("]"):
        return None
    inner = secret[7:-1]
    parts = inner.split(":", 2)
    if len(parts) < 2:
        return None
    file_type = parts[0]
    file_id   = parts[1]
    caption   = parts[2] if len(parts) > 2 else ""
    return file_type, file_id, caption

def send_decoded_media(chat_id, file_type, file_id, caption=""):
    try:
        if file_type == "photo":
            bot.send_photo(chat_id, file_id, caption=caption or None)
        elif file_type == "video":
            bot.send_video(chat_id, file_id, caption=caption or None)
        elif file_type == "audio":
            bot.send_audio(chat_id, file_id, caption=caption or None)
        elif file_type == "voice":
            bot.send_voice(chat_id, file_id, caption=caption or None)
        elif file_type == "document":
            bot.send_document(chat_id, file_id, caption=caption or None)
        else:
            bot.send_document(chat_id, file_id, caption=caption or None)
    except Exception as e:
        tg_log("WARNING", f"stealth send_decoded_media: {e}")

# ===================== /start =====================
@bot.message_handler(commands=["start"])
def handle_start(msg):
    register_user(msg)
    update_activity(msg.chat.id)
    if not is_owner(msg.from_user.id) and ai_enabled.get(msg.chat.id, True):
        bot.send_message(msg.chat.id, tx("stealth_welcome"))

# ===================== نايف حبيبي = إطفاء AI + شروحات =====================
@bot.message_handler(func=lambda m: m.text and m.text.strip() == "نايف حبيبي")
def handle_naif(msg):
    chat_id = msg.chat.id
    owner   = is_owner(msg.from_user.id)
    try:
        bot.delete_message(chat_id, msg.message_id)
    except:
        pass
    # إطفاء AI بالخمول
    cancel_timer(chat_id)
    ai_enabled[chat_id] = False
    t = threading.Timer(INACTIVITY_TIMEOUT, re_enable_ai, args=[chat_id])
    disable_timers[chat_id] = t
    t.start()
    # إرسال الشروحات
    send_help(chat_id, owner=owner)

# ===================== الأوامر النقطية =====================
@bot.message_handler(func=lambda m: m.text and m.text.startswith("."))
def handle_dot_commands(msg):
    register_user(msg)
    update_activity(msg.chat.id)
    text    = msg.text.strip()
    chat_id = msg.chat.id

    def _del():
        try:
            bot.delete_message(chat_id, msg.message_id)
        except:
            pass

    # .. المخفي / الظاهر — تشفير يدوي
    if text.startswith(".. ") and "/" in text:
        content = text[3:].strip()
        parts   = content.split("/", 1)
        secret  = parts[0].strip()
        visible = parts[1].strip()
        if not secret or not visible:
            bot.reply_to(msg, tx("stealth_hide_hint"))
            return
        encoded = encode_hidden(visible, secret)
        _del()
        target = active_target if is_owner(msg.from_user.id) and active_target else chat_id
        bot.send_message(target, encoded)
        return

    # .. المخفي — تشفير تلقائي بالظاهرة الافتراضية
    if text.startswith(".. ") and "/" not in text:
        secret  = text[3:].strip()
        visible = user_visible.get(chat_id)
        if not secret:
            bot.reply_to(msg, tx("stealth_qhide_hint"))
            return
        if not visible:
            bot.reply_to(msg, tx("stealth_no_visible"))
            return
        encoded = encode_hidden(visible, secret)
        _del()
        target = active_target if is_owner(msg.from_user.id) and active_target else chat_id
        bot.send_message(target, encoded)
        return

    # .. (رد على رسالة) — فك التشفير
    if text == ".." and msg.reply_to_message:
        encoded_text = msg.reply_to_message.text or ""
        secret = decode_hidden(encoded_text)
        _del()
        if not secret:
            bot.send_message(chat_id, tx("stealth_no_hidden"))
            return
        # تحقق هل المحتوى وسيط
        media = decode_media(secret)
        if media:
            file_type, file_id, caption = media
            send_decoded_media(chat_id, file_type, file_id, caption)
            # لا نعدّل الرسالة الأصلية بل نرسل الوسيط
        else:
            target_msg_id = msg.reply_to_message.message_id
            try:
                bot.edit_message_text(chat_id=chat_id, message_id=target_msg_id, text=f"🔓 {secret}")
            except:
                pass
            key = (chat_id, target_msg_id)
            if key in decoded_messages:
                _, old_timer = decoded_messages[key]
                old_timer.cancel()
            t = threading.Timer(INACTIVITY_TIMEOUT, re_encode_message,
                                args=[chat_id, target_msg_id, encoded_text])
            decoded_messages[key] = (encoded_text, t)
            t.start()
        return

    # .reenc — إعادة تشفير يدوي
    if text == ".reenc" and msg.reply_to_message:
        target_msg_id = msg.reply_to_message.message_id
        key = (chat_id, target_msg_id)
        _del()
        if key in decoded_messages:
            encoded_text, old_timer = decoded_messages[key]
            old_timer.cancel()
            try:
                bot.edit_message_text(chat_id=chat_id, message_id=target_msg_id, text=encoded_text)
            except:
                pass
            decoded_messages.pop(key, None)
        else:
            send_auto_delete(chat_id, tx("stealth_reenc_not_found"), delay=10)
        return

    # .setvisible النص
    if text.startswith(".setvisible"):
        content = text[11:].strip()
        if not content:
            bot.reply_to(msg, tx("stealth_setvisible_hint"))
            return
        user_visible[chat_id] = content
        _del()
        send_auto_delete(chat_id, tx("stealth_set_visible", text=content), delay=10)
        return

    # .clearvisible
    if text == ".clearvisible":
        user_visible.pop(chat_id, None)
        _del()
        send_auto_delete(chat_id, tx("stealth_clear_visible"), delay=10)
        return

    # .settings
    if text == ".settings":
        _del()
        send_settings(chat_id)
        return

    # .off [دقائق]
    if text.startswith(".off"):
        _del()
        parts = text.split()
        if len(parts) > 1:
            try:    minutes = int(parts[1])
            except: minutes = 30
            disable_ai_timed(chat_id, minutes * 60)
            send_auto_delete(chat_id, tx("stealth_ai_off_timed", minutes=minutes), delay=5)
        else:
            cancel_timer(chat_id)
            ai_enabled[chat_id] = False
            t = threading.Timer(INACTIVITY_TIMEOUT, re_enable_ai, args=[chat_id])
            disable_timers[chat_id] = t
            t.start()
            send_auto_delete(chat_id, tx("stealth_ai_off_idle"), delay=5)
        return

    # .on
    if text == ".on":
        ai_enabled[chat_id] = True
        cancel_timer(chat_id)
        _del()
        send_auto_delete(chat_id, tx("stealth_ai_on"), delay=5)
        return

    # .users — للمالك فقط
    if text == ".users":
        if not is_owner(msg.from_user.id):
            return
        if not known_users:
            bot.reply_to(msg, tx("stealth_no_users"))
            return
        markup = InlineKeyboardMarkup()
        for uid, info in known_users.items():
            markup.add(InlineKeyboardButton(
                f"{info['name']} {info['username']}",
                callback_data=f"stl_target_{uid}"
            ))
        markup.add(InlineKeyboardButton("🚫 إلغاء الاختيار", callback_data="stl_target_none"))
        _del()
        bot.send_message(chat_id, tx("stealth_choose_user"), reply_markup=markup)
        return

# ===================== الوسائط المشفرة (للمالك) =====================
@bot.message_handler(content_types=["photo", "video", "audio", "voice", "document"])
def handle_media(msg):
    """
    المالك يرسل وسيط → يتحول لرسالة نصية مشفرة ويُرسل للـ target
    الكابشن يصبح الرسالة المخفية داخل الوسيط
    """
    if not is_owner(msg.from_user.id):
        return
    if not active_target:
        return

    if msg.photo:
        file_id, ftype = msg.photo[-1].file_id, "photo"
    elif msg.video:
        file_id, ftype = msg.video.file_id, "video"
    elif msg.audio:
        file_id, ftype = msg.audio.file_id, "audio"
    elif msg.voice:
        file_id, ftype = msg.voice.file_id, "voice"
    elif msg.document:
        file_id, ftype = msg.document.file_id, "document"
    else:
        return

    caption  = msg.caption or ""
    visible  = user_visible.get(msg.chat.id, ".")
    raw      = f"[MEDIA:{ftype}:{file_id}:{caption}]"
    encoded  = encode_hidden(visible, raw)

    try:
        bot.delete_message(msg.chat.id, msg.message_id)
    except:
        pass

    bot.send_message(active_target, encoded)
    send_auto_delete(msg.chat.id, tx("stealth_media_sent"), delay=5)

# ===================== /refresh — من بوت اللوج فقط =====================
@bot.message_handler(commands=["refresh"])
def handle_refresh(msg):
    if not is_owner(msg.from_user.id):
        return
    if str(msg.chat.id) != str(LOG_TOKEN):
        return
    try:
        bot.delete_message(msg.chat.id, msg.message_id)
    except:
        pass
    load_bot_texts()
    load_ai_providers()
    send_auto_delete(msg.chat.id, tx("stealth_refresh_done"), delay=10)

# ===================== اختيار المستخدم =====================
@bot.callback_query_handler(func=lambda call: call.data.startswith("stl_target_"))
def handle_target_selection(call):
    global active_target
    if not is_owner(call.from_user.id):
        return
    data = call.data.replace("stl_target_", "")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    if data == "none":
        active_target = None
        bot.send_message(call.message.chat.id, tx("stealth_target_none"))
    else:
        active_target = int(data)
        info     = known_users.get(active_target, {})
        name     = info.get("name", "مجهول")
        username = info.get("username", "")
        bot.send_message(call.message.chat.id,
                         tx("stealth_target_set", name=name, username=username))

# ===================== الرسائل العادية =====================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_message(msg):
    global active_target
    chat_id = msg.chat.id
    update_activity(chat_id)
    register_user(msg)

    # رسائل المالك → للمستخدم المحدد
    if is_owner(msg.from_user.id):
        if active_target:
            try:
                bot.send_message(active_target, msg.text)
            except Exception as e:
                bot.send_message(chat_id, tx("stealth_send_fail", error=str(e)))
        return

    # AI مطفي → للمالك
    if not ai_enabled.get(chat_id, True):
        owners = get_fake_ai_owners()
        info   = known_users.get(chat_id, {})
        name   = info.get("name", "مجهول")
        for oid in owners:
            try:
                # من active_target → بدون header
                if chat_id == active_target:
                    bot.send_message(oid, msg.text)
                else:
                    bot.send_message(oid, tx("stealth_incoming_msg", name=name, text=msg.text))
            except:
                pass
        return

    # رد AI
    threading.Thread(
        target=lambda: bot.send_message(chat_id, get_ai_reply(msg.text)),
        daemon=True
    ).start()

# ===================== تشغيل =====================
def run():
    load_bot_texts()
    load_ai_providers()
    if not AI_PROVIDERS:
        tg_log("WARNING", "stealth_bot: لا يوجد مزود AI نشط")
    tg_log("INFO", "▶️ stealth_bot يعمل")
    bot.infinity_polling()

if __name__ == "__main__":
    run()
