# Telegram Bot Project by Naif Saba
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# ----- إعدادات البوت -----
TOKEN = os.environ.get("BOT_TOKEN", "")
SHEET_KEY = os.environ.get("SHEET_KEY", "")
allowed_users = list(map(int, os.environ.get("ALLOWED_USERS", "0").split(",")))

bot = telebot.TeleBot(TOKEN)

# ----- إعدادات Google Sheets -----
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_KEY).sheet1
except Exception as e:
    print(f"خطأ في الاتصال بـ Google Sheets: {e}")
    sheet = None

# ----- حالة المستخدم -----
user_state = {}

# ----- صلاحيات المستخدم -----
def check_user(message):
    return message.from_user.id in allowed_users

# ----- قوائم الكيبورد -----
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add("📚 المواد", "🕐 أوقات المحاضرات", "📝 التكاليف", "💰 أسعار الملازم", "⚠️ تنبيهات")
    return markup

def subjects_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add("إحصاء واحتمالات", "انجليزي", "برمجة", "رياضيات 102", "شبكات", "عربي", "🔙 العودة")
    return markup

def subject_options_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add("🕐 أوقات المحاضرات", "📝 التكاليف", "💰 سعر الملزمة", "📖 الملخص", "⚠️ تنبيهات", "🔙 العودة")
    return markup

def dates_menu(dates):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for d in dates:
        markup.add(d)
    markup.add("🔙 العودة")
    return markup

# ----- مساعدات -----
def safe_get(row, idx):
    return row[idx].strip() if len(row) > idx and row[idx].strip() else ""

def parse_date(date_str):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return date_str.strip()

def get_data():
    try:
        rows = sheet.get_all_values()
        return rows[1:]
    except Exception as e:
        print(f"خطأ في جلب البيانات: {e}")
        return []

NO_ACCESS_MSG = "⛔ غير مسموح لك باستخدام البوت\n\nالرجاء طلب الصلاحية من منشئ البوت\n                         @nt18s"

# ----- /start -----
@bot.message_handler(commands=['start'])
def start_message(message):
    if not check_user(message):
        bot.send_message(message.chat.id, NO_ACCESS_MSG)
        return
    user_state.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "مرحبًا! اختر أحد الخيارات:", reply_markup=main_menu())

# ----- معالجة الرسائل -----
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if not check_user(message):
        bot.send_message(message.chat.id, NO_ACCESS_MSG)
        return
    if sheet is None:
        bot.send_message(message.chat.id, "❌ لا يوجد اتصال بقاعدة البيانات.")
        return

    uid = message.from_user.id
    text = message.text
    state = user_state.get(uid, {})

    try:
        # ===== العودة =====
        if text == "🔙 العودة":
            if state.get("subject") and not state.get("action") and not state.get("awaiting_date"):
                user_state.pop(uid, None)
                bot.send_message(message.chat.id, "اختر المادة:", reply_markup=subjects_menu())
            elif state.get("subject"):
                subj = state["subject"]
                user_state[uid] = {"subject": subj}
                bot.send_message(message.chat.id, f"📌 اخترت: *{subj}*\nماذا تحتاج؟",
                                 parse_mode="Markdown", reply_markup=subject_options_menu())
            else:
                user_state.pop(uid, None)
                bot.send_message(message.chat.id, "مرحبًا! اختر أحد الخيارات:", reply_markup=main_menu())
            return

        # ===== 📚 المواد =====
        if text == "📚 المواد":
            user_state.pop(uid, None)
            bot.send_message(message.chat.id, "اختر المادة:", reply_markup=subjects_menu())
            return

        # ===== اختيار مادة =====
        SUBJECTS = ["إحصاء واحتمالات", "انجليزي", "برمجة", "رياضيات 102", "شبكات", "عربي"]
        if text in SUBJECTS:
            user_state[uid] = {"subject": text}
            bot.send_message(message.chat.id, f"📌 اخترت: *{text}*\nماذا تحتاج؟",
                             parse_mode="Markdown", reply_markup=subject_options_menu())
            return

        # ===== خيارات داخل المادة =====
        if state.get("subject") and not state.get("awaiting_date"):
            subj = state["subject"]
            data = get_data()
            rows = [r for r in data if safe_get(r, 1) == subj]

            if text in ["🕐 أوقات المحاضرات", "📝 التكاليف", "📖 الملخص", "⚠️ تنبيهات", "💰 سعر الملزمة"]:
                if text == "💰 سعر الملزمة":
                    price = next((safe_get(r, 4) for r in rows if safe_get(r, 4)), None)
                    msg = f"💰 سعر ملزمة *{subj}*: {price}" if price else f"لا يوجد سعر مسجل لـ *{subj}*"
                    bot.send_message(message.chat.id, msg, parse_mode="Markdown",
                                     reply_markup=subject_options_menu())
                    return

                col_map = {
                    "🕐 أوقات المحاضرات": 2,
                    "📝 التكاليف": 3,
                    "📖 الملخص": 5,
                    "⚠️ تنبيهات": 6,
                }
                col = col_map[text]
                dates = list(dict.fromkeys(
                    parse_date(safe_get(r, 0)) for r in rows if safe_get(r, col) and safe_get(r, 0)
                ))

                if not dates:
                    bot.send_message(message.chat.id, f"لا توجد بيانات لـ *{subj}*",
                                     parse_mode="Markdown", reply_markup=subject_options_menu())
                    return

                user_state[uid] = {"subject": subj, "action": text, "awaiting_date": True, "col": col}
                bot.send_message(message.chat.id, "📅 اختر التاريخ:", reply_markup=dates_menu(dates))
                return

        # ===== اختيار التاريخ =====
        if state.get("awaiting_date"):
            subj = state["subject"]
            action = state["action"]
            col = state["col"]
            data = get_data()
            matched = [r for r in data if safe_get(r, 1) == subj and parse_date(safe_get(r, 0)) == text]

            if not matched:
                bot.send_message(message.chat.id, "لم يتم العثور على بيانات لهذا التاريخ.",
                                 reply_markup=subject_options_menu())
                user_state[uid] = {"subject": subj}
                return

            labels = {
                "🕐 أوقات المحاضرات": "🕐 الوقت",
                "📝 التكاليف": "📝 التكليف",
                "📖 الملخص": "📖 الملخص",
                "⚠️ تنبيهات": "⚠️ التنبيه",
            }
            label = labels.get(action, "")
            response = f"*{subj}* — {text}\n{'─'*25}\n"
            for row in matched:
                val = safe_get(row, col)
                if val:
                    response += f"{label}: {val}\n"

            if response.strip().endswith("─" * 25):
                response += "لا توجد بيانات."

            bot.send_message(message.chat.id, response, parse_mode="Markdown",
                             reply_markup=subject_options_menu())
            user_state[uid] = {"subject": subj}
            return

        # ===== القائمة الرئيسية =====
        data = get_data()
        today = datetime.today().strftime("%d/%m/%Y")

        if text == "🕐 أوقات المحاضرات":
            rows = [r for r in data if parse_date(safe_get(r, 0)) == today and safe_get(r, 2)]
            if not rows:
                bot.send_message(message.chat.id, "📭 لا توجد محاضرات لليوم.", reply_markup=main_menu())
                return
            response = f"🕐 *محاضرات اليوم:*\n{'─'*25}\n"
            for r in rows:
                response += f"📌 {safe_get(r,1)}: {safe_get(r,2)}\n"
            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=main_menu())

        elif text == "📝 التكاليف":
            rows = [r for r in data if parse_date(safe_get(r, 0)) == today and safe_get(r, 3)]
            if not rows:
                bot.send_message(message.chat.id, "✅ لا يوجد تكاليف لليوم.", reply_markup=main_menu())
                return
            response = f"📝 *تكاليف اليوم:*\n{'─'*25}\n"
            for r in rows:
                response += f"📌 {safe_get(r,1)}: {safe_get(r,3)}\n"
            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=main_menu())

        elif text == "💰 أسعار الملازم":
            seen = {}
            for r in data:
                s, p = safe_get(r, 1), safe_get(r, 4)
                if s and p and s not in seen:
                    seen[s] = p
            if not seen:
                bot.send_message(message.chat.id, "لا توجد أسعار مسجلة.", reply_markup=main_menu())
                return
            response = f"💰 *أسعار الملازم:*\n{'─'*25}\n"
            for s, p in seen.items():
                response += f"📖 {s}: {p}\n"
            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=main_menu())

        elif text == "⚠️ تنبيهات":
            alerts = [(safe_get(r,1), parse_date(safe_get(r,0)), safe_get(r,6)) for r in data if safe_get(r,6)]
            if not alerts:
                bot.send_message(message.chat.id, "✅ لا توجد تنبيهات.", reply_markup=main_menu())
                return
            response = f"⚠️ *التنبيهات:*\n{'─'*25}\n"
            for s, d, a in alerts:
                response += f"🔔 {s} ({d}):\n{a}\n\n"
            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=main_menu())

        else:
            bot.send_message(message.chat.id, "❓ اختر من القائمة.", reply_markup=main_menu())

    except Exception as e:
        bot.send_message(message.chat.id, "❌ حدث خطأ، حاول مرة أخرى.")
        print(f"Error: {e}")

# ----- بدء البوت -----
if __name__ == "__main__":
    print("البوت يعمل...")
    bot.infinity_polling()
