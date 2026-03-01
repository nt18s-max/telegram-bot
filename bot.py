# Telegram Bot Project by Naif Saba
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import os
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv()

import logging
import requests as _requests

# ===== نظام Logging =====
LOG_BOT_TOKEN = os.environ.get("LOG_BOT_TOKEN", "")
LOG_CHAT_ID = ""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("BotLogger")

def tg_log(level, msg):
    """يرسل اللوج لبوت التيليغرام"""
    icons = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🚨"}
    icon = icons.get(level, "📋")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = f"{icon} *{level}*\n`{now}`\n\n{msg}"
    if LOG_BOT_TOKEN:
        # قراءة مباشرة من الشيت بدون دالة منفصلة
        recipients = []
        try:
            if users_sheet:
                rows = users_sheet.get_all_values()
                empty_streak = 0
                for row in rows[1:]:
                    if not row or not any(c.strip() for c in row):
                        empty_streak += 1
                        if empty_streak >= 5: break
                        continue
                    empty_streak = 0
                    uid_str = row[2].strip().lstrip("'") if len(row) > 2 else ""
                    log_val = row[7].strip().upper() if len(row) > 7 else "FALSE"
                    if uid_str.isdigit() and log_val == "TRUE":
                        recipients.append(int(uid_str))
        except:
            pass
        for chat_id in recipients:
            try:
                _requests.post(
                    f"https://api.telegram.org/bot{LOG_BOT_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                    timeout=5
                )
            except:
                pass
    getattr(logger, level.lower(), logger.info)(msg)

def log_info(msg):     tg_log("INFO", msg)
def log_warning(msg):  tg_log("WARNING", msg)
def log_error(msg):    tg_log("ERROR", msg)
def log_critical(msg): tg_log("CRITICAL", msg)

TOKEN = os.environ.get("BOT_TOKEN", "")
SHEET_KEY = os.environ.get("SHEET_KEY", "")

bot = telebot.TeleBot(TOKEN)

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
    log_critical(f"خطأ في الاتصال بـ Google Sheets: {e}")
    sheet = None
    users_sheet = None
    help_sheet = None
    rooms_sheet = None

user_state = {}
user_lang = {}
pending_requests = set()  # يتتبع من أرسل طلب انضمام في هذه الجلسة

def is_pending(uid):
    """يتحقق إذا المستخدم أرسل طلب من قبل - من الذاكرة أو الشيت"""
    if uid in pending_requests:
        return True
    try:
        rows = users_sheet.get_all_values()
        uid_str = str(uid)
        empty_streak = 0
        for row in rows[1:]:
            if not row or not any(c.strip() for c in row):
                empty_streak += 1
                if empty_streak >= 5: break
                continue
            empty_streak = 0
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                return True
    except:
        pass
    return False

DAYS_AR = {0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس", 4: "الجمعة", 5: "السبت", 6: "الأحد"}
DAYS_EN = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}

LANG = {
    "ar": {
        "subjects": "📚 المواد", "schedule": "🕐 أوقات المحاضرات", "tasks": "📝 التكاليف",
        "prices": "💰 أسعار الملازم", "alerts": "⚠️ تنبيهات", "back": "🔙 العودة",
        "upload_file": "📤 رفع ملف", "upload_help": "📹 رفع التعليمات", "broadcast": "📢 إرسال إشعار",
        "add_data": "➕ إضافة بيانات", "edit_data": "✏️ تعديل/حذف بيانات",
        "manage_users": "👥 إدارة المستخدمين",
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
        "choose_audience": "👥 هذه التعليمات لمن؟", "send_file_now": "📎 أرسل الملف:",
        "no_lectures": "📭 لا توجد محاضرات.", "no_tasks": "✅ لا يوجد تكاليف.",
        "no_prices": "لا توجد أسعار مسجلة.", "no_alerts": "✅ لا توجد تنبيهات.",
        "choose_data_type": "اختر نوع البيانات للإضافة:",
        "choose_edit_type": "اختر نوع البيانات للتعديل/الحذف:",
        "add_lecture": "🕐 إضافة محاضرة", "add_task": "📝 إضافة تكليف نصي",
        "add_summary": "📖 إضافة ملخص نصي", "add_price": "💰 إضافة سعر ملزمة", "add_alert": "⚠️ إضافة تنبيه",
        "edit_lecture": "🕐 تعديل/حذف محاضرة", "edit_task": "📝 تعديل/حذف تكليف",
        "edit_summary": "📖 تعديل/حذف ملخص", "edit_price": "💰 تعديل/حذف سعر", "edit_alert": "⚠️ تعديل/حذف تنبيه",
        "edit_btn": "✏️ تعديل", "delete_btn": "🗑 حذف",
        "current_val": "القيمة الحالية:", "enter_new_val": "أدخل القيمة الجديدة:",
        "deleted": "✅ تم الحذف!", "edited": "✅ تم التعديل!",
        "choose_building": "اختر المبنى:", "building_old": "🏛 القديم", "building_arts": "🏫 الاداب",
        "choose_room": "اختر القاعة:", "enter_time": "أدخل وقت المحاضرة:\nمثال: 08:00 - 09:30",
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
        "no_schedule": "لا توجد أوقات محاضرات لـ", "no_tasks_subj": "لا توجد تكاليف لـ",
        "no_summary": "لا توجد ملخصات لـ", "no_alerts_subj": "لا توجد تنبيهات لـ",
        "unknown": "غير معروف بعد", "no_exist": "لا يوجد",
        "user_list": "قائمة المستخدمين:", "no_users": "لا يوجد مستخدمون مسجلون.",
        "make_admin": "👑 ترقية لأدمن", "make_user": "👤 تحويل لمستخدم",
        "role_changed": "✅ تم تغيير الصلاحية!",
        "new_request": "📩 طلب انضمام جديد!\n\nالاسم: {name}\nالمعرف: {uid}",
        "approved": "✅ تمت الموافقة على طلبك! أرسل /start للبدء.",
        "rejected": "❌ تم رفض طلبك.",
        "pending": "⏳ تم إرسال طلبك، انتظر موافقة المالك.",
    },
    "en": {
        "subjects": "📚 Subjects", "schedule": "🕐 Schedule", "tasks": "📝 Tasks",
        "prices": "💰 Book Prices", "alerts": "⚠️ Alerts", "back": "🔙 Back",
        "upload_file": "📤 Upload File", "upload_help": "📹 Upload Tutorials", "broadcast": "📢 Send Notification",
        "add_data": "➕ Add Data", "edit_data": "✏️ Edit/Delete Data",
        "manage_users": "👥 Manage Users",
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
        "choose_audience": "👥 Who is this for?", "send_file_now": "📎 Send the file:",
        "no_lectures": "📭 No lectures.", "no_tasks": "✅ No tasks.",
        "no_prices": "No prices recorded.", "no_alerts": "✅ No alerts.",
        "choose_data_type": "Choose data type to add:",
        "choose_edit_type": "Choose data type to edit/delete:",
        "add_lecture": "🕐 Add Lecture", "add_task": "📝 Add Text Task",
        "add_summary": "📖 Add Text Summary", "add_price": "💰 Add Book Price", "add_alert": "⚠️ Add Alert",
        "edit_lecture": "🕐 Edit/Delete Lecture", "edit_task": "📝 Edit/Delete Task",
        "edit_summary": "📖 Edit/Delete Summary", "edit_price": "💰 Edit/Delete Price", "edit_alert": "⚠️ Edit/Delete Alert",
        "edit_btn": "✏️ Edit", "delete_btn": "🗑 Delete",
        "current_val": "Current value:", "enter_new_val": "Enter new value:",
        "deleted": "✅ Deleted!", "edited": "✅ Edited!",
        "choose_building": "Choose building:", "building_old": "🏛 Old Building", "building_arts": "🏫 Arts Building",
        "choose_room": "Choose room:", "enter_time": "Enter lecture time:\nExample: 08:00 - 09:30",
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
        "no_schedule": "No schedule for", "no_tasks_subj": "No tasks for",
        "no_summary": "No summaries for", "no_alerts_subj": "No alerts for",
        "unknown": "Unknown yet", "no_exist": "Does not exist",
        "user_list": "User list:", "no_users": "No registered users.",
        "make_admin": "👑 Promote to Admin", "make_user": "👤 Demote to User",
        "role_changed": "✅ Role changed!",
        "new_request": "📩 New join request!\n\nName: {name}\nID: {uid}",
        "approved": "✅ Your request was approved! Send /start to begin.",
        "rejected": "❌ Your request was rejected.",
        "pending": "⏳ Your request was sent, waiting for owner approval.",
    }
}

def t(uid, key):
    lang = user_lang.get(uid, "ar")
    return LANG[lang].get(key, LANG["ar"].get(key, key))

def load_user_lang(uid):
    """يقرأ اللغة من الشيت مرة واحدة ويحفظها في الذاكرة"""
    if uid not in user_lang:
        user_lang[uid] = get_user_lang_from_sheet(uid)

# ----- قراءة الإعدادات -----
def get_settings():
    try:
        rows = help_sheet.get_all_values()
        welcome = "مرحبًا! اختر أحد الخيارات:"
        rejection = "⛔ غير مسموح لك باستخدام البوت\n\nالرجاء طلب الصلاحية من منشئ البوت\n                         @nt18s"
        materials = []
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
        log_error(f"خطأ في جلب الإعدادات: {e}")
        return "مرحبًا! اختر أحد الخيارات:", "⛔ غير مسموح", []

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
        log_error(f"خطأ في جلب المواد: {e}")
        return []

def get_rooms(building):
    try:
        if not rooms_sheet:
            return []
        rows = rooms_sheet.get_all_values()
        return [row[1].strip() for row in rows if len(row) > 1 and row[0].strip() == building and row[1].strip()]
    except:
        return []

# ----- صلاحيات - الشيت الثاني: A=الاسم B=ID C=مسموح D=ادمن E=مالك F=English -----
def get_users():
    try:
        rows = users_sheet.get_all_values()
        allowed, admins, owners, log_ids = [], [], [], []
        open_all = admin_all = False
        empty_streak = 0
        for row in rows[1:]:
            if not row or not any(c.strip() for c in row):
                empty_streak += 1
                if empty_streak >= 5:
                    break
                continue
            empty_streak = 0
            name = row[0].strip()
            uid_str = row[2].strip() if len(row) > 2 else ""
            allowed_val = row[3].strip().upper() if len(row) > 3 else "FALSE"
            admin_val = row[4].strip().upper() if len(row) > 4 else "FALSE"
            owner_val = row[5].strip().upper() if len(row) > 5 else "FALSE"
            log_val = row[7].strip().upper() if len(row) > 7 else "FALSE"
            if name == "الكل":
                if allowed_val == "TRUE": open_all = True
                if admin_val == "TRUE": admin_all = True
                continue
            if not uid_str.isdigit():
                continue
            uid = int(uid_str)
            if allowed_val == "TRUE": allowed.append(uid)
            if admin_val == "TRUE": admins.append(uid)
            if owner_val == "TRUE": owners.append(uid)
            if log_val == "TRUE": log_ids.append(uid)
        return allowed, admins, owners, open_all, admin_all, log_ids
    except Exception as e:
        log_error(f"خطأ في جلب المستخدمين: {e}")
        return [], [], [], False, False, []

def get_user_lang_from_sheet(uid):
    """يقرأ اللغة من عمود F في الشيت"""
    try:
        rows = users_sheet.get_all_values()
        for row in rows[1:]:
            uid_str = row[2].strip() if len(row) > 2 else ""
            if uid_str.isdigit() and int(uid_str) == uid:
                lang_val = row[6].strip().upper() if len(row) > 6 else "FALSE"
                return "en" if lang_val == "TRUE" else "ar"
        return "ar"
    except:
        return "ar"

def save_user_lang_to_sheet(uid, lang):
    """يحفظ اللغة في عمود F"""
    try:
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            uid_str = row[2].strip() if len(row) > 2 else ""
            if uid_str.isdigit() and int(uid_str) == uid:
                users_sheet.update_cell(i, 7, lang == "en")
                return True
        return False
    except:
        return False

def get_all_user_ids():
    allowed, _, _, open_all, _ = get_users()
    return allowed, open_all

def get_all_registered_uids():
    """يجلب كل المعرفات المسجلة بما فيهم المضافون تلقائياً"""
    try:
        rows = users_sheet.get_all_values()
        uids = []
        empty_streak = 0
        for row in rows[1:]:
            if not row or not any(c.strip() for c in row):
                empty_streak += 1
                if empty_streak >= 5: break
                continue
            empty_streak = 0
            uid_str = row[2].strip() if len(row) > 2 else ""
            if uid_str.isdigit():
                uids.append(int(uid_str))
        return uids
    except:
        return []

def get_owner_ids():
    _, _, owners, _, _, _ = get_users()
    return owners

def check_user(message):
    allowed, _, _, open_all, _ = get_users()
    return open_all or message.from_user.id in allowed

def is_admin(message):
    _, admins, _, _, admin_all = get_users()
    return admin_all or message.from_user.id in admins

def is_owner_id(uid):
    return uid in get_owner_ids()

def is_owner(message):
    return is_owner_id(message.from_user.id)

def add_user_to_sheet(name, uid, auto=False):
    try:
        display_name = f"🆕 {name}" if auto else name
        users_sheet.append_row([display_name, "", uid, True, False, False, False, False], value_input_option="USER_ENTERED")
        return True
    except:
        return False

def auto_register_user(message, open_all=None):
    """يسجل المستخدم تلقائياً إذا البوت مفتوح للكل"""
    try:
        if open_all is None:
            _, _, _, open_all, _ = get_users()
        if not open_all:
            return
        rows = users_sheet.get_all_values()
        uid_str = str(message.from_user.id)
        for row in rows[1:]:
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                return  # موجود مسبقاً
        name = message.from_user.full_name or "مجهول"
        add_user_to_sheet(name, message.from_user.id, auto=True)
    except:
        pass

def update_user_role(uid, make_admin):
    try:
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            uid_str = row[2].strip() if len(row) > 2 else ""
            if uid_str.isdigit() and int(uid_str) == uid:
                users_sheet.update_cell(i, 5, make_admin)
                return True
        return False
    except:
        return False

# ----- مساعدات الخلية -----
def get_text(cell):
    return cell.split("|")[0].strip() if "|" in cell else cell.strip()

def get_file_id(cell):
    return cell.split("|")[1].strip() if "|" in cell else ""

def merge_cell(text, file_id):
    return f"{text}|{file_id}"

def get_day_name(date_str, uid):
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return DAYS_EN[dt.weekday()] if user_lang.get(uid, "ar") == "en" else DAYS_AR[dt.weekday()]
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

def is_valid_date(date_str):
    """يتحقق أن التاريخ صحيح ومقبول"""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            datetime.strptime(date_str.strip(), fmt)
            return True
        except ValueError:
            continue
    return False

def normalize_time(time_str):
    """يوحد تنسيق الوقت: 8:00–10:00 أو 8:00-10:00 → 08:00 - 10:00"""
    import re
    t = time_str.strip().replace("–", "-").replace("—", "-")
    # إزالة المسافات الزائدة حول -
    t = re.sub(r'\s*-\s*', ' - ', t)
    # إضافة صفر للأرقام المفردة مثل 8:00 → 08:00
    def pad_time(m):
        h, mi = m.group(1), m.group(2)
        return f"{int(h):02d}:{mi}"
    t = re.sub(r'(\d{1,2}):(\d{2})', pad_time, t)
    return t

def get_data():
    try:
        rows = sheet.get_all_values()[1:]
        # فلترة الصفوف التي تحتوي تاريخ ومادة فقط بدون أي بيانات أخرى
        useful = []
        for r in rows:
            has_time    = len(r) > 2 and r[2].strip()
            has_place   = len(r) > 3 and r[3].strip()
            has_task    = len(r) > 4 and r[4].strip()
            has_price   = len(r) > 5 and r[5].strip()
            has_summary = len(r) > 6 and r[6].strip()
            has_alert   = len(r) > 7 and r[7].strip()
            if has_time or has_place or has_task or has_price or has_summary or has_alert:
                useful.append(r)
        return useful
    except:
        return []

def send_today_date(chat_id, tomorrow=False, uid=None):
    dt = datetime.now() + timedelta(days=1) if tomorrow else datetime.now()
    d = dt.strftime("%d/%m/%Y")
    day_ar = DAYS_AR[dt.weekday()]
    label = "📅 مقترح (غداً):" if tomorrow else "📅 مقترح (اليوم):"
    bot.send_message(chat_id, f"{label} {day_ar}\n`{d}`", parse_mode="Markdown")

def save_file_to_cell(date, subject, col, file_id):
    try:
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) and parse_date(safe_get(row, 0)) == date and safe_get(row, 1) == subject:
                current = safe_get(row, col)
                text = get_text(current) if current else ""
                sheet.update_cell(i, col + 1, merge_cell(text, file_id))
                return True
        new_row = [""] * 8
        new_row[0] = date
        new_row[1] = subject
        new_row[col] = f"|{file_id}"
        sheet.append_row(new_row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        log_error(f"خطأ في حفظ الملف: {e}")
        return False

def save_text_to_cell(date, subject, col, text_val):
    try:
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) and parse_date(safe_get(row, 0)) == date and safe_get(row, 1) == subject:
                sheet.update_cell(i, col + 1, text_val)
                return True
        new_row = [""] * 8
        new_row[0] = date
        new_row[1] = subject
        new_row[col] = text_val
        sheet.append_row(new_row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        log_error(f"خطأ في حفظ البيانات: {e}")
        return False

def parse_time_range(time_str):
    """يحول '08:00 - 10:00' إلى (480, 600) دقائق"""
    import re
    t = normalize_time(time_str)
    sep = r'\s*-\s*'
    parts = re.split(sep, t)
    if len(parts) != 2:
        return None, None
    def to_minutes(s):
        s = s.strip()
        h, m = s.split(":") if ":" in s else (s, "0")
        return int(h) * 60 + int(m)
    try:
        return to_minutes(parts[0]), to_minutes(parts[1])
    except:
        return None, None

def check_lecture_conflict(date, time_val):
    """يتحقق من التداخل الزمني مع أي محاضرة في نفس اليوم"""
    try:
        new_start, new_end = parse_time_range(time_val)
        if new_start is None:
            return None
        rows = get_data()
        for row in rows:
            r_date = parse_date(safe_get(row, 0))
            r_time = safe_get(row, 2)
            if r_date != date or not r_time.strip():
                continue
            ex_start, ex_end = parse_time_range(r_time)
            if ex_start is None:
                continue
            # تحقق من التداخل: الجديد يبدأ قبل نهاية القديم والقديم يبدأ قبل نهاية الجديد
            if new_start < ex_end and ex_start < new_end:
                return {
                    "subject": safe_get(row, 1),
                    "room": safe_get(row, 3),
                    "time": normalize_time(r_time)
                }
    except:
        pass
    return None

def save_lecture(date, subject, time_val, room):
    """يحفظ وقت ومكان المحاضرة في نفس السطر دفعة واحدة"""
    try:
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) and parse_date(safe_get(row, 0)) == date and safe_get(row, 1) == subject:
                sheet.update_cell(i, 3, time_val)
                sheet.update_cell(i, 4, room)
                return True
        new_row = [""] * 8
        new_row[0] = date
        new_row[1] = subject
        new_row[2] = time_val
        new_row[3] = room
        sheet.append_row(new_row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        log_error(f"خطأ في حفظ المحاضرة: {e}")
        return False

def delete_cell(date, subject, col):
    try:
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) and parse_date(safe_get(row, 0)) == date and safe_get(row, 1) == subject:
                sheet.update_cell(i, col + 1, "")
                return True
        return False
    except:
        return False

def save_help_material(file_id, file_type, audience, note=""):
    try:
        rows = help_sheet.get_all_values()
        # أول سطر فارغ من السطر 3 فصاعداً (تجاوز صفي الإعدادات)
        next_row = max(4, len(rows) + 1)
        help_sheet.update([[file_id, file_type, audience, note]], f"B{next_row}:E{next_row}")
        help_sheet.update([["مادة مساعدة"]], f"A{next_row}")
        return True
    except Exception as e:
        log_error(f"خطأ في حفظ مادة المساعدة: {e}")
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
        fid, ftype, note = m["file_id"], m["file_type"], m["note"]
        if note:
            bot.send_message(chat_id, note)
        if fid:
            try:
                if ftype == "photo": bot.send_photo(chat_id, fid)
                elif ftype == "audio": bot.send_audio(chat_id, fid)
                elif ftype == "voice": bot.send_voice(chat_id, fid)
                elif ftype == "document": bot.send_document(chat_id, fid)
                elif ftype == "video": bot.send_video(chat_id, fid)
            except:
                try: bot.send_document(chat_id, fid)
                except: pass

def notify_owners_new_request(requester_id, requester_name):
    owners = get_owner_ids()
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("✅ قبول", callback_data=f"approve_{requester_id}_{requester_name}"),
        telebot.types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_{requester_id}")
    )
    msg = f"📩 طلب انضمام جديد!\n\n👤 الاسم: {requester_name}\n🆔 المعرف: {requester_id}"
    for owner_id in owners:
        try:
            bot.send_message(owner_id, msg, reply_markup=markup)
        except:
            pass

# ----- قوائم -----
def lang_menu():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🇾🇪 العربية", "🇬🇧 English")
    return markup

def main_menu(uid, admin=False, owner=False):
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
    if admin or owner:
        markup.add(t(uid, "add_data"))
        markup.add(t(uid, "edit_data"))
        markup.row(
            telebot.types.KeyboardButton(t(uid, "upload_help")),
            telebot.types.KeyboardButton(t(uid, "upload_file")),
            telebot.types.KeyboardButton(t(uid, "broadcast"))
        )
    if owner:
        markup.add(t(uid, "manage_users"))
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
    for k in ["subject_options_schedule", "subject_options_tasks", "subject_options_price",
               "subject_options_summary", "subject_options_alerts"]:
        markup.add(t(uid, k))
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
    markup.add(t(uid, "task_type"), t(uid, "summary_type"), t(uid, "back"))
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
    for k in ["add_lecture", "add_task", "add_summary", "add_price", "add_alert"]:
        markup.add(t(uid, k))
    markup.add(t(uid, "back"))
    return markup

def edit_data_menu(uid):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for k in ["edit_lecture", "edit_task", "edit_summary", "edit_price", "edit_alert"]:
        markup.add(t(uid, k))
    markup.add(t(uid, "back"))
    return markup

def edit_action_menu(uid):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(t(uid, "edit_btn"), t(uid, "delete_btn"))
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

def lecture_time_menu(uid):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🕐 08:00 - 10:00", "🕐 10:00 - 12:00")
    markup.add("🕐 12:00 - 14:00", "⏰ توقيت آخر")
    markup.add(t(uid, "back"))
    return markup

def back_only_with_no_exist_menu(uid):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(t(uid, "no_exist"), t(uid, "back"))
    return markup

def back_only_menu(uid):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(t(uid, "back"))
    return markup

def manage_users_menu(uid):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add("📋 قائمة المستخدمين")
    markup.add("🔄 تغيير صلاحية مستخدم")
    markup.add(t(uid, "back"))
    return markup

# ----- Callback handler للموافقة/الرفض -----
@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def handle_approval(call):
    caller_id = call.from_user.id
    if not is_owner_id(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح")
        return

    if call.data.startswith("approve_"):
        parts = call.data.split("_", 2)
        requester_id = int(parts[1])
        requester_name = parts[2] if len(parts) > 2 else "مستخدم"
        # ابحث عن السطر الموجود وحدّثه بدل إضافة سطر جديد
        try:
            rows = users_sheet.get_all_values()
            uid_str = str(requester_id)
            found = False
            empty_streak = 0
            for i, row in enumerate(rows[1:], start=2):
                if not row or not any(c.strip() for c in row):
                    empty_streak += 1
                    if empty_streak >= 5: break
                    continue
                empty_streak = 0
                cell_id = row[2].strip().lstrip("'") if len(row) > 2 else ""
                if cell_id == uid_str:
                    users_sheet.update_cell(i, 4, True)  # مسموح = TRUE
                    found = True
                    break
            if not found:
                add_user_to_sheet(requester_name, requester_id)
            pending_requests.discard(requester_id)
            try:
                bot.send_message(requester_id, LANG["ar"]["approved"])
            except:
                pass
            bot.edit_message_text(f"✅ تمت الموافقة على {requester_name} ({requester_id})",
                                  call.message.chat.id, call.message.message_id)
        except Exception as e:
            log_error(f"خطأ في الموافقة: {e}")
            bot.answer_callback_query(call.id, "❌ خطأ في الحفظ")

    elif call.data.startswith("reject_"):
        requester_id = int(call.data.split("_")[1])
        pending_requests.discard(requester_id)
        try:
            bot.send_message(requester_id, LANG["ar"]["rejected"])
        except:
            pass
        bot.edit_message_text(f"❌ تم رفض الطلب ({requester_id})",
                              call.message.chat.id, call.message.message_id)

    bot.answer_callback_query(call.id)

def _do_broadcast(chat_id, uid, admin, owner, text_msg, file_id, file_type):
    uids, open_all = get_all_user_ids()
    if open_all:
        registered = get_all_registered_uids()
        if registered:
            uids = registered
        # إذا لم يكن أحد مسجلاً نرسل لمن في القائمة العادية فقط
        if not uids:
            bot.send_message(chat_id, "⚠️ لا يوجد مستخدمون مسجلون بعد.")
            return
    success = fail = 0
    for user_id in uids:
        try:
            if text_msg:
                bot.send_message(user_id, "📢 *إشعار:*\n\n" + text_msg, parse_mode="Markdown")
            if file_id:
                if file_type == "photo": bot.send_photo(user_id, file_id)
                elif file_type == "audio": bot.send_audio(user_id, file_id)
                elif file_type == "voice": bot.send_voice(user_id, file_id)
                elif file_type == "video": bot.send_video(user_id, file_id)
                else: bot.send_document(user_id, file_id)
            success += 1
        except:
            fail += 1
    bot.send_message(chat_id, t(uid, 'broadcast_done') + f"\n✅ {success} | ❌ {fail}",
                     reply_markup=main_menu(uid, admin=admin, owner=owner))

# ----- /start -----
@bot.message_handler(commands=['start'])
def start_message(message):
    _, rejection, _ = get_settings()
    uid = message.from_user.id
    load_user_lang(uid)
    allowed_ids, admin_ids, owner_ids, open_all, admin_all, log_ids = get_users()
    is_allowed = open_all or uid in allowed_ids
    if not is_allowed:
        owners = owner_ids
        if owners:
            if not is_pending(uid):
                pending_requests.add(uid)
            bot.send_message(message.chat.id, rejection)
            contact_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            contact_markup.add(telebot.types.KeyboardButton("📱 مشاركة جهة الاتصال", request_contact=True))
            bot.send_message(message.chat.id, "📲 شارك جهة اتصالك لتسهيل التواصل معك:", reply_markup=contact_markup)
        else:
            bot.send_message(message.chat.id, rejection)
            contact_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            contact_markup.add(telebot.types.KeyboardButton("📱 مشاركة جهة الاتصال", request_contact=True))
            bot.send_message(message.chat.id, "📲 شارك جهة اتصالك لتسهيل التواصل معك:", reply_markup=contact_markup)
        return
    user_state.pop(uid, None)
    welcome, _, _ = get_settings()
    admin = admin_all or uid in admin_ids
    owner = uid in owner_ids
    log_info(f"START | uid={uid} | name={message.from_user.full_name} | admin={admin} | owner={owner}")
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin, owner=owner))

# ----- /lang -----
@bot.message_handler(commands=['lang'])
def language_command(message):
    _, rejection, _ = get_settings()
    if not check_user(message):
        bot.send_message(message.chat.id, rejection)
        return
    uid = message.from_user.id
    load_user_lang(uid)
    user_state[uid] = {"choosing_lang": True}
    bot.send_message(message.chat.id, "🌐 اختر اللغة / Choose Language", reply_markup=lang_menu())

# ----- /help -----
@bot.message_handler(commands=['help'])
def help_message(message):
    uid = message.from_user.id
    admin = is_admin(message) or is_owner(message)
    if admin:
        bot.send_message(message.chat.id, t(uid, "choose_lang"), reply_markup=help_view_menu(uid))
        user_state[uid] = {"viewing_help": True}
    else:
        send_help_materials(message.chat.id, uid, "user")

# ----- استقبال جهة الاتصال -----
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    uid = message.from_user.id
    contact = message.contact
    phone = contact.phone_number if contact else ""
    name = message.from_user.full_name or "مجهول"

    # إشعار المالك برسالة موحدة مع أزرار القبول/الرفض
    owners = get_owner_ids()
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("✅ قبول", callback_data=f"approve_{uid}_{name}"),
        telebot.types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_{uid}")
    )
    phone_line = f"📞 الرقم: `{phone}`\n" if phone else ""
    msg = f"📩 طلب انضمام جديد!\n\n👤 الاسم: `{name}`\n🆔 المعرف: `{uid}`\n{phone_line}"
    for owner_id in owners:
        try:
            bot.send_message(owner_id, msg, parse_mode="Markdown", reply_markup=markup)
        except:
            pass

    # حفظ الاسم + الرقم + الهاتف معاً — تحديث إذا موجود أو إضافة إذا جديد
    try:
        rows = users_sheet.get_all_values()
        uid_str = str(uid)
        found = False
        empty_streak = 0
        for i, row in enumerate(rows[1:], start=2):
            if not row or not any(c.strip() for c in row):
                empty_streak += 1
                if empty_streak >= 5: break
                continue
            empty_streak = 0
            cell_id = row[2].strip().lstrip("'") if len(row) > 2 else ""
            if cell_id == uid_str:
                # تحديث الاسم والهاتف في نفس الوقت
                users_sheet.update(f"A{i}:B{i}", [[name, phone]])
                found = True
                break
        if not found:
            # إضافة سطر جديد بالاسم والهاتف والـ ID بدون صلاحية
            users_sheet.append_row([name, phone, uid, False, False, False, False], value_input_option="USER_ENTERED")
    except Exception as e:
        log_error(f"خطأ في حفظ جهة الاتصال: {e}")

    bot.send_message(message.chat.id, "✅ شكراً! تم إرسال معلوماتك.", reply_markup=telebot.types.ReplyKeyboardRemove())

# ----- استقبال الملفات -----
@bot.message_handler(content_types=['document', 'photo', 'video', 'audio', 'voice'])
def handle_file(message):
    uid = message.from_user.id
    load_user_lang(uid)
    _, rejection, _ = get_settings()
    allowed_ids, admin_ids, owner_ids, open_all, admin_all, log_ids = get_users()
    is_allowed = open_all or uid in allowed_ids
    if not is_allowed:
        bot.send_message(message.chat.id, rejection)
        return
    auto_register_user(message, open_all=open_all)
    f_admin = admin_all or uid in admin_ids
    f_owner = uid in owner_ids
    if not (f_admin or f_owner):
        bot.send_message(message.chat.id, t(uid, "admin_only"))
        return

    state = user_state.get(uid, {})

    if message.document: file_id, ftype = message.document.file_id, "document"
    elif message.photo: file_id, ftype = message.photo[-1].file_id, "photo"
    elif message.video: file_id, ftype = message.video.file_id, "video"
    elif message.audio: file_id, ftype = message.audio.file_id, "audio"
    elif message.voice: file_id, ftype = message.voice.file_id, "voice"
    else: return

    if state.get("uploading_help") and state.get("step") == "waiting_file_help":
        audience = state.get("audience", "user")
        note = state.get("note", "")
        type_names = {"video": "الفيديو", "photo": "الصورة", "audio": "الصوت", "document": "الملف"}
        if save_help_material(file_id, ftype, audience, note):
            bot.send_message(message.chat.id, f"✅ تم حفظ {type_names.get(ftype, 'الملف')}!",
                             reply_markup=main_menu(uid, admin=f_admin, owner=f_owner))
        else:
            bot.send_message(message.chat.id, t(uid, "help_error"))
        user_state.pop(uid, None)
        return

    if state.get("broadcasting"):
        user_state[uid]["broadcast_file_id"] = file_id
        user_state[uid]["broadcast_file_type"] = ftype
        _do_broadcast(message.chat.id, uid, f_admin, f_owner,
                      state.get("broadcast_text", ""), file_id, ftype)
        user_state.pop(uid, None)
        return

    if state.get("uploading") and state.get("step") == "waiting_file":
        user_state[uid]["file_id"] = file_id
        user_state[uid]["step"] = "choose_subject"
        markup, _ = subjects_menu(uid)
        bot.send_message(message.chat.id, t(uid, "file_received"), reply_markup=markup)
        return

    bot.send_message(message.chat.id, t(uid, "send_file_first"), parse_mode="Markdown")

# ----- معالجة الرسائل -----
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    uid = message.from_user.id
    load_user_lang(uid)
    # جلب كل شيء مرة واحدة
    welcome_msg, rejection, materials = get_settings()
    allowed_ids, admin_ids, owner_ids, open_all, admin_all, log_ids = get_users()
    is_allowed = open_all or uid in allowed_ids
    admin = admin_all or uid in admin_ids
    owner = uid in owner_ids

    if not is_allowed:
        contact_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        contact_markup.add(telebot.types.KeyboardButton("📱 مشاركة جهة الاتصال", request_contact=True))
        if owner_ids:
            if not is_pending(uid):
                pending_requests.add(uid)
            bot.send_message(message.chat.id, rejection)
            bot.send_message(message.chat.id, "📲 شارك جهة اتصالك لتسهيل التواصل معك:", reply_markup=contact_markup)
        else:
            bot.send_message(message.chat.id, rejection)
            bot.send_message(message.chat.id, "📲 شارك جهة اتصالك لتسهيل التواصل معك:", reply_markup=contact_markup)
        return
    if sheet is None:
        bot.send_message(message.chat.id, "❌ لا يوجد اتصال بقاعدة البيانات.")
        return

    auto_register_user(message, open_all=open_all)
    text = message.text
    state = user_state.get(uid, {})
    back_btn = t(uid, "back")

    try:
        # جلب البيانات مرة واحدة لكل الرسالة
        subjects_markup, subjects_list = subjects_menu(uid)
        data = get_data()

        # ===== اختيار اللغة =====
        if state.get("choosing_lang") or text in ["🇾🇪 العربية", "🇬🇧 English"]:
            if text == "🇾🇪 العربية": user_lang[uid] = "ar"
            elif text == "🇬🇧 English": user_lang[uid] = "en"
            else:
                bot.send_message(message.chat.id, "🌐 اختر اللغة / Choose Language", reply_markup=lang_menu())
                return
            user_state.pop(uid, None)
            save_user_lang_to_sheet(uid, user_lang.get(uid, "ar"))
            bot.send_message(message.chat.id, welcome_msg, reply_markup=main_menu(uid, admin=admin, owner=owner))
            return

        # ===== عرض تعليمات البوت =====
        if state.get("viewing_help"):
            if text == t(uid, "view_user_help"):
                send_help_materials(message.chat.id, uid, "user")
                user_state.pop(uid, None)
                bot.send_message(message.chat.id, t(uid, "choose_lang"), reply_markup=main_menu(uid, admin=admin, owner=owner))
            elif text == t(uid, "view_admin_help"):
                send_help_materials(message.chat.id, uid, "admin")
                user_state.pop(uid, None)
                bot.send_message(message.chat.id, t(uid, "choose_lang"), reply_markup=main_menu(uid, admin=admin, owner=owner))
            else:
                bot.send_message(message.chat.id, t(uid, "choose_lang"), reply_markup=help_view_menu(uid))
            return

        # ===== إدارة المستخدمين (مالك) =====
        if text == t(uid, "manage_users"):
            if not owner:
                bot.send_message(message.chat.id, t(uid, "admin_only"))
                return
            user_state[uid] = {"managing_users": True, "step": "menu"}
            bot.send_message(message.chat.id, "👥 إدارة المستخدمين:", reply_markup=manage_users_menu(uid))
            return

        if state.get("managing_users"):
            step = state.get("step")

            if text == "📋 قائمة المستخدمين":
                rows = users_sheet.get_all_values()
                if len(rows) <= 1:
                    bot.send_message(message.chat.id, t(uid, "no_users"))
                    return
                response = "👥 *قائمة المستخدمين:*\n" + "─" * 25 + "\n"
                for row in rows[1:]:
                    name = row[0].strip() if row else ""
                    uid_str = row[2].strip() if len(row) > 2 else ""
                    allowed = row[3].strip().upper() if len(row) > 3 else "FALSE"
                    adm = row[4].strip().upper() if len(row) > 4 else "FALSE"
                    own = row[5].strip().upper() if len(row) > 5 else "FALSE"
                    if not name or name == "الكل": continue
                    role = "👸 مالك" if own == "TRUE" else ("👑 أدمن" if adm == "TRUE" else "👤 مستخدم")
                    status = "✅" if allowed == "TRUE" else "❌"
                    response += f"{status} {name} ({uid_str}) — {role}\n"
                bot.send_message(message.chat.id, response, parse_mode="Markdown")
                return

            if text == "🔄 تغيير صلاحية مستخدم":
                user_state[uid]["step"] = "enter_uid_role"
                bot.send_message(message.chat.id, "أدخل معرف المستخدم (ID):", reply_markup=back_only_menu(uid))
                return

            if step == "enter_uid_role":
                if text == back_btn:
                    user_state[uid] = {"managing_users": True, "step": "menu"}
                    bot.send_message(message.chat.id, "👥 إدارة المستخدمين:", reply_markup=manage_users_menu(uid))
                    return
                if text.isdigit():
                    user_state[uid]["target_uid"] = int(text)
                    user_state[uid]["step"] = "choose_role"
                    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                    markup.add(t(uid, "make_admin"), t(uid, "make_user"), t(uid, "back"))
                    bot.send_message(message.chat.id, "اختر الصلاحية الجديدة:", reply_markup=markup)
                else:
                    bot.send_message(message.chat.id, "❌ أدخل معرفاً رقمياً صحيحاً.")
                return

            if step == "choose_role":
                target = state.get("target_uid")
                if text == t(uid, "make_admin"):
                    if update_user_role(target, True):
                        bot.send_message(message.chat.id, t(uid, "role_changed"), reply_markup=manage_users_menu(uid))
                    else:
                        bot.send_message(message.chat.id, t(uid, "error"))
                elif text == t(uid, "make_user"):
                    if update_user_role(target, False):
                        bot.send_message(message.chat.id, t(uid, "role_changed"), reply_markup=manage_users_menu(uid))
                    else:
                        bot.send_message(message.chat.id, t(uid, "error"))
                user_state[uid] = {"managing_users": True, "step": "menu"}
                return

        # ===== العودة =====
        if text == back_btn:
            if any(state.get(k) for k in ["uploading", "uploading_help", "viewing_help", "broadcasting",
                                            "adding_data", "editing_data", "managing_users"]):
                user_state.pop(uid, None)
                bot.send_message(message.chat.id, welcome_msg, reply_markup=main_menu(uid, admin=admin, owner=owner))
                return
            if state.get("awaiting_date"):
                subj = state["subject"]
                user_state[uid] = {"subject": subj}
                bot.send_message(message.chat.id, f"📌 {subj}\n{t(uid, 'choose_option')}",
                                 reply_markup=subject_options_menu(uid))
                return
            if state.get("subject"):
                user_state.pop(uid, None)
                markup, _ = subjects_menu(uid)
                bot.send_message(message.chat.id, t(uid, "choose_subject"), reply_markup=markup)
                return
            user_state.pop(uid, None)
            bot.send_message(message.chat.id, welcome_msg, reply_markup=main_menu(uid, admin=admin, owner=owner))
            return

        # ===== إرسال إشعار =====
        if text == t(uid, "broadcast"):
            if not (admin or owner):
                bot.send_message(message.chat.id, t(uid, "admin_only"))
                return
            user_state[uid] = {"broadcasting": True, "step": "waiting_text"}
            markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            markup.add("📤 إرسال بدون نص", t(uid, "back"))
            bot.send_message(message.chat.id, "اكتب نص الإشعار أو اضغط إرسال بدون نص:", reply_markup=markup)
            return

        if state.get("broadcasting"):
            step = state.get("step", "waiting_text")
            if step == "waiting_text":
                if text == "📤 إرسال بدون نص":
                    user_state[uid]["broadcast_text"] = ""
                    user_state[uid]["step"] = "waiting_file_or_send"
                    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                    markup.add("📤 إرسال الآن", t(uid, "back"))
                    bot.send_message(message.chat.id, "أرسل ملفاً أو اضغط إرسال الآن:", reply_markup=markup)
                else:
                    user_state[uid]["broadcast_text"] = text
                    user_state[uid]["step"] = "waiting_file_or_send"
                    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                    markup.add("📤 إرسال الآن", t(uid, "back"))
                    bot.send_message(message.chat.id, "أرسل ملفاً (اختياري) أو اضغط إرسال الآن:", reply_markup=markup)
                return
            if step == "waiting_file_or_send":
                if text == "📤 إرسال الآن":
                    _do_broadcast(message.chat.id, uid, admin, owner,
                                  state.get("broadcast_text", ""),
                                  state.get("broadcast_file_id"), state.get("broadcast_file_type"))
                    user_state.pop(uid, None)
                return

        # ===== رفع التعليمات =====
        if text == t(uid, "upload_help"):
            if not (admin or owner):
                bot.send_message(message.chat.id, t(uid, "admin_only"))
                return
            user_state[uid] = {"uploading_help": True, "step": "choose_audience"}
            bot.send_message(message.chat.id, t(uid, "choose_audience"), reply_markup=help_audience_menu(uid))
            return

        if state.get("uploading_help"):
            step = state.get("step")
            if step == "choose_audience":
                if text == t(uid, "for_users"): user_state[uid]["audience"] = "user"
                elif text == t(uid, "for_admins"): user_state[uid]["audience"] = "admin"
                else: return
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
                audience = state.get("audience", "user")
                note = state.get("note", "")
                if save_help_material("", "text", audience, text):
                    bot.send_message(message.chat.id, t(uid, "help_saved"),
                                     reply_markup=main_menu(uid, admin=admin, owner=owner))
                else:
                    bot.send_message(message.chat.id, t(uid, "help_error"))
                user_state.pop(uid, None)
                return

        # ===== رفع ملف عادي =====
        if text == t(uid, "upload_file"):
            if not (admin or owner):
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
            _, subjects_list = subjects_menu(uid)
            if step == "choose_subject" and text in subjects_list:
                user_state[uid]["subject"] = text
                user_state[uid]["step"] = "choose_type"
                bot.send_message(message.chat.id, f"📌 *{text}*", parse_mode="Markdown", reply_markup=file_type_menu(uid))
                return
            if step == "choose_type" and text in [t(uid, "task_type"), t(uid, "summary_type")]:
                col = 4 if text == t(uid, "task_type") else 6
                user_state[uid]["col"] = col
                user_state[uid]["file_type"] = text
                user_state[uid]["step"] = "choose_date"
                bot.send_message(message.chat.id, t(uid, "enter_date"))
                send_today_date(message.chat.id)
                return
            if step == "choose_date":
                if not is_valid_date(text):
                    bot.send_message(message.chat.id, "❌ صيغة التاريخ غير صحيحة.\n`مثال: 27/02/2026`", parse_mode="Markdown")
                    send_today_date(message.chat.id)
                    return
                date = parse_date(text)
                if save_file_to_cell(date, state.get("subject"), state.get("col"), state.get("file_id")):
                    log_info(f"FILE_SAVED | uid={uid} | subject={state.get('subject')} | type={state.get('file_type')} | date={date}")
                    bot.send_message(message.chat.id,
                                     f"{t(uid, 'file_saved')}\n\n📌 *{state.get('subject')}*\n{state.get('file_type')}\n📅 {date}",
                                     parse_mode="Markdown", reply_markup=main_menu(uid, admin=admin, owner=owner))
                else:
                    bot.send_message(message.chat.id, t(uid, "file_error"))
                user_state.pop(uid, None)
                return

        # ===== إضافة بيانات =====
        if text == t(uid, "add_data"):
            if not (admin or owner):
                bot.send_message(message.chat.id, t(uid, "admin_only"))
                return
            user_state[uid] = {"adding_data": True, "step": "choose_type"}
            bot.send_message(message.chat.id, t(uid, "choose_data_type"), reply_markup=add_data_menu(uid))
            return

        if state.get("adding_data"):
            step = state.get("step")
            data_types = {t(uid, k): v for k, v in [("add_lecture","lecture"),("add_task","task"),
                          ("add_summary","summary"),("add_price","price"),("add_alert","alert")]}

            if step == "choose_type" and text in data_types:
                user_state[uid]["data_type"] = data_types[text]
                dtype = data_types[text]
                if dtype == "lecture":
                    # ترتيب جديد للمحاضرة: تاريخ ← مبنى ← قاعة ← مادة ← وقت
                    user_state[uid]["step"] = "enter_date"
                    bot.send_message(message.chat.id, t(uid, "enter_date"), reply_markup=back_only_menu(uid))
                    send_today_date(message.chat.id, tomorrow=True)
                elif dtype == "price":
                    user_state[uid]["step"] = "choose_subject"
                    bot.send_message(message.chat.id, t(uid, "choose_subject"), reply_markup=subjects_markup)
                else:
                    user_state[uid]["step"] = "choose_subject"
                    bot.send_message(message.chat.id, t(uid, "choose_subject"), reply_markup=subjects_markup)
                return

            if step == "enter_date":
                dtype = state.get("data_type")
                if not is_valid_date(text):
                    bot.send_message(message.chat.id, "❌ صيغة التاريخ غير صحيحة.\n`مثال: 27/02/2026`", parse_mode="Markdown")
                    send_today_date(message.chat.id, tomorrow=(dtype == "lecture"))
                    return
                date = parse_date(text)
                user_state[uid]["date"] = date
                if dtype == "lecture":
                    user_state[uid]["step"] = "choose_building"
                    bot.send_message(message.chat.id, t(uid, "choose_building"), reply_markup=buildings_menu(uid))
                elif dtype == "alert":
                    user_state[uid]["step"] = "enter_value"
                    bot.send_message(message.chat.id, t(uid, "enter_alert") + "\n`مثال: الاختبار يوم الخميس`", parse_mode="Markdown", reply_markup=back_only_with_no_exist_menu(uid))
                elif dtype == "task":
                    user_state[uid]["step"] = "enter_value"
                    bot.send_message(message.chat.id, t(uid, "enter_task") + "\n`مثال: حل تمارين الفصل 3`", parse_mode="Markdown", reply_markup=back_only_with_no_exist_menu(uid))
                elif dtype == "summary":
                    user_state[uid]["step"] = "enter_value"
                    bot.send_message(message.chat.id, "أدخل نص الملخص:\n`مثال: ملخص الفصل الأول`", parse_mode="Markdown", reply_markup=back_only_with_no_exist_menu(uid))
                return

            if step == "choose_building":
                building_map = {t(uid, "building_old"): "القديم", t(uid, "building_arts"): "الاداب"}
                if text in building_map:
                    bkey = building_map[text]
                    user_state[uid]["building"] = bkey
                    user_state[uid]["building_label"] = text
                    markup, rooms = rooms_menu(uid, bkey)
                    if not rooms:
                        bot.send_message(message.chat.id, t(uid, "no_rooms"))
                        return
                    user_state[uid]["step"] = "choose_room"
                    bot.send_message(message.chat.id, t(uid, "choose_room"), reply_markup=markup)
                return

            if step == "choose_room":
                user_state[uid]["room"] = f"{state.get('building_label', '')}: {text}"
                user_state[uid]["step"] = "choose_subject"
                bot.send_message(message.chat.id, t(uid, "choose_subject"), reply_markup=subjects_markup)
                return

            if step == "choose_subject" and text in subjects_list:
                user_state[uid]["subject"] = text
                dtype = state.get("data_type")
                if dtype == "lecture":
                    user_state[uid]["step"] = "enter_time"
                    bot.send_message(message.chat.id, "اختر وقت المحاضرة أو أدخل توقيتاً خاصاً:", reply_markup=lecture_time_menu(uid))
                elif dtype == "price":
                    user_state[uid]["step"] = "enter_value"
                    bot.send_message(message.chat.id, t(uid, "enter_price") + "\n`25 ريال`", parse_mode="Markdown", reply_markup=back_only_with_no_exist_menu(uid))
                return

            if step == "enter_time":
                time_options = {"🕐 08:00 - 10:00": "08:00 - 10:00", "🕐 10:00 - 12:00": "10:00 - 12:00", "🕐 12:00 - 14:00": "12:00 - 14:00"}
                if text in time_options:
                    user_state[uid]["time_val"] = time_options[text]
                elif text == "⏰ توقيت آخر":
                    bot.send_message(message.chat.id, "أدخل الوقت:\n`08:00 - 09:30`", parse_mode="Markdown", reply_markup=back_only_with_no_exist_menu(uid))
                    user_state[uid]["step"] = "enter_time_custom"
                    return
                else:
                    user_state[uid]["time_val"] = t(uid, "no_exist") if text == t(uid, "no_exist") else normalize_time(text)
                # تحقق من التعارض ثم حفظ
                subject = state.get("subject")
                date = state.get("date", "")
                room = state.get("room", "")
                time_val = normalize_time(user_state[uid].get("time_val", ""))
                conflict = check_lecture_conflict(date, time_val)
                if conflict:
                    user_state[uid]["step"] = "confirm_lecture_overwrite"
                    user_state[uid]["time_val"] = time_val
                    conflict_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
                    conflict_markup.add("🔄 استبدال", t(uid, "back"))
                    bot.send_message(message.chat.id,
                        f"⚠️ تداخل في الوقت!\n\n📌 {conflict['subject']}\n🕐 {conflict['time']}\n📍 {conflict['room']}\n\nالوقت الجديد `{time_val}` يتداخل معها.\n\nماذا تريد؟",
                        parse_mode="Markdown", reply_markup=conflict_markup)
                elif save_lecture(date, subject, time_val, room):
                    log_info(f"LECTURE_SAVED | uid={uid} | subject={subject} | date={date} | time={time_val} | room={room}")
                    add_another_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
                    add_another_markup.add("➕ إضافة محاضرة أخرى", t(uid, "back"))
                    user_state[uid]["step"] = "lecture_done"
                    bot.send_message(message.chat.id, f"✅ تم حفظ المحاضرة!\n\n📌 {subject}\n📅 {date}\n🕐 {time_val}\n📍 {room}", reply_markup=add_another_markup)
                else:
                    log_error(f"LECTURE_SAVE_FAILED | uid={uid} | subject={subject}")
                    bot.send_message(message.chat.id, t(uid, "data_error"))
                    user_state.pop(uid, None)
                return

            if step == "enter_time_custom":
                user_state[uid]["time_val"] = t(uid, "no_exist") if text == t(uid, "no_exist") else normalize_time(text)
                subject = state.get("subject")
                date = state.get("date", "")
                room = state.get("room", "")
                time_val = normalize_time(user_state[uid]["time_val"])
                conflict = check_lecture_conflict(date, time_val)
                if conflict:
                    user_state[uid]["step"] = "confirm_lecture_overwrite"
                    user_state[uid]["time_val"] = time_val
                    conflict_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
                    conflict_markup.add("🔄 استبدال", t(uid, "back"))
                    bot.send_message(message.chat.id,
                        f"⚠️ تداخل في الوقت!\n\n📌 {conflict['subject']}\n🕐 {conflict['time']}\n📍 {conflict['room']}\n\nالوقت الجديد `{time_val}` يتداخل معها.\n\nماذا تريد؟",
                        parse_mode="Markdown", reply_markup=conflict_markup)
                elif save_lecture(date, subject, time_val, room):
                    log_info(f"LECTURE_SAVED | uid={uid} | subject={subject} | date={date} | time={time_val} | room={room}")
                    add_another_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
                    add_another_markup.add("➕ إضافة محاضرة أخرى", t(uid, "back"))
                    user_state[uid]["step"] = "lecture_done"
                    bot.send_message(message.chat.id, f"✅ تم حفظ المحاضرة!\n\n📌 {subject}\n📅 {date}\n🕐 {time_val}\n📍 {room}", reply_markup=add_another_markup)
                else:
                    log_error(f"LECTURE_SAVE_FAILED | uid={uid} | subject={subject}")
                    bot.send_message(message.chat.id, t(uid, "data_error"))
                    user_state.pop(uid, None)
                return

            if step == "confirm_lecture_overwrite":
                subject = state.get("subject")
                date = state.get("date", "")
                room = state.get("room", "")
                time_val = state.get("time_val", "")
                if text == "🔄 استبدال":
                    if save_lecture(date, subject, time_val, room):
                        log_info(f"LECTURE_REPLACED | uid={uid} | subject={subject} | date={date} | time={time_val}")
                        add_another_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
                        add_another_markup.add("➕ إضافة محاضرة أخرى", t(uid, "back"))
                        user_state[uid]["step"] = "lecture_done"
                        bot.send_message(message.chat.id, f"✅ تم استبدال المحاضرة!\n\n📌 {subject}\n📅 {date}\n🕐 {time_val}\n📍 {room}", reply_markup=add_another_markup)
                    else:
                        bot.send_message(message.chat.id, t(uid, "data_error"))
                        user_state.pop(uid, None)
                return

            if step == "lecture_done":
                if text == "➕ إضافة محاضرة أخرى":
                    saved_date = state.get("date", "")
                    saved_room = state.get("room", "")
                    saved_building = state.get("building", "")
                    saved_building_label = state.get("building_label", "")
                    user_state[uid] = {
                        "adding_data": True, "step": "choose_subject",
                        "data_type": "lecture",
                        "date": saved_date, "room": saved_room,
                        "building": saved_building, "building_label": saved_building_label,
                        "from_add_another": True  # رجوع من المادة يروح للمبنى
                    }
                    bot.send_message(message.chat.id, t(uid, "choose_subject"), reply_markup=subjects_markup)
                    return

            if step == "confirm_overwrite":
                subject = state.get("subject")
                date = state.get("date", "")
                dtype = state.get("data_type")
                existing = state.get("existing_val", "")
                new_val = state.get("pending_val", "")
                col = {"task": 4, "summary": 6, "alert": 7}.get(dtype, 4)
                if text == "✏️ بجانبه":
                    combined = existing + " | " + new_val
                    ok = save_text_to_cell(date, subject, col, combined)
                    if ok: log_info(f"{dtype.upper()}_APPENDED | uid={uid} | subject={subject} | date={date}")
                    bot.send_message(message.chat.id, t(uid, "data_saved") if ok else t(uid, "data_error"),
                                     reply_markup=main_menu(uid, admin=admin, owner=owner))
                elif text == "🔄 بدله":
                    ok = save_text_to_cell(date, subject, col, new_val)
                    if ok: log_info(f"{dtype.upper()}_REPLACED | uid={uid} | subject={subject} | date={date}")
                    bot.send_message(message.chat.id, t(uid, "data_saved") if ok else t(uid, "data_error"),
                                     reply_markup=main_menu(uid, admin=admin, owner=owner))
                else:
                    bot.send_message(message.chat.id, t(uid, "choose_menu"), reply_markup=main_menu(uid, admin=admin, owner=owner))
                user_state.pop(uid, None)
                return

            if step == "enter_value":
                subject = state.get("subject")
                date = state.get("date", "")
                dtype = state.get("data_type")
                val = text

                # تحقق من وجود قيمة سابقة لـ task/summary/alert
                if dtype in ("task", "summary", "alert"):
                    col = {"task": 4, "summary": 6, "alert": 7}[dtype]
                    existing_rows = get_data()
                    matched = [r for r in existing_rows if safe_get(r, 1) == subject and parse_date(safe_get(r, 0)) == date]
                    existing_val = get_text(safe_get(matched[0], col)) if matched else ""
                    if existing_val and existing_val.strip():
                        user_state[uid]["step"] = "confirm_overwrite"
                        user_state[uid]["existing_val"] = existing_val
                        user_state[uid]["pending_val"] = val
                        overwrite_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
                        overwrite_markup.add("✏️ بجانبه", "🔄 بدله")
                        overwrite_markup.add(t(uid, "back"))
                        bot.send_message(message.chat.id,
                                         f"⚠️ يوجد مدخل سابق:\n`{existing_val}`\n\nماذا تريد؟",
                                         parse_mode="Markdown", reply_markup=overwrite_markup)
                        return

                if dtype == "price":
                    rows = sheet.get_all_values()
                    updated = False
                    for i, row in enumerate(rows[1:], start=2):
                        if safe_get(row, 1) == subject:
                            sheet.update_cell(i, 6, val)
                            updated = True
                            break
                    if not updated:
                        sheet.append_row(["", subject, "", "", "", val, "", ""], value_input_option="USER_ENTERED")
                    log_info(f"PRICE_SAVED | uid={uid} | subject={subject} | val={val}")
                    bot.send_message(message.chat.id, t(uid, "data_saved"), reply_markup=main_menu(uid, admin=admin, owner=owner))
                elif dtype == "task":
                    ok = save_text_to_cell(date, subject, 4, val)
                    if ok: log_info(f"TASK_SAVED | uid={uid} | subject={subject} | date={date} | val={val}")
                    bot.send_message(message.chat.id, t(uid, "data_saved") if ok else t(uid, "data_error"),
                                     reply_markup=main_menu(uid, admin=admin, owner=owner))
                elif dtype == "summary":
                    ok = save_text_to_cell(date, subject, 6, val)
                    if ok: log_info(f"SUMMARY_SAVED | uid={uid} | subject={subject} | date={date} | val={val}")
                    bot.send_message(message.chat.id, t(uid, "data_saved") if ok else t(uid, "data_error"),
                                     reply_markup=main_menu(uid, admin=admin, owner=owner))
                elif dtype == "alert":
                    ok = save_text_to_cell(date, subject, 7, val)
                    if ok: log_info(f"ALERT_SAVED | uid={uid} | subject={subject} | date={date} | val={val}")
                    bot.send_message(message.chat.id, t(uid, "data_saved") if ok else t(uid, "data_error"),
                                     reply_markup=main_menu(uid, admin=admin, owner=owner))
                user_state.pop(uid, None)
                return

            # fallback - أعد عرض القائمة الحالية
            return

        # ===== تعديل/حذف بيانات =====
        if text == t(uid, "edit_data"):
            if not (admin or owner):
                bot.send_message(message.chat.id, t(uid, "admin_only"))
                return
            user_state[uid] = {"editing_data": True, "step": "choose_type"}
            bot.send_message(message.chat.id, t(uid, "choose_edit_type"), reply_markup=edit_data_menu(uid))
            return

        if state.get("editing_data"):
            step = state.get("step")
            edit_types = {t(uid, k): v for k, v in [("edit_lecture","lecture"),("edit_task","task"),
                          ("edit_summary","summary"),("edit_price","price"),("edit_alert","alert")]}
            col_map_edit = {"lecture": 2, "task": 4, "summary": 6, "price": 5, "alert": 7}

            if step == "choose_type" and text in edit_types:
                user_state[uid]["data_type"] = edit_types[text]
                user_state[uid]["step"] = "choose_subject"
                markup, _ = subjects_menu(uid)
                bot.send_message(message.chat.id, t(uid, "choose_subject"), reply_markup=markup)
                return

            if step == "choose_subject" and text in subjects_list:
                user_state[uid]["subject"] = text
                dtype = state.get("data_type")
                if dtype == "price":
                    rows = [r for r in data if safe_get(r, 1) == text]
                    current = next((get_text(safe_get(r, 5)) for r in rows if safe_get(r, 5)), "")
                    user_state[uid]["step"] = "choose_action"
                    user_state[uid]["current_val"] = current
                    user_state[uid]["date"] = ""
                    bot.send_message(message.chat.id, f"{t(uid, 'current_val')} *{current or 'فارغ'}*",
                                     parse_mode="Markdown", reply_markup=edit_action_menu(uid))
                else:
                    user_state[uid]["step"] = "choose_date_edit"
                    col = col_map_edit.get(dtype, 2)
                    rows = [r for r in data if safe_get(r, 1) == text]
                    dates = list(dict.fromkeys(
                        parse_date(safe_get(r, 0)) for r in rows
                        if get_text(safe_get(r, col)) and safe_get(r, 0)
                    ))
                    if not dates:
                        bot.send_message(message.chat.id, t(uid, "no_data"), reply_markup=edit_data_menu(uid))
                        user_state[uid] = {"editing_data": True, "step": "choose_type"}
                        return
                    user_state[uid]["col"] = col
                    bot.send_message(message.chat.id, t(uid, "choose_date"), reply_markup=dates_menu(uid, dates))
                return

            if step == "choose_date_edit":
                subj = state.get("subject")
                col = state.get("col", 2)
                matched = [r for r in data if safe_get(r, 1) == subj and parse_date(safe_get(r, 0)) == text]
                if not matched:
                    bot.send_message(message.chat.id, t(uid, "no_data"))
                    return
                current = get_text(safe_get(matched[0], col))
                user_state[uid]["date"] = text
                user_state[uid]["current_val"] = current
                user_state[uid]["step"] = "choose_action"
                bot.send_message(message.chat.id, f"{t(uid, 'current_val')} *{current or 'فارغ'}*",
                                 parse_mode="Markdown", reply_markup=edit_action_menu(uid))
                return

            if step == "choose_action":
                if text == t(uid, "edit_btn"):
                    user_state[uid]["step"] = "enter_new_val"
                    bot.send_message(message.chat.id, t(uid, "enter_new_val"), reply_markup=back_only_menu(uid))
                elif text == t(uid, "delete_btn"):
                    user_state[uid]["step"] = "confirm_delete"
                    current = state.get("current_val", "")
                    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                    markup.add("✅ نعم، احذف", "❌ لا، إلغاء")
                    bot.send_message(message.chat.id,
                                     "⚠️ هل أنت متأكد من حذف:\n*" + current + "*؟",
                                     parse_mode="Markdown", reply_markup=markup)
                return

            if step == "confirm_delete":
                if text == "✅ نعم، احذف":
                    subj = state.get("subject")
                    date = state.get("date", "")
                    dtype = state.get("data_type")
                    col = col_map_edit.get(dtype, 2)
                    if dtype == "price":
                        rows = sheet.get_all_values()
                        for i, row in enumerate(rows[1:], start=2):
                            if safe_get(row, 1) == subj:
                                sheet.update_cell(i, 6, "")
                                break
                        bot.send_message(message.chat.id, t(uid, "deleted"), reply_markup=main_menu(uid, admin=admin, owner=owner))
                    else:
                        if delete_cell(date, subj, col):
                            bot.send_message(message.chat.id, t(uid, "deleted"), reply_markup=main_menu(uid, admin=admin, owner=owner))
                        else:
                            bot.send_message(message.chat.id, t(uid, "error"))
                    user_state.pop(uid, None)
                elif text == "❌ لا، إلغاء":
                    user_state[uid]["step"] = "choose_action"
                    bot.send_message(message.chat.id, "تم الإلغاء.", reply_markup=edit_action_menu(uid))
                return

            if step == "enter_new_val":
                subj = state.get("subject")
                date = state.get("date", "")
                dtype = state.get("data_type")
                col = col_map_edit.get(dtype, 2)
                if dtype == "price":
                    rows = sheet.get_all_values()
                    for i, row in enumerate(rows[1:], start=2):
                        if safe_get(row, 1) == subj:
                            sheet.update_cell(i, 6, text)
                            break
                    bot.send_message(message.chat.id, t(uid, "edited"), reply_markup=main_menu(uid, admin=admin, owner=owner))
                else:
                    if save_text_to_cell(date, subj, col, text):
                        bot.send_message(message.chat.id, t(uid, "edited"), reply_markup=main_menu(uid, admin=admin, owner=owner))
                    else:
                        bot.send_message(message.chat.id, t(uid, "error"))
                user_state.pop(uid, None)
                return

            # fallback
            return

        # ===== المواد =====
        if text == t(uid, "subjects"):
            user_state.pop(uid, None)
            markup, _ = subjects_menu(uid)
            bot.send_message(message.chat.id, t(uid, "choose_subject"), reply_markup=markup)
            return

        _, subjects_list = subjects_menu(uid)
        if text in subjects_list:
            user_state[uid] = {"subject": text}
            bot.send_message(message.chat.id, f"📌 *{text}*\n{t(uid, 'choose_option')}",
                             parse_mode="Markdown", reply_markup=subject_options_menu(uid))
            return

        subject_opts = [t(uid, k) for k in ["subject_options_schedule", "subject_options_tasks",
                        "subject_options_price", "subject_options_summary", "subject_options_alerts"]]

        if state.get("subject") and not state.get("awaiting_date"):
            subj = state["subject"]
            rows = [r for r in data if safe_get(r, 1) == subj]

            if text in subject_opts:
                if text == t(uid, "subject_options_price"):
                    price = next((get_text(safe_get(r, 5)) for r in rows if safe_get(r, 5)), None)
                    msg = f"💰 *{subj}*: {price}" if price else f"لا يوجد سعر مسجل لـ *{subj}*"
                    bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=subject_options_menu(uid))
                    return

                col_map = {t(uid, "subject_options_schedule"): 2, t(uid, "subject_options_tasks"): 4,
                           t(uid, "subject_options_summary"): 6, t(uid, "subject_options_alerts"): 7}
                col = col_map[text]
                dates = list(dict.fromkeys(
                    parse_date(safe_get(r, 0)) for r in rows
                    if (get_text(safe_get(r, col)) or get_file_id(safe_get(r, col))) and safe_get(r, 0)
                ))
                if not dates:
                    no_data_map = {t(uid, "subject_options_schedule"): t(uid, "no_schedule"),
                                   t(uid, "subject_options_tasks"): t(uid, "no_tasks_subj"),
                                   t(uid, "subject_options_summary"): t(uid, "no_summary"),
                                   t(uid, "subject_options_alerts"): t(uid, "no_alerts_subj")}
                    no_msg = no_data_map.get(text, "لا توجد بيانات لـ")
                    bot.send_message(message.chat.id, f"{no_msg} *{subj}*",
                                     parse_mode="Markdown", reply_markup=subject_options_menu(uid))
                    return
                user_state[uid] = {"subject": subj, "action": text, "awaiting_date": True, "col": col, "dates": dates}
                bot.send_message(message.chat.id, t(uid, "choose_date"), reply_markup=dates_menu(uid, dates))
                return

        if state.get("awaiting_date"):
            subj = state["subject"]
            action = state["action"]
            col = state["col"]
            dates = state.get("dates", [])
            matched = [r for r in data if safe_get(r, 1) == subj and parse_date(safe_get(r, 0)) == text]
            if not matched:
                bot.send_message(message.chat.id, t(uid, "no_data"), reply_markup=dates_menu(uid, dates))
                return

            label_map = {t(uid, "subject_options_schedule"): t(uid, "label_time"),
                         t(uid, "subject_options_tasks"): t(uid, "label_task"),
                         t(uid, "subject_options_summary"): t(uid, "label_summary"),
                         t(uid, "subject_options_alerts"): t(uid, "label_alert")}
            label = label_map.get(action, "")
            day = get_day_name(text, uid)
            day_str = f" ({day})" if day else ""
            response = f"*{subj}* — {text}{day_str}\n" + "─" * 25 + "\n"
            file_ids = []

            for row in matched:
                cell = safe_get(row, col)
                val = get_text(cell)
                fid = get_file_id(cell)
                if val: response += f"{label}: {val}\n"
                if fid: file_ids.append(fid)

            if response.strip().endswith("─" * 25):
                response += t(uid, "no_data")

            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=dates_menu(uid, dates))
            for fid in file_ids:
                sent = False
                for sender in [bot.send_document, bot.send_photo, bot.send_video, bot.send_audio, bot.send_voice]:
                    try:
                        sender(message.chat.id, fid)
                        sent = True
                        break
                    except:
                        continue
            return

        # ===== القائمة الرئيسية =====
        if text == t(uid, "schedule"):
            last_date = get_last_date(data, 2)
            if not last_date:
                has_any = any(safe_get(r, 1) for r in data)
                msg = t(uid, "no_exist") + " 🕐" if has_any else t(uid, "unknown") + " 🕐"
                bot.send_message(message.chat.id, msg, reply_markup=main_menu(uid, admin=admin, owner=owner))
                return
            rows = [r for r in data if parse_date(safe_get(r, 0)) == last_date and get_text(safe_get(r, 2))]
            day = get_day_name(last_date, uid)
            response = f"🕐 *{day} — {last_date}:*\n" + "─" * 25 + "\n"
            for r in rows:
                response += f"📌 {safe_get(r,1)}: {get_text(safe_get(r,2))}\n"
            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=main_menu(uid, admin=admin, owner=owner))

        elif text == t(uid, "tasks"):
            last_date = get_last_date(data, 4)
            if not last_date:
                has_any = any(safe_get(r, 1) for r in data)
                msg = t(uid, "no_exist") + " 📝" if has_any else t(uid, "unknown") + " 📝"
                bot.send_message(message.chat.id, msg, reply_markup=main_menu(uid, admin=admin, owner=owner))
                return
            rows = [r for r in data if parse_date(safe_get(r, 0)) == last_date and (get_text(safe_get(r, 4)) or get_file_id(safe_get(r, 4)))]
            day = get_day_name(last_date, uid)
            response = f"📝 *{day} — {last_date}:*\n" + "─" * 25 + "\n"
            task_files = []
            for r in rows:
                cell = safe_get(r, 4)
                val = get_text(cell)
                fid = get_file_id(cell)
                if val: response += f"📌 {safe_get(r,1)}: {val}\n"
                elif fid: response += f"📌 {safe_get(r,1)}: 📎 ملف\n"
                if fid: task_files.append(fid)
            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=main_menu(uid, admin=admin, owner=owner))
            for fid in task_files:
                for sender in [bot.send_document, bot.send_photo, bot.send_video, bot.send_audio, bot.send_voice]:
                    try: sender(message.chat.id, fid); break
                    except: continue

        elif text == t(uid, "prices"):
            seen = {}
            for r in data:
                s = safe_get(r, 1)
                p = get_text(safe_get(r, 5))
                if s and p and s not in seen:
                    seen[s] = p
            if not seen:
                has_any = any(safe_get(r, 1) for r in data)
                msg = t(uid, "no_exist") + " 💰" if has_any else t(uid, "unknown") + " 💰"
                bot.send_message(message.chat.id, msg, reply_markup=main_menu(uid, admin=admin, owner=owner))
                return
            title = "💰 أسعار الملازم" if user_lang.get(uid, "ar") == "ar" else "💰 Book Prices"
            max_len = max(len(s) for s in seen.keys()) if seen else 10
            lines = ""
            for s, p in seen.items():
                lines += f"📖 {s:<{max_len}} : {p}\n"
            response = f"{title}:\n```\n{lines}```"
            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=main_menu(uid, admin=admin, owner=owner))

        elif text == t(uid, "alerts"):
            alerts = [(safe_get(r,1), parse_date(safe_get(r,0)), get_text(safe_get(r,7)))
                      for r in data if get_text(safe_get(r,7))]
            if not alerts:
                bot.send_message(message.chat.id, t(uid, "no_alerts"), reply_markup=main_menu(uid, admin=admin, owner=owner))
                return
            title = "⚠️ التنبيهات" if user_lang.get(uid, "ar") == "ar" else "⚠️ Alerts"
            response = f"*{title}:*\n" + "─" * 25 + "\n"
            for s, d, a in alerts:
                response += f"🔔 {s} ({d}):\n{a}\n\n"
            bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=main_menu(uid, admin=admin, owner=owner))

        else:
            bot.send_message(message.chat.id, t(uid, "choose_menu"), reply_markup=main_menu(uid, admin=admin, owner=owner))

    except Exception as e:
        bot.send_message(message.chat.id, t(uid, "error"))
        log_error(f"خطأ في handle_message: {e}")

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

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    log_info("البوت يعمل...")
    bot.infinity_polling()
