# Telegram Bot Project by Naif Saba
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ----- إعدادات البوت -----
TOKEN = "8514084720:AAHqsr3JLTvb5uSJ2IxJRQ6hNYHCtRKneps"
bot = telebot.TeleBot(TOKEN)

# ----- إعدادات Google Sheets -----
scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key("1miGc6eWklKkkvoelvoZmRxJ6ddXeGBSl91Ucj6rOrPs").sheet1

# ----- صلاحيات المستخدم -----
allowed_users = [123456789]  # ضع هنا ID الحسابات المسموح لها
def check_user(message):
    return message.from_user.id in allowed_users

# ----- مساعدة اليوم -----
def get_day_name(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%A")  # Monday, Tuesday...

# ----- أوامر جانبية -----
@bot.message_handler(commands=['start'])
def start_message(message):
    if not check_user(message):
        bot.send_message(message.chat.id, "غير مسموح لك باستخدام البوت.")
        return
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("ابدأ", "بحث باليوم", "تنبيهات", "تشيك الحساب")
    bot.send_message(message.chat.id, "اختر من القائمة الجانبية:", reply_markup=markup)

# ----- أوامر المحادثة -----
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if not check_user(message):
        bot.send_message(message.chat.id, "غير مسموح لك باستخدام البوت.")
        return
    text = message.text

    if text == "أوقات_المحاضرات":
        last_row = sheet.get_all_values()[-1]
        day = get_day_name(last_row[0])  # العمود 0: تاريخ
        times = last_row[1]  # العمود 1: أوقات المحاضرات
        bot.send_message(message.chat.id, f"{day}\n{times}")

    elif text == "التكاليف":
        today = datetime.today().strftime("%Y-%m-%d")
        rows = sheet.get_all_values()
        found = False
        for row in rows:
            if row[0] == today:
                found = True
                bot.send_message(message.chat.id, row[2])  # العمود 2: التكاليف
        if not found:
            bot.send_message(message.chat.id, "لا يوجد تكاليف")

    elif text == "الملخصات":
        today = datetime.today().strftime("%Y-%m-%d")
        rows = sheet.get_all_values()
        found = False
        for row in rows:
            if row[0] == today:
                found = True
                bot.send_message(message.chat.id, row[3])  # العمود 3: الملخصات
        if not found:
            bot.send_message(message.chat.id, "لا يوجد ملخصات")

# ----- بدء البوت -----
bot.infinity_polling()