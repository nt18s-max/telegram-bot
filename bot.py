# Telegram Bot Project by Naif Saba
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
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
    help_sheet = spreadsheet.worksheet("المساعدة")
    try:
        rooms_sheet = spreadsheet.worksheet("القاعات")
    except:
        rooms_sheet = None
except Exception as e:
    print(f"خطأ في الاتصال بـ Google Sheets: {e}")
    sheet = None
    users_sheet = None
    help_sheet = None
    rooms_sheet = None

# ----- حالة المستخدم واللغة -----
user_state = {}
user_lang = {}

# ----- أيام الأسبوع -----
DAYS_AR = {0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس", 4: "الجمعة", 5: "السبت", 6: "الأحد"}
DAYS_EN = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}

# ----- ترجمات -----
LANG = {
    "ar": {
        "subjects": "📚 المواد", "schedule": "🕐 أوقات المحاضرات", "tasks": "📝 التكاليف",
        "prices": "💰 أسعار الملازم", "alerts": "⚠️ تنبيهات", "back": "🔙 العودة",
        "upload_file": "📤 رفع ملف", "upload_help": "📹 رفع التعليمات", "broadcast": "📢 إرسال إشعار",
        "add_data": "➕ إضافة بيانات",
        "choose_subject": "اختر المادة:", "choose_option": "ماذا تحتاج؟", "choose_date": "📅 اختر التاريخ:",
        "no_data": "لا توجد بيانات", "error": "❌ حدث خطأ، حاول مرة أخرى.", "choose_menu": "❓ اختر من القائمة.",
        "no_connection": "❌ لا يوجد اتصال بقاعدة البيانات.",
        "admin_only": "⛔ فقط المدير يستطيع القيام بهذا.",
        "send_file_first": "📤 إذا تريد رفع ملف، اضغط على زر *رفع ملف* أولاً.",
        "file_received": "✅ تم استلام الملف!\n\nاختر المادة:", "file_saved": "✅ تم حفظ الملف بنجاح!",
        "file_error": "❌ حدث خطأ في حفظ الملف.", "help_saved": "✅ تم الحفظ!", "help_error": "❌ حدث خطأ في الحفظ.",
        "for_users": "👤 للمستخدمين", "for_admins": "👑 للأدمن",
        "no_help": "📭 لا توجد تعليمات حالياً.",
        "help_title_user": "📖 تعليمات المستخدم", "help_title_admin": "📖 تعليمات الأدمن",
        "send_now": "📢 اكتب رسالة الإشعار:", "broadcast_done": "✅ تم الإرسال!",
        "broadcast_open": "⚠️ البوت مفتوح للكل، لا يمكن إرسال إشعار جماعي بدون قائمة معرفات.",
        "choose_audience": "👥 هذه التعليمات لمن؟", "send_file_now": "📎 أرسل الملف أو اكتب النص:",
        "no_lectures": "📭 لا توجد محاضرات.", "no_tasks": "✅ لا يوجد تكاليف.",
        "no_prices": "لا توجد أسعار مسجلة.", "no_alerts": "✅ لا توجد تنبيهات.",
        "choose_data_type": "اختر نوع البيانات للإضافة:",
        "add_lecture": "🕐 إضافة محاضرة", "add_task": "📝 إضافة تكليف نصي",
        "add_summary": "📖 إضافة ملخص نصي", "add_price": "💰 إضافة سعر ملزمة", "add_alert": "⚠️ إضافة تنبيه",
        "choose_building": "اختر المبنى:", "building_old": "🏛 القديم", "building_arts": "🏫 الاداب",
        "choose_room": "اختر القاعة:", "enter_time": "أدخل وقت المحاضرة:\nمثال: 8:00 - 9:30",
        "enter_date": "📅 أدخل التاريخ:",
        "enter_task": "أدخل نص التكليف:", "enter_price": "أدخل سعر الملزمة:", "enter_alert": "أدخل نص التنبيه:",
        "data_saved": "✅ تم حفظ البيانات بنجاح!", "data_error": "❌ حدث خطأ في حفظ البيانات.",
        "no_rooms": "⚠️ لا توجد قاعات لهذا المبنى.",
        "view_user_help": "👤 تعليمات المستخدم", "view_admin_help": "👑 تعليمات الأدمن",
        "choose_lang": "اختر من القائمة:", "subject_options_schedule": "🕐 أوقات المحاضرات",
        "subject_options_tasks": "📝 التكاليف", "subject_options_price": "💰 سعر الملزمة",
        "subject_options_summary": "📖 الملخص", "subject_options_alerts": "⚠️ تنبيهات",
        "task_type": "📝 تكليف", "summary_type": "📖 ملخص",
        "label_time": "🕐 الوقت", "label_task": "📝 التكليف", "label_summary": "📖 الملخص", "label_alert": "⚠️ التنبيه",
        "no_schedule": "لا توجد أوقات محاضرات لـ", "no_tasks_subj": "لا توجد تكاليف لـ", "no_summary": "لا توجد ملخصات لـ", "no_alerts_subj": "لا توجد تنبيهات لـ",
        "unknown": "غير معروف بعد", "no_exist": "لا يوجد",
    },
    "en": {
        "subjects": "📚 Subjects", "schedule": "🕐 Schedule", "tasks": "📝 Tasks",
        "prices": "💰 Book Prices", "alerts": "⚠️ Alerts", "back": "🔙 Back",
        "upload_file": "📤 Upload File", "upload_help": "📹 Upload Tutorials", "broadcast": "📢 Send Notification",
        "add_data": "➕ Add Data",
        "choose_subject": "Choose subject:", "choose_option": "What do you need?", "choose_date": "📅 Choose date:",
        "no_data": "No data available", "error": "❌ An error occurred, try again.", "choose_menu": "❓ Choose from the menu.",
        "no_connection": "❌ No database connection.",
        "admin_only": "⛔ Only admin can do this.",
        "send_file_first": "📤 To upload a file, press *Upload File* first.",
        "file_received": "✅ File received!\n\nChoose subject:", "file_saved": "✅ File saved successfully!",
        "file_error": "❌ Error saving file.", "help_saved": "✅ Saved!", "help_error": "❌ Error saving.",
        "for_users": "👤 For Users", "for_admins": "👑 For Admins",
        "no_help": "📭 No tutorials available.",
        "help_title_user": "📖 User Tutorials", "help_title_admin": "📖 Admin Tutorials",
        "send_now": "📢 Write your notification:", "broadcast_done": "✅ Sent!",
        "broadcast_open": "⚠️ Bot is open to all, cannot broadcast without ID list.",
        "choose_audience": "👥 Who is this for?", "send_file_now": "📎 Send the file or type the text:",
        "no_lectures": "📭 No lectures.", "no_tasks": "✅ No tasks.",
        "no_prices": "No prices recorded.", "no_alerts": "✅ No alerts.",
        "choose_data_type": "Choose data type to add:",
        "add_lecture": "🕐 Add Lecture", "add_task": "📝 Add Text Task",
        "add_summary": "📖 Add Text Summary", "add_price": "💰 Add Book Price", "add_alert": "⚠️ Add Alert",
        "choose_building": "Choose building:", "building_old": "🏛 Old Building", "building_arts": "🏫 Arts Building",
        "choose_room": "Choose room:", "enter_time": "Enter lecture time:\nExample: 8:00 - 9:30",
        "enter_date": "📅 Enter date:",
        "enter_task": "Enter task text:", "enter_price": "Enter book price:", "enter_alert": "Enter alert text:",
        "data_saved": "✅ Data saved successfully!", "data_error": "❌ Error saving data.",
        "no_rooms": "⚠️ No rooms for this building.",
        "view_user_help": "👤 User Tutorials", "view_admin_help": "👑 Admin Tutorials",
        "choose_lang": "Choose from menu:", "subject_options_schedule": "🕐 Schedule",
        "subject_options_tasks": "📝 Tasks", "subject_options_price": "💰 Book Price",
        "subject_options_summary": "📖 Summary", "subject_options_alerts": "⚠️ Alerts",
        "task_type": "📝 Task", "summary_type": "📖 Summary",
        "label_time": "🕐 Time", "label_task": "📝 Task", "label_summary": "📖 Summary", "label_alert": "⚠️ Alert",
        "no_schedule": "No schedule for", "no_tasks_subj": "No tasks for", "no_summary": "No summaries for", "no_alerts_subj": "No alerts for",
        "unknown": "Unknown yet", "no_exist": "Does not exist",
    }
}

def t(uid, key):
    lang = user_lang.get(uid, "ar")
    return LANG[lang].get(key, LANG["ar"].get(key, key))

# ----- قراءة الإعدادات من الشيت الثالث -----
def get_settings():
    try:
        rows = help_sheet.get_all_values()
        welcome = "مرحبًا! اختر أحد الخيارات:"
        rejection = "⛔ غير مسموح لك باستخدام البوت\n\nالرجاء طلب الصلاحية من منشئ البوت\n                         @nt18s"
        materials = []
        # صف 1-2: النصوص، صف 3: عناوين، صف 4+: المواد
        for row in rows[:2]:
            if not row:
                continue
            key = row[0].strip()
            val = row[1].strip() if len(row) > 1 else ""
            if key == "رسالة_الترحيب":
                welcome = val
            elif key == "رسالة_الرفض":
                rejection = val
        for row in rows[3:]:
            if not row or not any(r.strip() for r in row):
                continue
            file_id = row[1].strip() if len(row) > 1 else ""
            file_type = row[2].strip() if len(row) > 2 and row[2].strip() else ""
            audience = row[3].strip() if len(row) > 3 and row[3].strip() else "user"
            note = row[4].strip() if len(row) > 4 else ""
            if file_id or note:
                materials.append({"file_id": file_id, "file_type": file_type, "audience": audience, "note": note})
        return welcome, rejection, materials
    except Exception as e:
        print(f"خطأ في جلب الإعدادات: {e}")
        return "مرحبًا! اختر أحد الخيارات:", "⛔ غير مسموح", []

# ----- قراءة المواد من الشيت الأول -----
def get_subjects():
    try:
        rows = sheet.get_all_values()
        subjects = []
        for row in rows[1:]:
            subj = row[1].strip() if len(row) > 1 else ""
            if subj and subj not in subjects:
                subjects.append(subj)
        return subjects
    except Exception as e:
        print(f"خطأ في جلب المواد: {e}")
        return []

# ----- قراءة القاعات من الشيت الرابع -----
def get_rooms(building):
    try:
        if not rooms_sheet:
            return []
        rows = rooms_sheet.get_all_values()
        rooms = [row[1].strip() for row in rows if len(row) > 1 and row[0].strip() == building and row[1].strip()]
        return rooms
    except Exception as e:
        print(f"خطأ في جلب القاعات: {e}")
        return []

# ----- صلاحيات من الشيت الثاني -----
def get_users():
    try:
        rows = users_sheet.get_all_values()
        allowed = []
        admins = []
        open_all = False
        admin_all = False
        for row in rows[1:]:
            if not row:
                continue
            name = row[0].strip()
            uid_str = row[1].strip() if len(row) > 1 else ""
            allowed_val = row[2].strip().upper() if len(row) > 2 else "FALSE"
            admin_val = row[3].strip().upper() if len(row) > 3 else "FALSE"
            if name == "الكل":
                if allowed_val == "TRUE":
                    open_all = True
                if admin_val == "TRUE":
                    admin_all = True
                continue
            if not uid_str.isdigit():
                continue
            uid = int(uid_str)
            if allowed_val == "TRUE":
                allowed.append(uid)
            if admin_val == "TRUE":
                admins.append(uid)
        return allowed, admins, open_all, admin_all
    except Exception as e:
        print(f"خطأ في جلب المستخدمين: {e}")
        return [], [], False, False

def get_all_user_ids():
    try:
        rows = users_sheet.get_all_values()
        uids = []
        open_all = False
        for row in rows[1:]:
            if not row:
                continue
            name = row[0].strip()
            uid_str = row[1].strip() if len(row) > 1 else ""
            allowed_val = row[2].strip().upper() if len(row) > 2 else "FALSE"
            if name == "الكل" and allowed_val == "TRUE":
                open_all = True
            if uid_str.isdigit() and allowed_val == "TRUE":
                uids.append(int(uid_str))
        return uids, open_all
    except:
        return [], False

def check_user(message):
    allowed, _, open_all, _ = get_users()
    return open_all or message.from_user.id in allowed

def is_admin(message):
    _, admins, _, admin_all = get_users()
    return admin_all or message.from_user.id in admins

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
def get_day_name(date_str, uid):
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        lang = user_lang.get(uid, "ar")
        return DAYS_EN[dt.weekday()] if lang == "en" else DAYS_AR[dt.weekday()]
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
def lang_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🇸🇦 العربية", "🇬🇧 English")
    return markup

def main_menu(uid, admin=False):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(t(uid, "subjects"))
    markup.row(
        telebot.types.KeyboardButton(t(uid, "tasks")),
        telebot.types.KeyboardButton(t(uid, "schedule"))
    )
    markup.row(
        telebot.types.KeyboardButton(t(uid, "alerts")),
        telebot.types.KeyboardButton(t(uid, "prices"))
    )
    if admin:
        markup.add(t(uid, "add_data"))
        markup.row(
            telebot.types.KeyboardButton(t(uid, "upload_help")),
            telebot.types.KeyboardButton(t(uid, "upload_file")),
            telebot.types.KeyboardButton(t(uid, "broadcast"))
        )
    return markup

def subjects_menu(uid):
    subjects = get_subjects()
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for s in subjects:
        markup.add(s)
    markup.add(t(uid, "back"))
    return markup, subjects

def subject_options_menu(uid):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(t(uid, "subject_options_schedule"))
    markup.add(t(uid, "subject_options_tasks"))
    markup.add(t(uid, "subject_options_price"))
    markup.add(t(uid, "subject_options_summary"))
    markup.add(t(uid, "subject_options_alerts"))
    markup.add(t(uid, "back"))
    return markup

def dates_menu(uid, dates):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for d in dates:
        markup.add(d)
    markup.add(t(uid, "back"))
    return markup

def file_type_menu(uid):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(t(uid, "task_type"))
    markup.add(t(uid, "summary_type"))
    markup.add(t(uid, "back"))
    return markup

def help_audience_menu(uid):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(t(uid, "for_users"), t(uid, "for_admins"))
    markup.add(t(uid, "back"))
    return markup

def help_view_menu(uid):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(t(uid, "view_user_help"), t(uid, "view_admin_help"))
    markup.add(t(uid, "back"))
    return markup

def add_data_menu(uid):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(t(uid, "add_lecture"))
    markup.add(t(uid, "add_task"))
    markup.add(t(uid, "add_summary"))
    markup.add(t(uid, "add_price"))
    markup.add(t(uid, "add_alert"))
    markup.add(t(uid, "back"))
    return markup

def buildings_menu(uid):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(t(uid, "building_old"), t(uid, "building_arts"))
    markup.add(t(uid, "back"))
    return markup

def rooms_menu(uid, building_key):
    rooms = get_rooms(building_key)
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for r in rooms:
        markup.add(r)
    markup.add(t(uid, "back"))
    return markup, rooms

def back_only_with_no_exist_menu(uid):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(t(uid, "no_exist"), t(uid, "back"))
    return markup

def back_only_menu(uid):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(t(uid, "back"))
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

def send_today_date(chat_id):
    today = datetime.now().strftime("%d/%m/%Y")
    bot.send_message(chat_id, f"`{today}`", parse_mode="Markdown")

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

def save_text_to_cell(date, subject, col, text_val):
    try:
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if (safe_get(row, 0) and parse_date(safe_get(row, 0)) == date and
                    safe_get(row, 1) == subject):
                sheet.update_cell(i, col + 1, text_val)
                return True
        new_row = [""] * 7
        new_row[0] = date
        new_row[1] = subject
        new_row[col] = text_val
        sheet.append_row(new_row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        print(f"خطأ في حفظ البيانات: {e}")
        return False

def save_help_material(file_id, file_type, audience, note=""):
    try:
        help_sheet.append_row(["مادة مساعدة", file_id, file_type, audience, note])
        return True
    except Exception as e:
        print(f"خطأ في حفظ مادة المساعدة: {e}")
        return False

def send_help_materials(chat_id, uid, audience_filter):
    _, _, materials = get_settings()
    filtered = [m for m in materials if m["audience"] == audience_filter]
    if not filtered:
        bot.send_message(chat_id, t(uid, "no_help"))
        return
    title = t(uid, "help_title_user") if audience_filter == "user" else t(uid, "help_title_admin")
    bot.send_message(chat_id, f"*{title}*", parse_mode="Markdown")
    for m in filtered:
        fid = m["file_id"]
        ftype = m["file_type"]
        note = m["note"]
        if note:
            bot.send_message(chat_id, note)
        if fid:
            try:
                if ftype == "photo":
                    bot.send_photo(chat_id, fid)
                elif ftype == "audio":
                    bot.send_audio(chat_id, fid)
                elif ftype == "document":
                    bot.send_document(chat_id, fid)
                elif ftype == "text":
                    pass
                else:
                    bot.send_video(chat_id, fid)
            except:
                try:
                    bot.send_document(chat_id, fid)
                except:
                    pass

# ----- /start -----
@bot.message_handler(commands=['start'])
def start_message(message):
    _, rejection, _ = get_settings()
    if not check_user(message):
        bot.send_message(message.chat.id, rejection)
        return
    uid = message.from_user.id
    user_state.pop(uid, None)
    welcome, _, _ = get_settings()
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=is_admin(message)))

@bot.message_handler(commands=['language'])
def language_command(message):
    _, rejection, _ = get_settings()
    if not check_user(message):
        bot.send_message(message.chat.id, rejection)
        return
    user_state[message.from_user.id] = {"choosing_lang": True}
    bot.send_message(message.chat.id, "🌐 اختر اللغة / Choose Language", reply_markup=lang_menu())

# ----- /help -----
@bot.message_handler(commands=['help'])
def help_message(message):
    uid = message.from_user.id
    admin = is_admin(message)
    if admin:
        bot.send_message(message.chat.id, t(uid, "choose_lang"), reply_markup=help_view_menu(uid))
        user_state[uid] = {"viewing_help": True}
    else:
        send_help_materials(message.chat.id, uid, "user")

# ----- استقبال الملفات -----
@bot.message_handler(content_types=['document', 'photo', 'video', 'audio'])
def handle_file(message):
    _, rejection, _ = get_settings()
    if not check_user(message):
        bot.send_message(message.chat.id, rejection)
        return
    if not is_admin(message):
        bot.send_message(message.chat.id, t(message.from_user.id, "admin_only"))
        return

    uid = message.from_user.id
    state = user_state.get(uid, {})

    if message.document:
        file_id = message.document.file_id
        ftype = "document"
    elif message.photo:
        file_id = message.photo[-1].file_id
        ftype = "photo"
    elif message.video:
        file_id = message.video.file_id
        ftype = "video"
    elif message.audio:
        file_id = message.audio.file_id
        ftype = "audio"
    else:
        return

    # رفع تعليمات البوت
    if state.get("uploading_help") and state.get("step") == "waiting_file_help":
        audience = state.get("audience", "user")
        note = state.get("note", "")
        type_names = {"video": "الفيديو", "photo": "الصورة", "audio": "الصوت", "document": "الملف"}
        type_name = type_names.get(ftype, "الملف")
        if save_help_material(file_id, ftype, audience, note):
            bot.send_message(message.chat.id, f"✅ تم حفظ {type_name}!", reply_markup=main_menu(uid, admin=True))
        else:
            bot.send_message(message.chat.id, t(uid, "help_error"), reply_markup=main_menu(uid, admin=True))
        user_state.pop(uid, None)
        return

    # رفع ملف عادي
    if state.get("uploading") and state.get("step") == "waiting_file":
        user_state[uid]["file_id"] = file_id
        user_state[uid]["step"] = "choose_subject"
        markup, _ = subjects_menu(uid)
        bot.send_message(message.chat.id, t(uid, "file_received"), reply_markup=markup)
        return

    bot.send_message(message.chat.id, t(uid, "send_file_first"), parse_mode="Markdown",
                     reply_markup=main_menu(uid, admin=True))

# ----- معالجة الرسائل -----
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    _, rejection, _ = get_settings()
    if not check_user(message):
        bot.send_message(message.chat.id, rejection)
        return
    if sheet is None:
        bot.send_message(message.chat.id, "❌ لا يوجد اتصال بقاعدة البيانات.")
        return

    uid = message.from_user.id
    text = message.text
    state = user_state.get(uid, {})
    admin = is_admin(message)
    back_btn = t(uid, "back")

    try:
        # ===== اختيار اللغة =====
        if state.get("choosing_lang") or text in ["🇸🇦 العربية", "🇬🇧 English"]:
            if text == "🇸🇦 العربية":
                user_lang[uid] = "ar"
            elif text == "🇬🇧 English":
                user_lang[uid] = "en"
            else:
                bot.send_message(message.chat.id, "🌐 اختر اللغة / Choose Language", reply_markup=lang_menu())
                return
            user_state.pop(uid, None)
            welcome, _, _ = get_settings()
            bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin))
            return

        # ===== عرض تعليمات البوت =====
        if state.get("viewing_help"):
            if text == t(uid, "view_user_help"):
                send_help_materials(message.chat.id, uid, "user")
                user_state.pop(uid, None)
                bot.send_message(message.chat.id, t(uid, "choose_lang"), reply_markup=main_menu(uid, admin=admin))
                return
            elif text == t(uid, "view_admin_help"):
                send_help_materials(message.chat.id, uid, "admin")
                user_state.pop(uid, None)
                bot.send_message(message.chat.id, t(uid, "choose_lang"), reply_markup=main_menu(uid, admin=admin))
                return

        # ===== العودة =====
        if text == back_btn:
            if state.get("uploading") or state.get("uploading_help") or state.get("viewing_help") or state.get("broadcasting") or state.get("adding_data"):
                user_state.pop(uid, None)
                welcome, _, _ = get_settings()
                bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin))
                return
            if state.get("awaiting_date"):
                subj = state["subject"]
                user_state[uid] = {"subject": subj}
                bot.send_message(message.chat.id, f"📌 {subj}\n{t(uid, 'choose_option')}",
                                 parse_mode="Markdown", reply_markup=subject_options_menu(uid))
                return
            if state.get("subject"):
                user_state.pop(uid, None)
                markup, _ = subjects_menu(uid)
                bot.send_message(message.chat.id, t(uid, "choose_subject"), reply_markup=markup)
                return
            user_state.pop(uid, None)
            welcome, _, _ = get_settings()
            bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin))
            return

        # ===== إرسال إشعار =====
        if text == t(uid, "broadcast"):
            if not admin:
                bot.send_message(message.chat.id, t(uid, "admin_only"))
                return
            user_state[uid] = {"broadcasting": True}
            bot.send_message(message.chat.id, t(uid, "send_now"), reply_markup=back_only_menu(uid))
            return

        if state.get("broadcasting"):
            uids, open_all = get_all_user_ids()
            if open_all:
                bot.send_message(message.chat.id, t(uid, "broadcast_open"))
            else:
                success = 0
                fail = 0
                for user_id in uids:
                    try:
                        bot.send_message(user_id, f"📢 *إشعار:*\n\n{text}", parse_mode="Markdown")
                        success += 1
                    except:
                        fail += 1
                bot.send_message(message.chat.id,
                                 f"{t(uid, 'broadcast_done')}\n✅ {success} | ❌ {fail}",
                                 reply_markup=main_menu(uid, admin=True))
            user_state.pop(uid, None)
            return

        # ===== رفع تعليمات البوت =====
        if text == t(uid, "upload_help"):
            if not admin:
                bot.send_message(message.chat.id, t(uid, "admin_only"))
                return
            user_state[uid] = {"uploading_help": True, "step": "choose_audience"}
            bot.send_message(message.chat.id, t(uid, "choose_audience"), reply_markup=help_audience_menu(uid))
            return

        if state.get("uploading_help"):
            step = state.get("step")
            if step == "choose_audience":
                if text == t(uid, "for_users"):
                    user_state[uid]["audience"] = "user"
                elif text == t(uid, "for_admins"):
                    user_state[uid]["audience"] = "admin"
                else:
                    return
                user_state[uid]["step"] = "choose_note"
                bot.send_message(message.chat.id, "أدخل نصاً توضيحياً (اختياري) أو أرسل الملف مباشرة:",
                                 reply_markup=back_only_menu(uid))
                return
            if step == "choose_note":
                user_state[uid]["note"] = text
                user_state[uid]["step"] = "waiting_file_help"
                bot.send_message(message.chat.id, t(uid, "send_file_now"), reply_markup=back_only_menu(uid))
                return
            if step == "waiting_file_help":
                # النص فقط بدون ملف
                audience = state.get("audience", "user")
                note = state.get("note", "")
                if save_help_material("", "text", audience, text):
                    bot.send_message(message.chat.id, t(uid, "help_saved"), reply_markup=main_menu(uid, admin=True))
                else:
                    bot.send_message(message.chat.id, t(uid, "help_error"), reply_markup=main_menu(uid, admin=True))
                user_state.pop(uid, None)
                return

        # ===== رفع ملف عادي =====
        if text == t(uid, "upload_file"):
            if not admin:
                bot.send_message(message.chat.id, t(uid, "admin_only"))
                return
            user_state[uid] = {"uploading": True, "step": "waiting_file"}
            bot.send_message(message.chat.id, t(uid, "send_file_now"), reply_markup=back_only_menu(uid))
            return

        if state.get("uploading"):
            step = state.get("step")
            if step == "waiting_file":
                bot.send_message(message.chat.id, t(uid, "send_file_now"))
                return
            _, subjects = subjects_menu(uid)
            if step == "choose_subject" and text in subjects:
                user_state[uid]["subject"] = text
                user_state[uid]["step"] = "choose_type"
                bot.send_message(message.chat.id, f"📌 *{text}*", parse_mode="Markdown",
                                 reply_markup=file_type_menu(uid))
                return
            if step == "choose_type" and text in [t(uid, "task_type"), t(uid, "summary_type")]:
                col = 3 if text == t(uid, "task_type") else 5
                user_state[uid]["col"] = col
                user_state[uid]["file_type"] = text
                user_state[uid]["step"] = "choose_date"
                bot.send_message(message.chat.id, t(uid, "enter_date"), parse_mode="Markdown")
                send_today_date(message.chat.id)
                return
            if step == "choose_date":
                date = parse_date(text)
                file_id = state.get("file_id")
                subject = state.get("subject")
                col = state.get("col")
                file_type = state.get("file_type")
                if save_file_to_cell(date, subject, col, file_id):
                    bot.send_message(message.chat.id,
                                     f"{t(uid, 'file_saved')}\n\n📌 *{subject}*\n{file_type}\n📅 {date}",
                                     parse_mode="Markdown", reply_markup=main_menu(uid, admin=True))
                else:
                    bot.send_message(message.chat.id, t(uid, "file_error"), reply_markup=main_menu(uid, admin=True))
                user_state.pop(uid, None)
                return

        # ===== إضافة بيانات =====
        if text == t(uid, "add_data"):
            if not admin:
                bot.send_message(message.chat.id, t(uid, "admin_only"))
                return
            user_state[uid] = {"adding_data": True, "step": "choose_type"}
            bot.send_message(message.chat.id, t(uid, "choose_data_type"), reply_markup=add_data_menu(uid))
            return

        if state.get("adding_data"):
            step = state.get("step")
            _, subjects = subjects_menu(uid)

            if step == "choose_type":
                data_types = {
                    t(uid, "add_lecture"): "lecture",
                    t(uid, "add_task"): "task",
                    t(uid, "add_summary"): "summary",
                    t(uid, "add_price"): "price",
                    t(uid, "add_alert"): "alert",
                }
                if text in data_types:
                    user_state[uid]["data_type"] = data_types[text]
                    user_state[uid]["step"] = "choose_subject"
                    markup, _ = subjects_menu(uid)
                    bot.send_message(message.chat.id, t(uid, "choose_subject_add"), reply_markup=markup)
                return

            if step == "choose_subject" and text in subjects:
                user_state[uid]["subject"] = text
                data_type = state.get("data_type")
                if data_type == "lecture":
                    user_state[uid]["step"] = "choose_building"
                    bot.send_message(message.chat.id, t(uid, "choose_building"), reply_markup=buildings_menu(uid))
                elif data_type == "price":
                    user_state[uid]["step"] = "enter_value"
                    bot.send_message(message.chat.id, t(uid, "enter_price"), reply_markup=back_only_with_no_exist_menu(uid))
                elif data_type == "alert":
                    user_state[uid]["step"] = "enter_date"
                    bot.send_message(message.chat.id, t(uid, "enter_date"), reply_markup=back_only_menu(uid))
                else:
                    user_state[uid]["step"] = "enter_date"
                    bot.send_message(message.chat.id, t(uid, "enter_date"), reply_markup=back_only_menu(uid))
                return

            if step == "choose_building":
                building_map = {t(uid, "building_old"): "القديم", t(uid, "building_arts"): "الاداب"}
                if text in building_map:
                    building_key = building_map[text]
                    user_state[uid]["building"] = building_key
                    user_state[uid]["building_label"] = text
                    markup, rooms = rooms_menu(uid, building_key)
                    if not rooms:
                        bot.send_message(message.chat.id, t(uid, "no_rooms"))
                        return
                    user_state[uid]["step"] = "choose_room"
                    bot.send_message(message.chat.id, t(uid, "choose_room"), reply_markup=markup)
                return

            if step == "choose_room":
                building_label = state.get("building_label", "")
                user_state[uid]["room"] = f"{building_label}: {text}"
                user_state[uid]["step"] = "enter_time"
                bot.send_message(message.chat.id, t(uid, "enter_time"), reply_markup=back_only_with_no_exist_menu(uid))
                return

            if step == "enter_time":
                if text == t(uid, "no_exist"):
                    user_state[uid]["time_val"] = t(uid, "no_exist")
                else:
                    user_state[uid]["time_val"] = text
                user_state[uid]["step"] = "enter_date"
                bot.send_message(message.chat.id, t(uid, "enter_date"), reply_markup=back_only_menu(uid))
                return

            if step == "enter_date":
                date = parse_date(text)
                user_state[uid]["date"] = date
                data_type = state.get("data_type")
                if data_type == "alert":
                    user_state[uid]["step"] = "enter_value"
                    bot.send_message(message.chat.id, t(uid, "enter_alert"), reply_markup=back_only_with_no_exist_menu(uid))
                elif data_type == "task":
                    user_state[uid]["step"] = "enter_value"
                    bot.send_message(message.chat.id, t(uid, "enter_task"), reply_markup=back_only_with_no_exist_menu(uid))
                elif data_type == "summary":
                    user_state[uid]["step"] = "enter_value"
                    bot.send_message(message.chat.id, "أدخل نص الملخص:", reply_markup=back_only_with_no_exist_menu(uid))
                elif data_type == "lecture":
                    # حفظ المحاضرة
                    subject = state.get("subject")
                    room = state.get("room", "")
                    time_val = state.get("time_val", "")
                    val = f"{room} | {time_val}" if room else time_val
                    if save_text_to_cell(date, subject, 2, val):
                        bot.send_message(message.chat.id, t(uid, "data_saved"), reply_markup=main_menu(uid, admin=True))
                    else:
                        bot.send_message(message.chat.id, t(uid, "data_error"), reply_markup=main_menu(uid, admin=True))
                    user_state.pop(uid, None)
                return

            if step == "enter_value":
                subject = state.get("subject")
                date = state.get("date", "")
                data_type = state.get("data_type")
                if text == t(uid, "no_exist"):
                    text = t(uid, "no_exist")

                if data_type == "price":
                    # سعر الملزمة - ابحث في أي صف لهذه المادة
                    rows = sheet.get_all_values()
                    updated = False
                    for i, row in enumerate(rows[1:], start=2):
                        if safe_get(row, 1) == subject:
                            sheet.update_cell(i, 5, text)
                            updated = True
                            break
                    if not updated:
                        new_row = ["", subject, "", "", text, "", ""]
                        sheet.append_row(new_row, value_input_option="USER_ENTERED")
                    bot.send_message(message.chat.id, t(uid, "data_saved"), reply_markup=main_menu(uid, admin=True))

                elif data_type == "task":
                    if save_text_to_cell(date, subject, 3, text):
                        bot.send_message(message.chat.id, t(uid, "data_saved"), reply_markup=main_menu(uid, admin=True))
                    else:
                        bot.send_message(message.chat.id, t(uid, "data_error"), reply_markup=main_menu(uid, admin=True))

                elif data_type == "summary":
                    if save_text_to_cell(date, subject, 5, text):
                        bot.send_message(message.chat.id, t(uid, "data_saved"), reply_markup=main_menu(uid, admin=True))
                    else:
                        bot.send_message(message.chat.id, t(uid, "data_error"), reply_markup=main_menu(uid, admin=True))

                elif data_type == "alert":
                    if save_text_to_cell(date, subject, 6, text):
                        bot.send_message(message.chat.id, t(uid, "data_saved"), reply_markup=main_menu(uid, admin=True))
                    else:
                        bot.send_message(message.chat.id, t(uid, "data_error"), reply_markup=main_menu(uid, admin=True))

                user_state.pop(uid, None)
                return

        # ===== 📚 المواد =====
        if text == t(uid, "subjects"):
            user_state.pop(uid, None)
            markup, _ = subjects_menu(uid)
            bot.send_message(message.chat.id, t(uid, "choose_subject"), reply_markup=markup)
            return

        # ===== اختيار مادة =====
        _, subjects = subjects_menu(uid)
        if text in subjects:
            user_state[uid] = {"subject": text}
            bot.send_message(message.chat.id, f"📌 *{text}*\n{t(uid, 'choose_option')}",
                             parse_mode="Markdown", reply_markup=subject_options_menu(uid))
            return

        # ===== خيارات داخل المادة =====
        subject_opts = [t(uid, k) for k in ["subject_options_schedule", "subject_options_tasks",
                        "subject_options_price", "subject_options_summary", "subject_options_alerts"]]

        if state.get("subject") and not state.get("awaiting_date"):
            subj = state["subject"]
            data = get_data()
            rows = [r for r in data if safe_get(r, 1) == subj]

            if text in subject_opts:
                if text == t(uid, "subject_options_price"):
                    price = next((get_text(safe_get(r, 4)) for r in rows if safe_get(r, 4)), None)
                    msg = f"💰 *{subj}*: {price}" if price else f"لا يوجد سعر مسجل لـ *{subj}*"
                    bot.send_message(message.chat.id, msg, parse_mode="Markdown",
                                     reply_markup=subject_options_menu(uid))
                    return

                col_map = {
                    t(uid, "subject_options_schedule"): 2,
                    t(uid, "subject_options_tasks"): 3,
                    t(uid, "subject_options_summary"): 5,
                    t(uid, "subject_options_alerts"): 6,
                }
                col = col_map[text]
                dates = list(dict.fromkeys(
                    parse_date(safe_get(r, 0)) for r in rows
                    if (get_text(safe_get(r, col)) or get_file_id(safe_get(r, col))) and safe_get(r, 0)
                ))
                if not dates:
                    no_data_map = {
                        t(uid, "subject_options_schedule"): t(uid, "no_schedule"),
                        t(uid, "subject_options_tasks"): t(uid, "no_tasks_subj"),
                        t(uid, "subject_options_summary"): t(uid, "no_summary"),
                        t(uid, "subject_options_alerts"): t(uid, "no_alerts_subj"),
                    }
                    no_msg = no_data_map.get(text, "لا توجد بيانات لـ")
                    bot.send_message(message.chat.id, f"{no_msg} *{subj}*",
                                     parse_mode="Markdown", reply_markup=subject_options_menu(uid))
                    return
                user_state[uid] = {"subject": subj, "action": text, "awaiting_date": True, "col": col, "dates": dates}
                bot.send_message(message.chat.id, t(uid, "choose_date"), reply_markup=dates_menu(uid, dates))
                return

        # ===== اختيار التاريخ =====
        if state.get("awaiting_date"):
            subj = state["subject"]
            action = state["action"]
            col = state["col"]
            dates = state.get("dates", [])
            data = get_data()
            matched = [r for r in data if safe_get(r, 1) == subj and parse_date(safe_get(r, 0)) == text]

            if not matched:
                bot.send_message(message.chat.id, t(uid, "no_data"), reply_markup=dates_menu(uid, dates))
                return

            label_map = {
                t(uid, "subject_options_schedule"): t(uid, "label_time"),
                t(uid, "subject_options_tasks"): t(uid, "label_task"),
                t(uid, "subject_options_summary"): t(uid, "label_summary"),
                t(uid, "subject_options_alerts"): t(uid, "label_alert"),
            }
            label = label_map.get(action, "")
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
                response += t(uid, "no_data")

            bot.send_message(message.chat.id, response, parse_mode="Markdown",
                             reply_markup=dates_menu(uid, dates))
            for fid in file_ids:
                try:
                    bot.send_document(message.chat.id, fid)
                except:
                    try:
                        bot.send_photo(message.chat.id, fid)
                    except:
                        pass
            return

        # ===== القائمة الرئيسية =====
        data = get_data()

        if text == t(uid, "schedule"):
            last_date = get_last_date(data, 2)
            if not last_date:
                bot.send_message(message.chat.id, t(uid, "no_lectures"), reply_markup=main_menu(uid, admin=admin))
                return
            rows = [r for r in data if parse_date(safe_get(r, 0)) == last_date and get_text(safe_get(r, 2))]
            day = get_day_name(last_date, uid)
            response = f"🕐 *{day} — {last_date}:*\n" + "─" * 25 + "\n"
            for r in rows:
                response += f"📌 {safe_get(r,1)}: {get_text(safe_get(r,2))}\n"
            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=main_menu(uid, admin=admin))

        elif text == t(uid, "tasks"):
            last_date = get_last_date(data, 3)
            if not last_date:
                has_any = any(safe_get(r, 1) for r in data)
                msg = t(uid, "no_exist") + " 📝" if has_any else t(uid, "unknown") + " 📝"
                bot.send_message(message.chat.id, msg, reply_markup=main_menu(uid, admin=admin))
                return
            rows = [r for r in data if parse_date(safe_get(r, 0)) == last_date and get_text(safe_get(r, 3))]
            day = get_day_name(last_date, uid)
            response = f"📝 *{day} — {last_date}:*\n" + "─" * 25 + "\n"
            for r in rows:
                response += f"📌 {safe_get(r,1)}: {get_text(safe_get(r,3))}\n"
            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=main_menu(uid, admin=admin))

        elif text == t(uid, "prices"):
            seen = {}
            for r in data:
                s = safe_get(r, 1)
                p = get_text(safe_get(r, 4))
                if s and p and s not in seen:
                    seen[s] = p
            if not seen:
                has_any = any(safe_get(r, 1) for r in data)
                msg = t(uid, "no_exist") + " 💰" if has_any else t(uid, "unknown") + " 💰"
                bot.send_message(message.chat.id, msg, reply_markup=main_menu(uid, admin=admin))
                return
            response = "💰 *" + ("أسعار الملازم" if user_lang.get(uid, "ar") == "ar" else "Book Prices") + ":*\n" + "─" * 25 + "\n"
            for s, p in seen.items():
                response += f"📖 {s}: {p}\n"
            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=main_menu(uid, admin=admin))

        elif text == t(uid, "alerts"):
            alerts = [(safe_get(r,1), parse_date(safe_get(r,0)), get_text(safe_get(r,6)))
                      for r in data if get_text(safe_get(r,6))]
            if not alerts:
                bot.send_message(message.chat.id, t(uid, "no_alerts"), reply_markup=main_menu(uid, admin=admin))
                return
            response = "⚠️ *" + ("التنبيهات" if user_lang.get(uid, "ar") == "ar" else "Alerts") + ":*\n" + "─" * 25 + "\n"
            for s, d, a in alerts:
                response += f"🔔 {s} ({d}):\n{a}\n\n"
            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=main_menu(uid, admin=admin))

        else:
            bot.send_message(message.chat.id, t(uid, "choose_menu"), reply_markup=main_menu(uid, admin=admin))

    except Exception as e:
        bot.send_message(message.chat.id, t(uid, "error"))
        print(f"Error: {e}")

# ----- سيرفر بسيط لإبقاء البوت مستيقظاً -----
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
