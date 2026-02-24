# Telegram Bot Project by Naif Saba
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json
from dotenv import load_dotenv

load_dotenv()

# ----- إعدادات البوت -----
TOKEN = os.environ.get("BOT_TOKEN", "")
SHEET_KEY = os.environ.get("SHEET_KEY", "")

bot = telebot.TeleBot(TOKEN)

# ----- إعدادات Google Sheets -----
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    google_creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if google_creds_json:
        creds_dict = json.loads(google_creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_KEY)
    sheet = spreadsheet.sheet1
    users_sheet = spreadsheet.worksheet("المستخدمين")
except Exception as e:
    print(f"خطأ في الاتصال بـ Google Sheets: {e}")
    sheet = None
    users_sheet = None

# ----- حالة المستخدم -----
user_state = {}

# ----- رسالة عدم الصلاحية -----
NO_ACCESS_MSG = "⛔ غير مسموح لك باستخدام البوت\n\nالرجاء طلب الصلاحية من منشئ البوت\n                         @nt18s"

# ----- أيام الأسبوع -----
DAYS_AR = {0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس", 4: "الجمعة", 5: "السبت", 6: "الأحد"}

# ----- صلاحيات من الشيت -----
def get_users():
    """يجلب قائمة المستخدمين من شيت المستخدمين"""
    try:
        rows = users_sheet.get_all_values()
        allowed = []
        admins = []
        for row in rows[1:]:
            if len(row) < 3:
                continue
            uid_str = row[1].strip()
            allowed_val = row[2].strip().upper()
            admin_val = row[3].strip().upper() if len(row) > 3 else "FALSE"
            if not uid_str.isdigit():
                continue
            uid = int(uid_str)
            if allowed_val == "TRUE":
                allowed.append(uid)
            if admin_val == "TRUE":
                admins.append(uid)
        return allowed, admins
    except Exception as e:
        print(f"خطأ في جلب المستخدمين: {e}")
        return [], []

def check_user(message):
    allowed, _ = get_users()
    return message.from_user.id in allowed

def is_admin(message):
    _, admins = get_users()
    return message.from_user.id in admins

# ----- مساعدات الخلية -----
def get_text(cell):
    return cell.split("|")[0].strip() if "|" in cell else cell.strip()

def get_file_id(cell):
    if "|" in cell:
        return cell.split("|")[1].strip()
    return ""

def merge_cell(text, file_id):
    return f"{text}|{file_id}"

# ----- مساعدات التاريخ -----
def get_day_ar(date_str):
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return DAYS_AR[dt.weekday()]
    except:
        return ""

def get_last_date(data, col):
    dates = []
    for r in data:
        d = safe_get(r, 0)
        if d and (get_text(safe_get(r, col)) or get_file_id(safe_get(r, col))):
            try:
                dates.append(parse_date(d))
            except:
                pass
    if not dates:
        return None
    return sorted(dates, key=lambda x: datetime.strptime(x, "%d/%m/%Y"))[-1]

# ----- قوائم الكيبورد -----
def main_menu(admin=False):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add("📚 المواد", "🕐 أوقات المحاضرات", "📝 التكاليف", "💰 أسعار الملازم", "⚠️ تنبيهات")
    if admin:
        markup.add("📤 رفع ملف")
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

def file_type_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add("📝 تكليف", "📖 ملخص", "🔙 العودة")
    return markup

# ----- مساعدات -----
def safe_get(row, idx):
    val = row[idx].strip() if len(row) > idx else ""
    return val.lstrip("'").strip() if val else ""

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

def save_file_to_cell(date, subject, col, file_id):
    try:
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if (safe_get(row, 0) and parse_date(safe_get(row, 0)) == date and
                    safe_get(row, 1) == subject):
                current = safe_get(row, col)
                text = get_text(current) if current else ""
                new_value = merge_cell(text, file_id)
                sheet.update_cell(i, col + 1, new_value)
                return True
        new_row = [""] * 7
        new_row[0] = date
        new_row[1] = subject
        new_row[col] = f"|{file_id}"
        sheet.append_row(new_row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        print(f"خطأ في حفظ الملف: {e}")
        return False

# ----- /start -----
@bot.message_handler(commands=['start'])
def start_message(message):
    if not check_user(message):
        bot.send_message(message.chat.id, NO_ACCESS_MSG)
        return
    user_state.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "مرحبًا! اختر أحد الخيارات:",
                     reply_markup=main_menu(admin=is_admin(message)))

# ----- استقبال الملفات -----
@bot.message_handler(content_types=['document', 'photo', 'video', 'audio'])
def handle_file(message):
    if not check_user(message):
        bot.send_message(message.chat.id, NO_ACCESS_MSG)
        return
    if not is_admin(message):
        bot.send_message(message.chat.id, "⛔ فقط المدير يستطيع رفع الملفات.")
        return

    uid = message.from_user.id
    state = user_state.get(uid, {})

    if state.get("uploading") and state.get("step") == "waiting_file":
        if message.document:
            file_id = message.document.file_id
        elif message.photo:
            file_id = message.photo[-1].file_id
        elif message.video:
            file_id = message.video.file_id
        elif message.audio:
            file_id = message.audio.file_id
        else:
            file_id = None

        if file_id:
            user_state[uid]["file_id"] = file_id
            user_state[uid]["step"] = "choose_subject"
            bot.send_message(message.chat.id, "✅ تم استلام الملف!\n\nاختر المادة:",
                             reply_markup=subjects_menu())
        return

    bot.send_message(message.chat.id, "📤 إذا تريد رفع ملف، اضغط على زر *رفع ملف* أولاً.",
                     parse_mode="Markdown", reply_markup=main_menu(admin=True))

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
    admin = is_admin(message)

    SUBJECTS = ["إحصاء واحتمالات", "انجليزي", "برمجة", "رياضيات 102", "شبكات", "عربي"]

    try:
        # ===== العودة =====
        if text == "🔙 العودة":
            if state.get("uploading"):
                user_state.pop(uid, None)
                bot.send_message(message.chat.id, "مرحبًا! اختر أحد الخيارات:",
                                 reply_markup=main_menu(admin=admin))
                return
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
                bot.send_message(message.chat.id, "مرحبًا! اختر أحد الخيارات:",
                                 reply_markup=main_menu(admin=admin))
            return

        # ===== رفع ملف =====
        if text == "📤 رفع ملف":
            if not admin:
                bot.send_message(message.chat.id, "⛔ فقط المدير يستطيع رفع الملفات.")
                return
            user_state[uid] = {"uploading": True, "step": "waiting_file"}
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("🔙 العودة")
            bot.send_message(message.chat.id, "📎 أرسل الملف الآن:", reply_markup=markup)
            return

        # ===== خطوات رفع الملف =====
        if state.get("uploading"):
            step = state.get("step")

            if step == "waiting_file":
                bot.send_message(message.chat.id, "📎 أرسل الملف أولاً.")
                return

            if step == "choose_subject" and text in SUBJECTS:
                user_state[uid]["subject"] = text
                user_state[uid]["step"] = "choose_type"
                bot.send_message(message.chat.id, f"📌 المادة: *{text}*\n\nاختر نوع الملف:",
                                 parse_mode="Markdown", reply_markup=file_type_menu())
                return

            if step == "choose_type" and text in ["📝 تكليف", "📖 ملخص"]:
                col = 3 if text == "📝 تكليف" else 5
                user_state[uid]["col"] = col
                user_state[uid]["file_type"] = text
                user_state[uid]["step"] = "choose_date"
                bot.send_message(message.chat.id,
                                 "📅 أدخل التاريخ بهذا الشكل:\n*dd/mm/yyyy*\nمثال: 23/02/2026",
                                 parse_mode="Markdown")
                return

            if step == "choose_date":
                date = parse_date(text)
                file_id = state.get("file_id")
                subject = state.get("subject")
                col = state.get("col")
                file_type = state.get("file_type")

                if save_file_to_cell(date, subject, col, file_id):
                    bot.send_message(message.chat.id,
                                     f"✅ تم حفظ الملف بنجاح!\n\n📌 المادة: *{subject}*\n{file_type}\n📅 التاريخ: {date}",
                                     parse_mode="Markdown", reply_markup=main_menu(admin=True))
                else:
                    bot.send_message(message.chat.id, "❌ حدث خطأ في حفظ الملف.",
                                     reply_markup=main_menu(admin=True))
                user_state.pop(uid, None)
                return

        # ===== 📚 المواد =====
        if text == "📚 المواد":
            user_state.pop(uid, None)
            bot.send_message(message.chat.id, "اختر المادة:", reply_markup=subjects_menu())
            return

        # ===== اختيار مادة =====
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
                    price = next((get_text(safe_get(r, 4)) for r in rows if safe_get(r, 4)), None)
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
                    parse_date(safe_get(r, 0)) for r in rows
                    if (get_text(safe_get(r, col)) or get_file_id(safe_get(r, col))) and safe_get(r, 0)
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
            response = f"*{subj}* — {text}\n" + "─" * 25 + "\n"
            file_ids = []

            for row in matched:
                cell = safe_get(row, col)
                val = get_text(cell)
                fid = get_file_id(cell)
                if val:
                    response += f"{label}: {val}\n"
                if fid:
                    file_ids.append(fid)

            if response.strip().endswith("─" * 25):
                response += "لا توجد بيانات."

            bot.send_message(message.chat.id, response, parse_mode="Markdown",
                             reply_markup=subject_options_menu())

            for fid in file_ids:
                try:
                    bot.send_document(message.chat.id, fid)
                except:
                    try:
                        bot.send_photo(message.chat.id, fid)
                    except:
                        pass

            user_state[uid] = {"subject": subj}
            return

        # ===== القائمة الرئيسية =====
        data = get_data()

        if text == "🕐 أوقات المحاضرات":
            last_date = get_last_date(data, 2)
            if not last_date:
                bot.send_message(message.chat.id, "📭 لا توجد محاضرات.", reply_markup=main_menu(admin=admin))
                return
            rows = [r for r in data if parse_date(safe_get(r, 0)) == last_date and get_text(safe_get(r, 2))]
            day = get_day_ar(last_date)
            response = "🕐 *محاضرات يوم " + day + " — " + last_date + ":*\n" + "─" * 25 + "\n"
            for r in rows:
                response += f"📌 {safe_get(r,1)}: {get_text(safe_get(r,2))}\n"
            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=main_menu(admin=admin))

        elif text == "📝 التكاليف":
            last_date = get_last_date(data, 3)
            if not last_date:
                bot.send_message(message.chat.id, "✅ لا يوجد تكاليف.", reply_markup=main_menu(admin=admin))
                return
            rows = [r for r in data if parse_date(safe_get(r, 0)) == last_date and get_text(safe_get(r, 3))]
            day = get_day_ar(last_date)
            response = "📝 *تكاليف يوم " + day + " — " + last_date + ":*\n" + "─" * 25 + "\n"
            for r in rows:
                response += f"📌 {safe_get(r,1)}: {get_text(safe_get(r,3))}\n"
            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=main_menu(admin=admin))

        elif text == "💰 أسعار الملازم":
            seen = {}
            for r in data:
                s = safe_get(r, 1)
                p = get_text(safe_get(r, 4))
                if s and p and s not in seen:
                    seen[s] = p
            if not seen:
                bot.send_message(message.chat.id, "لا توجد أسعار مسجلة.", reply_markup=main_menu(admin=admin))
                return
            response = "💰 *أسعار الملازم:*\n" + "─" * 25 + "\n"
            for s, p in seen.items():
                response += f"📖 {s}: {p}\n"
            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=main_menu(admin=admin))

        elif text == "⚠️ تنبيهات":
            alerts = [(safe_get(r,1), parse_date(safe_get(r,0)), get_text(safe_get(r,6)))
                      for r in data if get_text(safe_get(r,6))]
            if not alerts:
                bot.send_message(message.chat.id, "✅ لا توجد تنبيهات.", reply_markup=main_menu(admin=admin))
                return
            response = "⚠️ *التنبيهات:*\n" + "─" * 25 + "\n"
            for s, d, a in alerts:
                response += f"🔔 {s} ({d}):\n{a}\n\n"
            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=main_menu(admin=admin))

        else:
            bot.send_message(message.chat.id, "❓ اختر من القائمة.", reply_markup=main_menu(admin=admin))

    except Exception as e:
        bot.send_message(message.chat.id, "❌ حدث خطأ، حاول مرة أخرى.")
        print(f"Error: {e}")

# ----- سيرفر بسيط لإبقاء البوت مستيقظاً -----
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class KeepAlive(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), KeepAlive)
    server.serve_forever()

# ----- بدء البوت -----
if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    print("البوت يعمل...")
    bot.infinity_polling()
