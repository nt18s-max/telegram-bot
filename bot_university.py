# Telegram Bot Project by Naif Saba
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from env import TOKEN, SHEET_KEY

bot = telebot.TeleBot(TOKEN)

# ----- إعدادات Google Sheets -----
scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_KEY).sheet1

# ----- مساعدة اليوم -----
def get_day_name(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%A")

# ----- أوامر جانبية -----
@bot.message_handler(commands=['start'])
def start_message(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("ابدأ", "بحث باليوم", "تنبيهات", "تشيك الحساب")
    bot.send_message(message.chat.id, "اختر من القائمة الجانبية:", reply_markup=markup)

# ----- أوامر المحادثة -----
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text

    if text == "أوقات_المحاضرات":
        last_row = sheet.get_all_values()[-1]
        day = get_day_name(last_row[1])
        times = last_row[2]
        bot.send_message(message.chat.id, f"{day}\n{times}")

    elif text == "التكاليف":
        rows = sheet.get_all_values()[1:]   # تجاهل صف العناوين

        dates_with_costs = [row[1] for row in rows if len(row) > 3 and row[3]]

        if not dates_with_costs:
            bot.send_message(message.chat.id, "لا يوجد تكاليف حتى الآن")
            return

        markup = telebot.types.InlineKeyboardMarkup()

        for date in dates_with_costs:
            markup.add(
                telebot.types.InlineKeyboardButton(
                    f"📅 {date}",
                    callback_data=f"cost_{date}"
                )
            )

        markup.add(telebot.types.InlineKeyboardButton("⬅️ العودة", callback_data="back_main"))
        bot.send_message(message.chat.id, "اختر اليوم لعرض التكاليف:", reply_markup=markup)

    elif text == "الملخصات":
        today = datetime.today().strftime("%Y-%m-%d")
        rows = sheet.get_all_values()[1:]
        found = False

        for row in rows:
            if row[1] == today:
                found = True
                bot.send_message(message.chat.id, row[3])

        if not found:
            bot.send_message(message.chat.id, "لا يوجد ملخصات")

# ----- التعامل مع أزرار Inline -----
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):

    if call.data.startswith("cost_"):

        date_selected = call.data.split("_")[1]
        rows = sheet.get_all_values()[1:]

        print(rows)   # ← سطر التشخيص

        for row in rows:
            if row[1] == date_selected and len(row) > 3 and row[3]:
                bot.send_message(call.message.chat.id, row[3])

        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )

    elif call.data == "back_main":
        markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add("ابدأ", "بحث باليوم", "تنبيهات", "تشيك الحساب")
        bot.send_message(call.message.chat.id, "اختر من القائمة الجانبية:", reply_markup=markup)

# ----- تشغيل البوت -----
bot.infinity_polling()
