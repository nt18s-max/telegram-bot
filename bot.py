
# -*- coding: utf-8 -*-
import requests
import csv
from io import StringIO
import telebot
from telebot import types
from datetime import datetime

# --- توكن البوت الجديد ---
TOKEN = "8514084720:AAHqsr3JLTvb5uSJ2IxJRQ6hNYHCtRKneps"
bot = telebot.TeleBot(TOKEN)

# --- رابط CSV العام ---
CSV_URL = "https://docs.google.com/spreadsheets/d/1miGc6eWklKkkvoelvoZmRxJ6ddXeGBSl91Ucj6rOrPs/export?format=csv"

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
    markup.add(types.InlineKeyboardButton("📚 المواد", callback_data='materials'))
    markup.add(types.InlineKeyboardButton("🕘 أوقات المحاضرات", callback_data='times'))
    markup.add(types.InlineKeyboardButton("📝 التكاليف", callback_data='costs'))
    markup.add(types.InlineKeyboardButton("💰 أسعار الملازم", callback_data='prices'))
    markup.add(types.InlineKeyboardButton("⚠️ تنبيهات", callback_data='alerts'))
    return markup

# --- بدء البوت ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "مرحبًا! اختر أحد الخيارات:", reply_markup=main_menu())

# --- التعامل مع الأزرار ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    global data
    chat_id = call.message.chat.id
    today_str = datetime.now().strftime("%d/%m/%Y")
    data_today = [row for row in data if row['التاريخ'] == today_str]

    # إعادة تحميل البيانات عند كل تفاعل للتحديث اليومي
    data = load_data()

    # --- المواد (شجرة) ---
    if call.data == 'materials':
        materials = sorted(list({row['المادة'] for row in data}))
        markup = types.InlineKeyboardMarkup()
        for mat in materials:
            markup.add(types.InlineKeyboardButton(mat, callback_data=f'mat_{mat}'))
        markup.add(types.InlineKeyboardButton("⬅️ العودة", callback_data='start'))
        bot.edit_message_text("اختر المادة:", chat_id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith('mat_'):
        mat_name = call.data.split('_',1)[1]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(" 🕘 وقت المحاضرة", callback_data=f'time_{mat_name}'))
        markup.add(types.InlineKeyboardButton(" 📝 التكاليف", callback_data=f'cost_{mat_name}'))
        markup.add(types.InlineKeyboardButton("⬅️ العودة", callback_data='materials'))
        bot.edit_message_text(f"اختر ما تريد معرفته عن {mat_name}:", chat_id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith('time_'):
        mat_name = call.data.split('_',1)[1]
        rows = [row for row in data if row['المادة'] == mat_name]
        rows.sort(key=lambda x: datetime.strptime(x['التاريخ'] + ' ' + x['وقت المحاضرة'].split('–')[0], "%d/%m/%Y %H:%M"))
        text = f"⏰ أوقات محاضرات {mat_name}:\n"
        for r in rows:
            text += f"{r['التاريخ']} – {r['وقت المحاضرة']}\n"
        bot.edit_message_text(text, chat_id, call.message.message_id)

    elif call.data.startswith('cost_'):
        mat_name = call.data.split('_',1)[1]
        rows = [row for row in data if row['المادة'] == mat_name]
        rows.sort(key=lambda x: datetime.strptime(x['التاريخ'], "%d/%m/%Y"))
        text = f"📝 التكاليف ل{mat_name}:\n"
        for r in rows:
            text += f"{r['التاريخ']} – {r['التكاليف / الواجبات']}\n"
        bot.edit_message_text(text, chat_id, call.message.message_id)

    # --- أوقات المحاضرات اليوم ---
    elif call.data == 'times':
        if not data_today:
            bot.edit_message_text("لا توجد محاضرات اليوم", chat_id, call.message.message_id)
            return
        text = "🕘 أوقات المحاضرات اليوم:\n"
        rows_sorted = sorted(data_today, key=lambda x: x['وقت المحاضرة'])
        for r in rows_sorted:
            text += f"{r['المادة']} – {r['وقت المحاضرة']}\n"
        bot.edit_message_text(text, chat_id, call.message.message_id)

    # --- التكاليف اليوم ---
    elif call.data == 'costs':
        if not data_today:
            bot.edit_message_text("لا توجد تكاليف اليوم", chat_id, call.message.message_id)
            return
        text = "📝 التكاليف اليوم:\n"
        rows_sorted = sorted(data_today, key=lambda x: x['وقت المحاضرة'])
        for r in rows_sorted:
            text += f"{r['المادة']} – {r['التكاليف / الواجبات']}\n"
        bot.edit_message_text(text, chat_id, call.message.message_id)

    # --- أسعار الملازم ---
    elif call.data == 'prices':
        text = "💰 أسعار الملازم:\n"
        materials = sorted(list({row['المادة'] for row in data}))
        for mat in materials:
            price = next(r['سعر الملزمة'] for r in data if r['المادة']==mat)
            text += f"{mat} – {price}\n"
        bot.edit_message_text(text, chat_id, call.message.message_id)

    # --- التنبيهات لمرة واحدة ---
    elif call.data == 'alerts':
        if user_alert_sent.get(chat_id):
            bot.edit_message_text("⚠️ لا توجد معلومات جديدة", chat_id, call.message.message_id)
        else:
            bot.edit_message_text("⚠️ تنبيه مهم للمستخدم!", chat_id, call.message.message_id)
            user_alert_sent[chat_id] = True

    # العودة للقائمة الرئيسية
    elif call.data == 'start':
        bot.edit_message_text("مرحبًا! اختر أحد الخيارات:", chat_id, call.message.message_id, reply_markup=main_menu())

# --- تشغيل البوت ---
bot.delete_webhook()
bot.infinity_polling()