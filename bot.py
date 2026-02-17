import telebot
import json

# ===== توكن البوت =====
TOKEN = "8514084720:AAHqsr3JLTvb5uSJ2IxJRQ6hNYH>
bot = telebot.TeleBot(TOKEN)

# ===== ملف البيانات =====
DATA_FILE = "data.json"

# ===== قراءة البيانات =====
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf>
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    return data

# ===== رسالة ترحيبية =====
@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "مرحبًا 👋\nاستخدم /تك>

# ===== عرض قائمة المواد =====
@bot.message_handler(commands=["تكاليف"])
def list_subjects(message):
    data = load_data()

    if not data:
        bot.reply_to(message, "لا توجد بيانات م>
        return

    markup = telebot.types.ReplyKeyboardMarkup(>
    buttons = [telebot.types.KeyboardButton(nam>
    markup.add(*buttons)

    bot.send_message(message.chat.id, "اختر الم>
# ===== عند اختيار مادة =====
@bot.message_handler(func=lambda message: True)
def show_subject_cost(message):
    data = load_data()
    subject = message.text

    if subject in data:
        cost = data[subject]
        bot.send_message(message.chat.id, f"تكل>
    else:
        bot.send_message(message.chat.id, "الما>

# ===== عرض جميع المواد =====
@bot.message_handler(commands=["جميع"])
def all_subjects(message):
    data = load_data()

    if not data:
        bot.reply_to(message, "لا توجد بيانات.")
        return

    text = ""
    for name, cost in data.items():
        text += f"{name} : {cost}\n"

    bot.send_message(message.chat.id, text)

# ===== تشغيل البوت =====
bot.infinity_polling()