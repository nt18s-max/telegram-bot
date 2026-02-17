# -*- coding: utf-8 -*-
import requests
import csv
from io import StringIO
import telebot
from telebot import types
from datetime import datetime

# --- توكن البوت الجديد ---
TOKEN = "8514084720:AAHqsr3JLTvb5uSJ2IxJRQ6hNYH>
bot = telebot.TeleBot(TOKEN)

# --- رابط CSV العام ---
CSV_URL = "https://docs.google.com/spreadsheets>

# --- تحميل البيانات ---
def load_data():
    response = requests.get(CSV_URL)
    response.encoding = 'utf-8'
    f = StringIO(response.text)
    reader = csv.DictReader(f)
    return list(reader)

data = load_data()

# --- تتبع التنبيهات لمرة واحدة لكل مستخدم ---
user_alert_sent = {}

# --- القائمة الرئيسية ---
def main_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📚 ا>
    markup.add(types.InlineKeyboardButton("🕘 أ>
    markup.add(types.InlineKeyboardButton("📝 ا>
    markup.add(types.InlineKeyboardButton("💰 أ>
    markup.add(types.InlineKeyboardButton("⚠️ تن>
    return markup

# --- بدء البوت ---@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "مرحبًا! ا>

# --- التعامل مع الأزرار ---
@bot.callback_query_handler(func=lambda call: T>
def callback_handler(call):
    global data
    chat_id = call.message.chat.id
    today_str = datetime.now().strftime("%d/%m/>
    data_today = [row for row in data if row['ا>

    # إعادة تحميل البيانات عند كل تفاعل للتحديث>
    data = load_data()

    # --- المواد (شجرة) ---
    if call.data == 'materials':
        materials = sorted(list({row['المادة'] >
        markup = types.InlineKeyboardMarkup()
        for mat in materials:
            markup.add(types.InlineKeyboardButt>
        markup.add(types.InlineKeyboardButton(">
        bot.edit_message_text("اختر المادة:", c>

    elif call.data.startswith('mat_'):
        mat_name = call.data.split('_',1)[1]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(">
        markup.add(types.InlineKeyboardButton(">
        markup.add(types.InlineKeyboardButton(">
        bot.edit_message_text(f"اختر ما تريد مع>

    elif call.data.startswith('time_'):
        mat_name = call.data.split('_',1)[1]
        rows = [row for row in data if row['الم>
        rows.sort(key=lambda x: datetime.strpti>
        text = f"⏰ أوقات محاضرات {mat_name}:\n"
        for r in rows:
            text += f"{r['التاريخ']} – {r['وقت >
        bot.edit_message_text(text, chat_id, caelif call.data.startswith('cost_'):
        mat_name = call.data.split('_',1)[1]
        rows = [row for row in data if row['الم>
        rows.sort(key=lambda x: datetime.strpti>
        text = f"📝 التكاليف ل{mat_name}:\n"
        for r in rows:
            text += f"{r['التاريخ']} – {r['التك>
        bot.edit_message_text(text, chat_id, ca>

    # --- أوقات المحاضرات اليوم ---
    elif call.data == 'times':
        if not data_today:
            bot.edit_message_text("لا توجد محاض>
            return
        text = "🕘 أوقات المحاضرات اليوم:\n"
        rows_sorted = sorted(data_today, key=la>
        for r in rows_sorted:
            text += f"{r['المادة']} – {r['وقت ا>
        bot.edit_message_text(text, chat_id, ca>

    # --- التكاليف اليوم ---
    elif call.data == 'costs':
        if not data_today:
            bot.edit_message_text("لا توجد تكال>
            return
        text = "📝 التكاليف اليوم:\n"
        rows_sorted = sorted(data_today, key=la>
        for r in rows_sorted:
            text += f"{r['المادة']} – {r['التكا>
        bot.edit_message_text(text, chat_id, ca>

    # --- أسعار الملازم ---
    elif call.data == 'prices':
        text = "💰 أسعار الملازم:\n"
        materials = sorted(list({row['المادة'] >
        for mat in materials:
            price = next(r['سعر الملزمة'] for r>
            text += f"{mat} – {price}\n"bot.edit_message_text(text, chat_id, ca>

    # --- التنبيهات لمرة واحدة ---
    elif call.data == 'alerts':
        if user_alert_sent.get(chat_id):
            bot.edit_message_text("⚠️ لا توجد مع>
        else:
            bot.edit_message_text("⚠️ تنبيه مهم >
            user_alert_sent[chat_id] = True

    # العودة للقائمة الرئيسية
    elif call.data == 'start':
        bot.edit_message_text("مرحبًا! اختر أحد >

# --- تشغيل البوت ---
bot.delete_webhook()
bot.infinity_polling()
