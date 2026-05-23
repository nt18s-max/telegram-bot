import os
import time
import threading
import telebot

# ===================== إعدادات =====================
TOKEN = os.environ.get("STEALTH_BOT_TOKEN")
OWNER_ID = int(os.environ.get("STEALTH_OWNER_ID", "0"))  # آيدي حسابك
SECRET_PREFIX = "."  # الأوامر السرية تبدأ بنقطة مثل .off 30

bot = telebot.TeleBot(TOKEN)

# ===================== الحالة =====================
ai_enabled = {}       # {chat_id: bool}
disable_timers = {}   # {chat_id: Timer}
last_activity = {}    # {chat_id: timestamp} — لإعادة التشفير بعد 30 دقيقة خمول
decoded_messages = {} # {(chat_id, message_id): (original_encoded, timer)}

INACTIVITY_TIMEOUT = 1800  # 30 دقيقة بالثواني
HELP_DELETE_DELAY = 180    # 3 دقائق

# ===================== التشفير =====================
def encode_hidden(visible: str, secret: str) -> str:
    binary = ''.join(format(ord(c), '08b') for c in secret)
    hidden = binary.replace('0', '\u200b').replace('1', '\u200c')
    return visible + '\u200f' + hidden

def decode_hidden(text: str):
    if '\u200f' not in text:
        return None
    _, hidden_part = text.split('\u200f', 1)
    binary = hidden_part.replace('\u200b', '0').replace('\u200c', '1')
    chars = [binary[i:i+8] for i in range(0, len(binary), 8)]
    try:
        result = ''.join(chr(int(b, 2)) for b in chars if len(b) == 8)
        return result if result else None
    except Exception:
        return None

# ===================== مساعدات =====================
def is_owner(msg):
    return msg.from_user.id == OWNER_ID

def set_ai(chat_id, enabled):
    ai_enabled[chat_id] = enabled

def cancel_timer(chat_id):
    if chat_id in disable_timers:
        disable_timers[chat_id].cancel()
        del disable_timers[chat_id]

def re_enable_ai(chat_id):
    ai_enabled[chat_id] = True
    print(f"✅ AI أُعيد تفعيله تلقائياً للـ chat_id: {chat_id}")

def disable_ai_timed(chat_id, seconds):
    cancel_timer(chat_id)
    ai_enabled[chat_id] = False
    t = threading.Timer(seconds, re_enable_ai, args=[chat_id])
    disable_timers[chat_id] = t
    t.start()

def update_activity(chat_id):
    last_activity[chat_id] = time.time()

def re_encode_message(chat_id, message_id, encoded_text):
    """تُعيد الرسالة لشكلها المشفر بعد 30 دقيقة خمول"""
    key = (chat_id, message_id)
    if key not in decoded_messages:
        return
    elapsed = time.time() - last_activity.get(chat_id, 0)
    if elapsed >= INACTIVITY_TIMEOUT:
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=encoded_text
            )
        except Exception:
            pass
        decoded_messages.pop(key, None)
    else:
        remaining = INACTIVITY_TIMEOUT - elapsed
        t = threading.Timer(remaining, re_encode_message, args=[chat_id, message_id, encoded_text])
        decoded_messages[key] = (encoded_text, t)
        t.start()

# ===================== AI =====================
def get_ai_reply(text: str) -> str:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system="أنت مساعد ذكاء اصطناعي مفيد وبسيط. أجب باختصار وبالعربية.",
            messages=[{"role": "user", "content": text}]
        )
        return response.content[0].text
    except Exception as e:
        return f"عذراً، حدث خطأ: {e}"

# ===================== /start =====================
@bot.message_handler(commands=["start"])
def handle_start(msg):
    update_activity(msg.chat.id)
    if ai_enabled.get(msg.chat.id, True):
        bot.send_message(msg.chat.id, "مرحباً! أنا بوت الذكاء الاصطناعي، كيف أقدر أساعدك؟")

# ===================== /help — للمالك فقط =====================
@bot.message_handler(commands=["help"])
def handle_help(msg):
    if not is_owner(msg):
        return
    help_text = (
        "📋 *الأوامر السرية*\n\n"
        "`.off [دقائق]` — تطفي AI لمدة معينة (افتراضي 30 دقيقة)\n"
        "`.on` — تشغّل AI فوراً\n"
        "`.hide الظاهر | المخفي` — ترسل رسالة مشفرة\n"
        "`.decode` (رد على رسالة) — تكشف المحتوى المخفي\n\n"
        "⚠️ _هذه الرسالة تختفي بعد 3 دقائق_"
    )
    sent = bot.send_message(OWNER_ID, help_text, parse_mode="Markdown")
    threading.Timer(
        HELP_DELETE_DELAY,
        lambda: bot.delete_message(OWNER_ID, sent.message_id)
    ).start()

# ===================== الأوامر السرية بالنقطة =====================
@bot.message_handler(func=lambda m: m.text and m.text.startswith("."))
def handle_secret_commands(msg):
    update_activity(msg.chat.id)
    text = msg.text.strip()
    chat_id = msg.chat.id

    # .off [دقائق]
    if text.startswith(".off"):
        parts = text.split()
        try:
            minutes = int(parts[1]) if len(parts) > 1 else 30
        except ValueError:
            minutes = 30
        disable_ai_timed(chat_id, minutes * 60)
        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass
        return

    # .on
    if text == ".on":
        set_ai(chat_id, True)
        cancel_timer(chat_id)
        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass
        return

    # .hide الظاهر | المخفي
    if text.startswith(".hide"):
        content = text[5:].strip()
        if '|' not in content:
            bot.reply_to(msg, "الصيغة: .hide الرسالة الظاهرة | الرسالة المخفية")
            return
        visible, secret = content.split('|', 1)
        encoded = encode_hidden(visible.strip(), secret.strip())
        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass
        bot.send_message(chat_id, encoded)
        return

    # .decode (رد على رسالة مشفرة)
    if text == ".decode":
        if not msg.reply_to_message:
            bot.reply_to(msg, "ارد على الرسالة المشفرة واكتب .decode")
            return

        encoded_text = msg.reply_to_message.text or ""
        secret = decode_hidden(encoded_text)

        # احذف رسالة الأمر فوراً
        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass

        if not secret:
            bot.reply_to(msg.reply_to_message, "❌ لا توجد رسالة مخفية")
            return

        target_msg_id = msg.reply_to_message.message_id

        # استبدل الرسالة المشفرة بالرسالة الحقيقية
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=target_msg_id,
                text=f"🔓 {secret}"
            )
        except Exception:
            pass

        # أعد التشفير بعد 30 دقيقة خمول
        key = (chat_id, target_msg_id)
        if key in decoded_messages:
            _, old_timer = decoded_messages[key]
            old_timer.cancel()

        t = threading.Timer(
            INACTIVITY_TIMEOUT,
            re_encode_message,
            args=[chat_id, target_msg_id, encoded_text]
        )
        decoded_messages[key] = (encoded_text, t)
        t.start()
        return

# ===================== الرسائل العادية =====================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_message(msg):
    chat_id = msg.chat.id
    update_activity(chat_id)

    # إذا AI مطفي → حوّل الرسالة لك
    if not ai_enabled.get(chat_id, True):
        if OWNER_ID:
            try:
                bot.forward_message(OWNER_ID, chat_id, msg.message_id)
            except Exception:
                pass
        return

    # رد AI
    reply = get_ai_reply(msg.text)
    bot.send_message(chat_id, reply)

# ===================== تشغيل =====================
if __name__ == "__main__":
    print("▶️ stealth_bot يعمل...")
    bot.infinity_polling()
