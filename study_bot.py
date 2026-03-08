# ====================================================
# study_bot.py — النسخة الكاملة المحدّثة
# ====================================================
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import os, json, re, threading, time
from dotenv import load_dotenv
import pytz, logging
import requests as _requests

load_dotenv()

YEMEN_TZ        = pytz.timezone('Asia/Aden')
LOG_BOT_TOKEN   = os.environ.get("STUDY_BOT_LOG_TOKEN", "")
STUDY_BOT_TOKEN = os.environ.get("STUDY_BOT_TOKEN", "")
SHEET_KEY       = os.environ.get("SHEET_KEY", "")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-8s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("StudyBot")

bot   = telebot.TeleBot(STUDY_BOT_TOKEN)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    gcreds = os.environ.get("GOOGLE_CREDENTIALS")
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(gcreds), scope) if gcreds else \
        ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client          = gspread.authorize(creds)
    spreadsheet     = client.open_by_key(SHEET_KEY)
    sheet           = spreadsheet.sheet1
    users_sheet     = spreadsheet.worksheet("المستخدمين")
    help_sheet      = spreadsheet.worksheet("المساعدة")
    bot_texts_sheet = spreadsheet.worksheet("bot_texts")
    try:    rooms_sheet = spreadsheet.worksheet("القاعات")
    except: rooms_sheet = None
except Exception as _e:
    logger.critical(f"خطأ Google Sheets: {_e}")
    sheet = users_sheet = help_sheet = bot_texts_sheet = rooms_sheet = None

# ─────────────────────────────────────────────────────
# BOT_TEXTS
# ─────────────────────────────────────────────────────
DEFAULT_BOT_TEXTS = {
    "رسالة_الترحيب":      "مرحبًا! اختر أحد الخيارات:",
    "رسالة_الرفض":        "⛔ غير مسموح لك باستخدام البوت\n\nالرجاء طلب الصلاحية من منشئ البوت @nt18s",
    "رسالة_انتظار":       "⏳ تم إرسال طلبك، انتظر موافقة المالك.",
    "رسالة_موافقة":       "✅ تمت الموافقة على طلبك! أرسل /start للبدء.",
    "رسالة_رفض_طلب":     "❌ تم رفض طلبك.",
    "زر_المواد":          "📚 المواد",
    "زر_التاريخ":         "📅 التاريخ",
    "زر_التكاليف":        "📝 التكاليف",
    "زر_الجدول":          "🕐 أوقات المحاضرات",
    "زر_التنبيهات":       "⚠️ تنبيهات",
    "زر_الاسعار":         "💰 أسعار الملازم",
    "زر_الملخصات":        "📖 الملخصات",
    "زر_طلب_رفع":         "📨 طلب رفع ملف",
    "زر_رفع_ملف":         "📤 رفع ملف",
    "زر_رفع_تعليمات":     "📹 رفع التعليمات",
    "زر_اشعار":           "📢 إرسال إشعار",
    "زر_اضافة":           "➕ إضافة بيانات",
    "زر_تعديل":           "✏️ تعديل/حذف بيانات",
    "زر_المستخدمين":      "👥 إدارة المستخدمين",
    "زر_عوده":            "🔙 العودة",
    "زر_يوم":             "🔍 يوم",
    "زر_فتره":            "📆 فترة",
    "زر_تحديد_الكل":     "تحديد الكل",
    "زر_تم_التحديد":     "✔️ تم التحديد",
    "زر_حسب_الماده":     "📌 حسب المادة",
    "زر_حسب_التاريخ":    "📅 حسب التاريخ",
    "زر_اضافة_محاضره":   "🕐 إضافة محاضرة",
    "زر_اضافة_تكليف":    "📝 إضافة تكليف",
    "زر_اضافة_ملخص":     "📖 إضافة ملخص",
    "زر_اضافة_سعر":      "💰 إضافة سعر ملزمة",
    "زر_اضافة_تنبيه":    "⚠️ إضافة تنبيه",
    "زر_تعديل_محاضره":   "🕐 تعديل/حذف محاضرة",
    "زر_تعديل_تكليف":    "📝 تعديل/حذف تكليف",
    "زر_تعديل_ملخص":     "📖 تعديل/حذف ملخص",
    "زر_تعديل_سعر":      "💰 تعديل/حذف سعر",
    "زر_تعديل_تنبيه":    "⚠️ تعديل/حذف تنبيه",
    "زر_تعديل_زرار":     "✏️ تعديل",
    "زر_حذف_زرار":       "🗑 حذف",
    "رسالة_لا_بيانات":    "لا توجد بيانات",
    "رسالة_خطأ":          "❌ حدث خطأ، حاول مرة أخرى.",
    "رسالة_تم_الحفظ":     "✅ تم حفظ البيانات بنجاح!",
    "رسالة_تم_الحذف":     "✅ تم الحذف!",
    "رسالة_تم_التعديل":   "✅ تم التعديل!",
    "رسالة_ادمن_فقط":     "⛔ فقط المدير يستطيع القيام بهذا.",
    "خيار_الجدول":        "🕐 أوقات المحاضرات",
    "خيار_التكاليف":      "📝 التكاليف",
    "خيار_السعر":         "💰 سعر الملزمة",
    "خيار_الملخص":        "📖 الملخص",
    "خيار_التنبيهات":     "⚠️ تنبيهات",
}
BOT_TEXTS = dict(DEFAULT_BOT_TEXTS)

def load_bot_texts():
    global BOT_TEXTS
    try:
        for row in bot_texts_sheet.get_all_values():
            if len(row) >= 2 and row[0].strip():
                BOT_TEXTS[row[0].strip()] = row[1].strip()
        logger.info("✅ bot_texts loaded")
    except Exception as e:
        logger.warning(f"bot_texts error: {e}")

def bt(key):
    return BOT_TEXTS.get(key, DEFAULT_BOT_TEXTS.get(key, key))

# ─────────────────────────────────────────────────────
# متغيرات الحالة
# ─────────────────────────────────────────────────────
user_state       = {}
user_lang        = {}
pending_requests = set()
request_msg_ids  = {}   # {requester_id: {owner_id: msg_id}}
_users_snapshot  = {}   # للمراقبة

DAYS_AR   = {0:"الاثنين",1:"الثلاثاء",2:"الأربعاء",3:"الخميس",4:"الجمعة",5:"السبت",6:"الأحد"}
DAYS_EN   = {0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",4:"Friday",5:"Saturday",6:"Sunday"}
MONTHS_AR = {1:"يناير",2:"فبراير",3:"مارس",4:"أبريل",5:"مايو",6:"يونيو",
             7:"يوليو",8:"أغسطس",9:"سبتمبر",10:"أكتوبر",11:"نوفمبر",12:"ديسمبر"}
MONTHS_AR_REV = {v: k for k, v in MONTHS_AR.items()}
MONTHS_EN_REV = {"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
                 "july":7,"august":8,"september":9,"october":10,"november":11,"december":12}
ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def normalize_digits(text):
    return text.translate(ARABIC_DIGITS)

# ─────────────────────────────────────────────────────
# Logging محسّن
# ─────────────────────────────────────────────────────
def _get_role_icon(uid):
    try:
        uid_str = str(uid)
        for row in users_sheet.get_all_values()[1:]:
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                if (row[5].strip().upper() if len(row) > 5 else "") == "TRUE": return "👑"
                if (row[4].strip().upper() if len(row) > 4 else "") == "TRUE": return "⭐"
                if (row[3].strip().upper() if len(row) > 3 else "") == "TRUE": return "👤"
                return "❌"
    except: pass
    return "👤"

def _get_user_name_phone(uid):
    try:
        uid_str = str(uid)
        for row in users_sheet.get_all_values()[1:]:
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                return row[0].strip(), (row[1].strip() if len(row) > 1 else "")
    except: pass
    return str(uid), ""

def tg_log(level, msg, uid=None):
    icons = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🚨"}
    now   = datetime.now(YEMEN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    if uid:
        name, phone   = _get_user_name_phone(uid)
        role_icon     = _get_role_icon(uid)
        ph_line       = f"\n📞 {phone}" if phone else ""
        user_block    = f"{role_icon} {name}\n🆔 `{uid}`{ph_line}\n\n"
    else:
        user_block = ""
    text = f"{icons.get(level, '📋')} *{level}*\n`{now}`\n\n{user_block}{msg}"
    if LOG_BOT_TOKEN and users_sheet:
        try:
            es = 0
            for row in users_sheet.get_all_values()[1:]:
                if not row or not any(c.strip() for c in row):
                    es += 1
                    if es >= 5: break
                    continue
                es = 0
                uid_str = row[2].strip().lstrip("'") if len(row) > 2 else ""
                if uid_str.isdigit() and (row[7].strip().upper() if len(row) > 7 else "") == "TRUE":
                    try:
                        _requests.post(
                            f"https://api.telegram.org/bot{LOG_BOT_TOKEN}/sendMessage",
                            json={"chat_id": int(uid_str), "text": text, "parse_mode": "Markdown"},
                            timeout=5)
                    except: pass
        except: pass
    getattr(logger, level.lower(), logger.info)(msg)

def log_info(m, uid=None):     tg_log("INFO", m, uid)
def log_warning(m, uid=None):  tg_log("WARNING", m, uid)
def log_error(m, uid=None):    tg_log("ERROR", m, uid)
def log_critical(m, uid=None): tg_log("CRITICAL", m, uid)


# ─────────────────────────────────────────────────────
# Google Sheets — قراءة
# ─────────────────────────────────────────────────────
def get_subjects():
    try:
        seen, result = set(), []
        for row in sheet.get_all_values()[1:]:
            s = row[1].strip() if len(row) > 1 else ""
            if s and s not in seen:
                seen.add(s); result.append(s)
        return result
    except Exception as e:
        log_error(f"get_subjects: {e}"); return []

def get_rooms(building):
    try:
        if not rooms_sheet: return []
        return [r[1].strip() for r in rooms_sheet.get_all_values()
                if len(r) > 1 and r[0].strip() == building and r[1].strip()]
    except: return []

def get_users():
    try:
        allowed, admins, owners, log_ids = [], [], [], []
        open_all = admin_all = False
        es = 0
        for row in users_sheet.get_all_values()[1:]:
            if not row or not any(c.strip() for c in row):
                es += 1
                if es >= 5: break
                continue
            es = 0
            name        = row[0].strip()
            uid_str     = row[2].strip().lstrip("'") if len(row) > 2 else ""
            allowed_val = row[3].strip().upper() if len(row) > 3 else "FALSE"
            admin_val   = row[4].strip().upper() if len(row) > 4 else "FALSE"
            owner_val   = row[5].strip().upper() if len(row) > 5 else "FALSE"
            log_val     = row[7].strip().upper() if len(row) > 7 else "FALSE"
            if name == "الكل":
                if allowed_val == "TRUE": open_all  = True
                if admin_val   == "TRUE": admin_all = True
                continue
            if not uid_str.isdigit(): continue
            uid = int(uid_str)
            if allowed_val == "TRUE": allowed.append(uid)
            if admin_val   == "TRUE": admins.append(uid)
            if owner_val   == "TRUE": owners.append(uid)
            if log_val     == "TRUE": log_ids.append(uid)
        return allowed, admins, owners, open_all, admin_all, log_ids
    except Exception as e:
        log_error(f"get_users: {e}"); return [], [], [], False, False, []

def get_user_lang_from_sheet(uid):
    try:
        for row in users_sheet.get_all_values()[1:]:
            if len(row) > 2 and row[2].strip().lstrip("'").isdigit() \
               and int(row[2].strip().lstrip("'")) == uid:
                return "en" if (row[6].strip().upper() if len(row) > 6 else "") == "TRUE" else "ar"
        return "ar"
    except: return "ar"

def save_user_lang_to_sheet(uid, lang):
    try:
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if len(row) > 2 and row[2].strip().lstrip("'").isdigit() \
               and int(row[2].strip().lstrip("'")) == uid:
                users_sheet.update_cell(i, 7, lang == "en"); return True
        return False
    except: return False

def load_user_lang(uid):
    if uid not in user_lang:
        user_lang[uid] = get_user_lang_from_sheet(uid)

def get_owner_ids():
    _, _, owners, _, _, _ = get_users(); return owners

def is_owner_id(uid): return uid in get_owner_ids()
def is_owner(msg):    return is_owner_id(msg.from_user.id)

def _is_admin_or_owner(uid):
    _, admins, owners, _, admin_all, _ = get_users()
    return admin_all or uid in admins or uid in owners

def is_pending(uid):
    if uid in pending_requests: return True
    try:
        uid_str = str(uid); es = 0
        for row in users_sheet.get_all_values()[1:]:
            if not row or not any(c.strip() for c in row):
                es += 1
                if es >= 5: break
                continue
            es = 0
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str: return True
    except: pass
    return False

def add_user_to_sheet(name, uid, auto=False, allowed=True):
    try:
        display = f"🆕 {name}" if auto else name
        users_sheet.append_row([display, "", uid, allowed, False, False, False, False],
                                value_input_option="USER_ENTERED")
        return True
    except: return False

def auto_register_user(message, open_all=None):
    try:
        if open_all is None: _, _, _, open_all, _, _ = get_users()
        if not open_all: return
        uid_str = str(message.from_user.id)
        for row in users_sheet.get_all_values()[1:]:
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str: return
        add_user_to_sheet(message.from_user.full_name or "مجهول",
                          message.from_user.id, auto=True, allowed=False)
    except: pass

def find_user_row_by_id(search_id):
    try:
        sid = str(search_id).strip()
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows, start=1):
            if len(row) > 2 and row[2].strip().lstrip("'") == sid: return i, row
        return None, None
    except: return None, None

def find_user_row_by_phone(phone):
    try:
        pc = re.sub(r'[\s\-\+]', '', phone.strip())
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows, start=1):
            rp = re.sub(r'[\s\-\+]', '', row[1].strip() if len(row) > 1 else "")
            if rp and rp == pc: return i, row
        return None, None
    except: return None, None

def get_all_user_ids():
    allowed, _, _, open_all, _, _ = get_users(); return allowed, open_all

def get_all_registered_uids():
    try:
        uids = []; es = 0
        for row in users_sheet.get_all_values()[1:]:
            if not row or not any(c.strip() for c in row):
                es += 1
                if es >= 5: break
                continue
            es = 0
            uid_str = row[2].strip().lstrip("'") if len(row) > 2 else ""
            if uid_str.isdigit(): uids.append(int(uid_str))
        return uids
    except: return []

# مراقبة تغييرات الشيت
def _snapshot_users():
    snap = {}
    try:
        for row in users_sheet.get_all_values()[1:]:
            uid_str = row[2].strip().lstrip("'") if len(row) > 2 else ""
            if not uid_str.isdigit(): continue
            snap[uid_str] = {
                "allowed": (row[3].strip().upper() if len(row) > 3 else "FALSE") == "TRUE",
                "admin":   (row[4].strip().upper() if len(row) > 4 else "FALSE") == "TRUE",
                "owner":   (row[5].strip().upper() if len(row) > 5 else "FALSE") == "TRUE",
                "name":    row[0].strip(),
                "phone":   row[1].strip() if len(row) > 1 else "",
            }
    except: pass
    return snap

def _watch_sheet_loop():
    global _users_snapshot
    _users_snapshot = _snapshot_users()
    while True:
        time.sleep(30)
        try:
            new_snap = _snapshot_users()
            for uid_str, new in new_snap.items():
                old = _users_snapshot.get(uid_str)
                if not old: continue
                uid   = int(uid_str)
                name  = new["name"]; phone = new["phone"]
                if new["owner"] and not old["owner"]:
                    try: bot.send_message(uid, "👑 تمت ترقيتك إلى مالك!")
                    except: pass
                    notify_owners_decision(uid, name, phone, "الشيت", True)
                elif new["admin"] and not old["admin"]:
                    try: bot.send_message(uid, "⭐ تمت ترقيتك إلى أدمن!")
                    except: pass
                    notify_owners_decision(uid, name, phone, "الشيت", True)
                elif new["allowed"] and not old["allowed"]:
                    try: bot.send_message(uid, bt("رسالة_موافقة"))
                    except: pass
                    notify_owners_decision(uid, name, phone, "الشيت", True)
                    log_info(f"موافقة من الشيت على {name}", uid)
                elif not new["allowed"] and old["allowed"]:
                    try: bot.send_message(uid, "⛔ تم إلغاء صلاحيتك.")
                    except: pass
            _users_snapshot = new_snap
        except: pass


# ─────────────────────────────────────────────────────
# Data helpers
# ─────────────────────────────────────────────────────
def safe_get(row, idx):
    v = row[idx].strip() if len(row) > idx else ""
    return v.lstrip("'").strip() if v else ""

def get_text(cell):
    return cell.split("|")[0].strip() if "|" in cell else cell.strip()

def get_file_ids(cell):
    if "|" not in cell: return []
    part = cell.split("|", 1)[1].strip()
    return [f.strip() for f in part.split(",") if f.strip()] if part else []

def merge_cell(text, fids):
    if not fids: return text
    fids_str = ",".join(fids) if isinstance(fids, list) else fids
    return f"{text}|{fids_str}" if fids_str else text

def parse_date(d):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try: return datetime.strptime(d.strip(), fmt).strftime("%d/%m/%Y")
        except: continue
    return d.strip()

def is_valid_date(d):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try: datetime.strptime(d.strip(), fmt); return True
        except: continue
    return False

def smart_date_from_day(day):
    now = datetime.now(YEMEN_TZ)
    if day < now.day:
        # اليوم مرّ → هذا الشهر
        try: return now.replace(day=day).strftime("%d/%m/%Y")
        except: return now.strftime("%d/%m/%Y")
    else:
        # اليوم لم يمرّ → الشهر الماضي
        first  = now.replace(day=1)
        last_m = first - timedelta(days=1)
        try: return last_m.replace(day=day).strftime("%d/%m/%Y")
        except: return now.strftime("%d/%m/%Y")

def parse_smart_date(raw):
    text = normalize_digits(raw.strip())
    if is_valid_date(text): return parse_date(text)
    if text.isdigit():
        d = int(text)
        if 1 <= d <= 31: return smart_date_from_day(d)
    # يوم شهر سنة
    m = re.match(r'^(\d{1,2})\s+([\u0600-\u06FFa-zA-Z]+)\s+(\d{4})$', text)
    if m:
        day_n = int(m.group(1)); mon_s = m.group(2); yr = int(m.group(3))
        mon = MONTHS_AR_REV.get(mon_s) or MONTHS_EN_REV.get(mon_s.lower())
        if mon:
            try: return datetime(yr, mon, day_n).strftime("%d/%m/%Y")
            except: pass
    # يوم/شهر
    m2 = re.match(r'^(\d{1,2})/(\d{1,2})$', text)
    if m2:
        now = datetime.now(YEMEN_TZ)
        try: return datetime(now.year, int(m2.group(2)), int(m2.group(1))).strftime("%d/%m/%Y")
        except: pass
    return None

def parse_date_range(raw):
    text = normalize_digits(raw.strip())
    m = re.match(r'(\d{1,2}/\d{1,2}/\d{4})\s*[-–]\s*(\d{1,2}/\d{1,2}/\d{4})', text)
    if m and is_valid_date(m.group(1)) and is_valid_date(m.group(2)):
        return parse_date(m.group(1)), parse_date(m.group(2))
    m2 = re.match(r'^(\d{1,2})[-–](\d{1,2})$', text)
    if m2:
        return smart_date_from_day(int(m2.group(1))), smart_date_from_day(int(m2.group(2)))
    return None, None

def normalize_time(t):
    t = t.strip().replace("–", "-").replace("—", "-")
    t = re.sub(r'\s*-\s*', ' - ', t)
    def pad(m): return f"{int(m.group(1)):02d}:{m.group(2)}"
    return re.sub(r'(\d{1,2}):(\d{2})', pad, t)

def parse_time_range(t):
    t = normalize_time(t)
    parts = re.split(r'\s*-\s*', t)
    if len(parts) != 2: return None, None
    def mins(s):
        s = s.strip()
        h, mm = s.split(":") if ":" in s else (s, "0")
        return int(h) * 60 + int(mm)
    try: return mins(parts[0]), mins(parts[1])
    except: return None, None

def check_lecture_conflict(date, time_val):
    try:
        ns, ne = parse_time_range(time_val)
        if ns is None: return None
        for row in get_data():
            rd = parse_date(safe_get(row, 0))
            rt = safe_get(row, 2)
            if rd != date or not rt: continue
            es2, ee2 = parse_time_range(rt)
            if es2 is None: continue
            if ns < ee2 and es2 < ne:
                return {"subject": safe_get(row, 1),
                        "room":    safe_get(row, 3),
                        "time":    normalize_time(rt)}
    except: pass
    return None

def get_day_name(date_str, uid=None):
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return DAYS_EN[dt.weekday()] if uid and user_lang.get(uid, "ar") == "en" \
               else DAYS_AR[dt.weekday()]
    except: return ""

def format_date_ar(date_str):
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return f"{dt.day} {MONTHS_AR[dt.month]}"
    except: return date_str

def dates_in_range(date_str, d1, d2):
    try:
        dt  = datetime.strptime(date_str, "%d/%m/%Y")
        dt1 = datetime.strptime(d1, "%d/%m/%Y")
        dt2 = datetime.strptime(d2, "%d/%m/%Y")
        if dt1 > dt2: dt1, dt2 = dt2, dt1
        return dt1 <= dt <= dt2
    except: return False

def get_last_date(data, col):
    dates = []
    for r in data:
        d = safe_get(r, 0)
        if d and (get_text(safe_get(r, col)) or get_file_ids(safe_get(r, col))):
            try: dates.append(parse_date(d))
            except: pass
    return sorted(dates, key=lambda x: datetime.strptime(x, "%d/%m/%Y"))[-1] if dates else None

def get_data():
    try:
        useful = []
        for r in sheet.get_all_values()[1:]:
            if any(len(r) > i and r[i].strip() for i in range(2, 8)):
                useful.append(r)
        return useful
    except: return []

def get_last_lectures_for_subject(subject, n=3):
    try:
        seen, dates = set(), []
        for r in get_data():
            s = safe_get(r, 1); d = safe_get(r, 0); t = safe_get(r, 2)
            if s == subject and d and t:
                p = parse_date(d)
                if p not in seen: seen.add(p); dates.append(p)
        dates.sort(key=lambda x: datetime.strptime(x, "%d/%m/%Y"), reverse=True)
        return dates[:n]
    except: return []

# ─────────────────────────────────────────────────────
# Sheet write helpers
# ─────────────────────────────────────────────────────
def save_file_to_cell(date, subject, col, fids, merge=False):
    try:
        fids = fids if isinstance(fids, list) else [fids]
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) and parse_date(safe_get(row, 0)) == date \
               and safe_get(row, 1) == subject:
                current  = safe_get(row, col)
                all_fids = (get_file_ids(current) + fids) if merge else fids
                sheet.update_cell(i, col + 1, merge_cell(get_text(current), all_fids))
                return True
        new_row = [""] * 8
        new_row[0] = date; new_row[1] = subject; new_row[col] = f"|{','.join(fids)}"
        sheet.append_row(new_row, value_input_option="USER_ENTERED"); return True
    except Exception as e:
        log_error(f"save_file_to_cell: {e}"); return False

def save_text_to_cell(date, subject, col, text_val):
    try:
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) and parse_date(safe_get(row, 0)) == date \
               and safe_get(row, 1) == subject:
                existing_fids = get_file_ids(safe_get(row, col))
                sheet.update_cell(i, col + 1, merge_cell(text_val, existing_fids)); return True
        new_row = [""] * 8
        new_row[0] = date; new_row[1] = subject; new_row[col] = text_val
        sheet.append_row(new_row, value_input_option="USER_ENTERED"); return True
    except Exception as e:
        log_error(f"save_text_to_cell: {e}"); return False

def save_lecture(date, subject, time_val, room):
    try:
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) and parse_date(safe_get(row, 0)) == date \
               and safe_get(row, 1) == subject:
                sheet.update_cell(i, 3, time_val)
                sheet.update_cell(i, 4, room); return True
        new_row = [""] * 8
        new_row[0] = date; new_row[1] = subject
        new_row[2] = time_val; new_row[3] = room
        sheet.append_row(new_row, value_input_option="USER_ENTERED"); return True
    except Exception as e:
        log_error(f"save_lecture: {e}"); return False

def delete_cell(date, subject, col):
    try:
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) and parse_date(safe_get(row, 0)) == date \
               and safe_get(row, 1) == subject:
                sheet.update_cell(i, col + 1, ""); return True
        return False
    except: return False

# ─────────────────────────────────────────────────────
# Help materials
# ─────────────────────────────────────────────────────
def get_help_materials():
    try:
        mats = []
        for row in help_sheet.get_all_values():
            if not row or not any(r.strip() for r in row): continue
            fid   = row[1].strip() if len(row) > 1 else ""
            ftype = row[2].strip() if len(row) > 2 else ""
            aud   = row[3].strip() if len(row) > 3 else "user"
            note  = row[4].strip() if len(row) > 4 else ""
            if fid or note: mats.append({"file_id": fid, "file_type": ftype,
                                          "audience": aud, "note": note})
        return mats
    except: return []

def save_help_material(files_data, audience, note=""):
    try:
        rows = help_sheet.get_all_values()
        nrow = len(rows) + 1
        if note:
            help_sheet.update([[f"note_{nrow}", "", "", audience, note]], f"A{nrow}:E{nrow}")
            nrow += 1
        for fd in files_data:
            help_sheet.update([[f"file_{nrow}", fd["file_id"], fd["file_type"], audience, ""]],
                               f"A{nrow}:E{nrow}")
            nrow += 1
        return True
    except Exception as e:
        log_error(f"save_help_material: {e}"); return False

def get_settings():
    return bt("رسالة_الترحيب"), bt("رسالة_الرفض")

# ─────────────────────────────────────────────────────
# الكود السري
# ─────────────────────────────────────────────────────
def calc_secret_code(uid):
    day   = datetime.now(YEMEN_TZ).day
    total = sum(int(d) for d in str(uid)) + day
    return str(total)


# ─────────────────────────────────────────────────────
# إرسال الملفات (media group محسّن)
# ─────────────────────────────────────────────────────
def _try_send_file(chat_id, fid, caption=None, parse_mode=None, reply_markup=None):
    for sender in [bot.send_photo, bot.send_video, bot.send_audio,
                   bot.send_voice, bot.send_document]:
        try:
            sender(chat_id, fid, caption=caption, parse_mode=parse_mode,
                   reply_markup=reply_markup)
            return True
        except: continue
    return False

def _is_media_fid(fid):
    from telebot.types import InputMediaPhoto
    try: InputMediaPhoto(fid); return True
    except: return False

def send_files_with_text(chat_id, text, fids, reply_markup=None):
    from telebot.types import InputMediaPhoto, InputMediaDocument
    if not fids:
        if text:
            bot.send_message(chat_id, text, parse_mode="Markdown",
                             reply_markup=reply_markup)
        return
    cap   = text[:1024] if text else None
    parse = "Markdown" if cap else None
    if len(fids) == 1:
        ok = _try_send_file(chat_id, fids[0], caption=cap,
                             parse_mode=parse, reply_markup=reply_markup)
        if not ok and text:
            bot.send_message(chat_id, text, parse_mode="Markdown",
                             reply_markup=reply_markup)
        return
    # تصنيف الملفات
    media_fids = [fid for fid in fids if _is_media_fid(fid)]
    other_fids = [fid for fid in fids if not _is_media_fid(fid)]
    # إرسال ميديا جروب
    if media_fids:
        try:
            mg = []
            for i, fid in enumerate(media_fids):
                if i == 0 and cap:
                    mg.append(InputMediaPhoto(fid, caption=cap, parse_mode=parse))
                else:
                    mg.append(InputMediaPhoto(fid))
            bot.send_media_group(chat_id, mg)
            cap = None  # أُرسل مع الميديا جروب
        except:
            for fid in media_fids:
                _try_send_file(chat_id, fid)
    # إرسال ملفات أخرى منفصلة
    for fid in other_fids:
        _try_send_file(chat_id, fid)
    # النص إذا لم يُرسل بعد
    if cap:
        bot.send_message(chat_id, cap, parse_mode=parse)
    if reply_markup:
        bot.send_message(chat_id, ".", reply_markup=reply_markup)

# ─────────────────────────────────────────────────────
# إشعارات المالكين
# ─────────────────────────────────────────────────────
def notify_owners_new_request(requester_id, requester_name, phone=""):
    owners = get_owner_ids()
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(
            "✅ قبول", callback_data=f"approve_{requester_id}_{requester_name}"),
        telebot.types.InlineKeyboardButton(
            "❌ رفض",  callback_data=f"reject_{requester_id}")
    )
    ph  = f"📞 الرقم: `{phone}`\n" if phone else ""
    msg = (f"📩 طلب انضمام جديد!\n\n"
           f"👤 الاسم: `{requester_name}`\n"
           f"🆔 المعرف: `{requester_id}`\n{ph}")
    if requester_id not in request_msg_ids:
        request_msg_ids[requester_id] = {}
    for oid in owners:
        try:
            sent = bot.send_message(oid, msg, parse_mode="Markdown", reply_markup=markup)
            request_msg_ids[requester_id][oid] = sent.message_id
        except: pass

def notify_owners_decision(requester_id, requester_name, phone, decided_by, approved):
    owners  = get_owner_ids()
    msg_ids = request_msg_ids.pop(requester_id, {})
    for oid in owners:
        mid = msg_ids.get(oid)
        if mid:
            try: bot.delete_message(oid, mid)
            except: pass
    status = "✅ تمت الموافقة على" if approved else "❌ تم الرفض على"
    ph     = f"📞 الرقم: `{phone}`\n" if phone else ""
    result = (f"{status}:\n👤 `{requester_name}`\n"
              f"🆔 `{requester_id}`\n{ph}"
              f"من قِبل: {decided_by}")
    for oid in owners:
        try: bot.send_message(oid, result, parse_mode="Markdown")
        except: pass

# ─────────────────────────────────────────────────────
# اقتراح التاريخ
# ─────────────────────────────────────────────────────
def send_date_suggestions(chat_id, subject=None, for_lecture=False, for_alert=False):
    now   = datetime.now(YEMEN_TZ)
    today = now.strftime("%d/%m/%Y")
    tmrw  = (now + timedelta(days=1)).strftime("%d/%m/%Y")
    if for_lecture or for_alert:
        lines = [f"`{tmrw}`", f"`{today}`"]
    else:
        lines = [f"`{today}`"]
        if subject:
            for d in get_last_lectures_for_subject(subject, 3):
                if d != today and f"`{d}`" not in lines:
                    lines.append(f"`{d}`")
        lines = lines[:4]
    msg = "📅 تواريخ مقترحة (اضغط للنسخ):\n\n" + "\n".join(lines)
    bot.send_message(chat_id, msg, parse_mode="Markdown")

# ─────────────────────────────────────────────────────
# Keyboards
# ─────────────────────────────────────────────────────
def main_menu(uid, admin=False, owner=False):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    if admin or owner:
        m.row(bt("زر_التاريخ"),        bt("زر_المواد"))
        m.row(bt("زر_التكاليف"),        bt("زر_الجدول"))
        m.row(bt("زر_الاسعار"),         bt("زر_الملخصات"),    bt("زر_التنبيهات"))
        m.row(bt("زر_اضافة"),           bt("زر_تعديل"))
        m.row(bt("زر_اشعار"),           bt("زر_رفع_ملف"),     bt("زر_رفع_تعليمات"))
        if owner: m.add(bt("زر_المستخدمين"))
    else:
        m.row(bt("زر_التاريخ"),        bt("زر_المواد"))
        m.row(bt("زر_التكاليف"),        bt("زر_الجدول"),      bt("زر_الملخصات"))
        m.row(bt("زر_الاسعار"),         bt("زر_طلب_رفع"),     bt("زر_التنبيهات"))
    return m

def back_only_menu():
    m = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add(bt("زر_عوده")); return m

def back_skip_menu():
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row("⏭️ تخطي", bt("زر_عوده")); return m

def back_with_noexist():
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("لا يوجد", bt("زر_عوده")); return m

def subjects_menu_kb():
    subjects = get_subjects()
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for s in subjects: m.add(s)
    m.add(bt("زر_عوده")); return m, subjects

def subject_options_menu():
    m = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for k in ["خيار_الجدول", "خيار_التكاليف", "خيار_السعر",
              "خيار_الملخص", "خيار_التنبيهات"]:
        m.add(bt(k))
    m.add(bt("زر_عوده")); return m

def dates_menu_kb(dates):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for d in dates: m.add(d)
    m.add(bt("زر_عوده")); return m

def file_type_menu():
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(bt("زر_اضافة_تكليف"), bt("زر_اضافة_ملخص"))
    m.add(bt("زر_عوده")); return m

def add_data_menu():
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row(bt("زر_اضافة_محاضره"), bt("زر_اضافة_تكليف"))
    m.row(bt("زر_اضافة_ملخص"),   bt("زر_اضافة_سعر"))
    m.add(bt("زر_اضافة_تنبيه")); m.add(bt("زر_عوده")); return m

def edit_data_menu():
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row(bt("زر_تعديل_محاضره"), bt("زر_تعديل_تكليف"))
    m.row(bt("زر_تعديل_ملخص"),   bt("زر_تعديل_سعر"))
    m.add(bt("زر_تعديل_تنبيه")); m.add(bt("زر_عوده")); return m

def edit_action_menu():
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(bt("زر_تعديل_زرار"), bt("زر_حذف_زرار"))
    m.add(bt("زر_عوده")); return m

def buildings_menu():
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("🏛 القديم", "🏫 الاداب"); m.add(bt("زر_عوده")); return m

def rooms_menu_kb(building):
    rooms = get_rooms(building)
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for r in rooms: m.add(r)
    m.add(bt("زر_عوده")); return m, rooms

def lecture_time_menu():
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("🕐 08:00 - 10:00", "🕐 10:00 - 12:00")
    m.add("🕐 12:00 - 14:00", "⏰ توقيت آخر")
    m.add("لا يوجد", bt("زر_عوده")); return m

def manage_users_menu():
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row("🔍 بحث بالID", "🔍 بحث بالرقم")
    m.add(bt("زر_عوده")); return m

def display_mode_menu():
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row(bt("زر_حسب_التاريخ"), bt("زر_حسب_الماده"))
    m.add(bt("زر_عوده")); return m

def date_type_menu():
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row(bt("زر_يوم"), bt("زر_فتره"))
    m.add(bt("زر_عوده")); return m

def help_audience_menu():
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("👤 للمستخدمين", "👑 للأدمن"); m.add(bt("زر_عوده")); return m

def help_view_menu():
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("👤 تعليمات المستخدم", "👑 تعليمات الأدمن")
    m.add(bt("زر_عوده")); return m

def lang_menu():
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("🇾🇪 العربية", "🇬🇧 English"); return m

def upload_confirm_menu():
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row("✅ إرسال", bt("زر_عوده")); return m

# ─────────────────────────────────────────────────────
# Inline multi-select keyboard
# ─────────────────────────────────────────────────────
def build_multiselect_kb(items, selected, prefix):
    keyboard = []; row = []
    for label, value in items:
        lbl = f"✅ {label}" if value in selected else label
        row.append(telebot.types.InlineKeyboardButton(
            lbl, callback_data=f"{prefix}:{value}"))
        if len(row) == 2: keyboard.append(row); row = []
    all_lbl  = f"✅ {bt('زر_تحديد_الكل')}" if "__all__" in selected \
               else bt("زر_تحديد_الكل")
    done_lbl = bt("زر_تم_التحديد")
    if row:
        row.append(telebot.types.InlineKeyboardButton(
            all_lbl, callback_data=f"{prefix}:__all__"))
        keyboard.append(row)
        keyboard.append([telebot.types.InlineKeyboardButton(
            done_lbl, callback_data=f"{prefix}:__done__")])
    else:
        keyboard.append([
            telebot.types.InlineKeyboardButton(
                all_lbl, callback_data=f"{prefix}:__all__"),
            telebot.types.InlineKeyboardButton(
                done_lbl, callback_data=f"{prefix}:__done__"),
        ])
    return telebot.types.InlineKeyboardMarkup(keyboard)

# ─────────────────────────────────────────────────────
# بطاقة المستخدم
# ─────────────────────────────────────────────────────
def user_card_markup(uid_str):
    mk = telebot.types.InlineKeyboardMarkup(row_width=3)
    mk.row(
        telebot.types.InlineKeyboardButton(
            "👑 مالك", callback_data=f"role_owner_{uid_str}"),
        telebot.types.InlineKeyboardButton(
            "⭐ أدمن", callback_data=f"role_admin_{uid_str}"),
        telebot.types.InlineKeyboardButton(
            "👤 مستخدم", callback_data=f"role_user_{uid_str}"),
    )
    return mk

def send_user_card(chat_id, row):
    name      = row[0].strip() if row else ""
    uid_str   = row[2].strip().lstrip("'") if len(row) > 2 else ""
    phone     = row[1].strip() if len(row) > 1 else ""
    own       = row[5].strip().upper() if len(row) > 5 else "FALSE"
    adm       = row[4].strip().upper() if len(row) > 4 else "FALSE"
    allow_val = row[3].strip().upper() if len(row) > 3 else "FALSE"
    icon = "👑" if own == "TRUE" else ("⭐" if adm == "TRUE" else
           ("👤" if allow_val == "TRUE" else "❌"))
    ph_line = f"\n📞 `{phone}`" if phone else ""
    text    = f"{icon} *{name}*\n🆔 `{uid_str}`{ph_line}\n{'─'*23}"
    bot.send_message(chat_id, text, parse_mode="Markdown",
                     reply_markup=user_card_markup(uid_str))


# ─────────────────────────────────────────────────────
# عرض نتائج البحث
# ─────────────────────────────────────────────────────
def send_search_results(chat_id, uid, date_filter, subjects_filter, types_filter, display_mode):
    data     = get_data()
    is_range = isinstance(date_filter, tuple)
    if is_range:
        d1, d2    = date_filter
        range_str = f"{format_date_ar(d1)} — {format_date_ar(d2)}"
    else:
        range_str = format_date_ar(date_filter)

    def match_date(r):
        rd = safe_get(r, 0)
        if not rd: return False
        try:
            pd = parse_date(rd)
        except: return False
        if is_range: return dates_in_range(pd, d1, d2)
        return pd == date_filter

    filtered = [r for r in data
                if match_date(r) and safe_get(r, 1) in subjects_filter]

    if not filtered:
        bot.send_message(chat_id,
                         f"{bt('رسالة_لا_بيانات')}\n📅 {range_str}")
        return

    found = False
    if display_mode == "date":
        all_dates = sorted(
            set(parse_date(safe_get(r, 0)) for r in filtered if safe_get(r, 0)),
            key=lambda x: datetime.strptime(x, "%d/%m/%Y")
        )
        for d in all_dates:
            rows_d = [r for r in filtered
                      if safe_get(r, 0) and parse_date(safe_get(r, 0)) == d]
            if not rows_d: continue
            day  = get_day_name(d, uid)
            d_ar = format_date_ar(d)
            msg  = f"📅 *{d_ar} — {day}*\n{'━'*20}\n"
            fids_all = []; has_content = False
            for row in rows_d:
                subj  = safe_get(row, 1)
                parts = []
                if "محاضرات" in types_filter:
                    t = safe_get(row, 2)
                    if t: parts.append(f"🕐 {t}")
                if "تكاليف" in types_filter:
                    cell = safe_get(row, 4)
                    tx = get_text(cell); fi = get_file_ids(cell)
                    if tx: parts.append(f"📝 {tx}")
                    fids_all.extend(fi)
                if "ملخصات" in types_filter:
                    cell = safe_get(row, 6)
                    tx = get_text(cell); fi = get_file_ids(cell)
                    if tx: parts.append(f"📖 {tx}")
                    fids_all.extend(fi)
                if parts:
                    msg += f"\n📌 *{subj}*\n" + "\n".join(parts) + "\n"
                    has_content = True
            if has_content or fids_all:
                found = True
                send_files_with_text(chat_id, msg, fids_all)
    else:
        for subj in subjects_filter:
            rows_s = sorted(
                [r for r in filtered if safe_get(r, 1) == subj],
                key=lambda r: datetime.strptime(
                    parse_date(safe_get(r, 0)), "%d/%m/%Y")
                    if safe_get(r, 0) else datetime.min
            )
            if not rows_s: continue
            msg      = f"📌 *{subj}*\n{'━'*20}\n"
            fids_all = []; has_content = False
            for row in rows_s:
                d    = parse_date(safe_get(row, 0))
                day  = get_day_name(d, uid)
                d_ar = format_date_ar(d)
                parts = [f"📅 {d_ar} — {day}"]
                if "محاضرات" in types_filter:
                    t = safe_get(row, 2)
                    if t: parts.append(f"🕐 {t}")
                if "تكاليف" in types_filter:
                    cell = safe_get(row, 4)
                    tx = get_text(cell); fi = get_file_ids(cell)
                    if tx: parts.append(f"📝 {tx}")
                    fids_all.extend(fi)
                if "ملخصات" in types_filter:
                    cell = safe_get(row, 6)
                    tx = get_text(cell); fi = get_file_ids(cell)
                    if tx: parts.append(f"📖 {tx}")
                    fids_all.extend(fi)
                if len(parts) > 1:
                    msg += "\n".join(parts) + "\n─\n"
                    has_content = True
            if has_content or fids_all:
                found = True
                send_files_with_text(chat_id, msg, fids_all)

    if not found:
        bot.send_message(chat_id,
                         f"{bt('رسالة_لا_بيانات')}\n📅 {range_str}")

# ─────────────────────────────────────────────────────
# بث الإشعارات
# ─────────────────────────────────────────────────────
def _do_broadcast(chat_id, uid, admin, owner, text_msg, files_data):
    uids, open_all = get_all_user_ids()
    if open_all:
        registered = get_all_registered_uids()
        if registered: uids = registered
    if not uids:
        bot.send_message(chat_id, "⚠️ لا يوجد مستخدمون."); return
    success = fail = 0
    for user_id in uids:
        try:
            if text_msg:
                bot.send_message(user_id,
                                 f"📢 *إشعار:*\n\n{text_msg}",
                                 parse_mode="Markdown")
            for fd in (files_data or []):
                _try_send_file(user_id, fd["file_id"])
            success += 1
        except: fail += 1
    bot.send_message(chat_id,
                     f"✅ تم الإرسال!\n✅ {success} | ❌ {fail}",
                     reply_markup=main_menu(uid, admin=admin, owner=owner))

# ─────────────────────────────────────────────────────
# عرض مواد المساعدة
# ─────────────────────────────────────────────────────
def send_help_materials(chat_id, uid, audience_filter):
    mats = [m for m in get_help_materials()
            if m["audience"] == audience_filter]
    if not mats:
        bot.send_message(chat_id, "📭 لا توجد تعليمات حالياً."); return
    title = ("📖 تعليمات المستخدم" if audience_filter == "user"
             else "📖 تعليمات الأدمن")
    bot.send_message(chat_id, f"*{title}*", parse_mode="Markdown")
    for m in mats:
        send_files_with_text(chat_id, m["note"] or None,
                             [m["file_id"]] if m["file_id"] else [])


# ─────────────────────────────────────────────────────
# Callback handlers
# ─────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda call: call.data.startswith("role_"))
def handle_role(call):
    caller_id = call.from_user.id
    if not is_owner_id(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح"); return
    parts      = call.data.split("_", 2)
    new_role   = parts[1]
    target_uid = parts[2]
    decided_by = (f"@{call.from_user.username}" if call.from_user.username
                  else call.from_user.full_name)
    try:
        rows = users_sheet.get_all_values(); es = 0
        for i, row in enumerate(rows[1:], start=2):
            if not row or not any(c.strip() for c in row):
                es += 1
                if es >= 5: break
                continue
            es = 0
            cell_id = row[2].strip().lstrip("'") if len(row) > 2 else ""
            if cell_id != target_uid: continue
            cur_own   = row[5].strip().upper() if len(row) > 5 else "FALSE"
            cur_adm   = row[4].strip().upper() if len(row) > 4 else "FALSE"
            cur_allow = row[3].strip().upper() if len(row) > 3 else "FALSE"
            t_name    = row[0].strip()
            t_phone   = row[1].strip() if len(row) > 1 else ""
            # تحديد الدور
            if new_role == "owner" and cur_own == "TRUE":
                users_sheet.update(f"D{i}:F{i}", [[True, False, False]])
                label = "تم إلغاء صلاحية المالك"
            elif new_role == "admin" and cur_adm == "TRUE" and cur_own != "TRUE":
                users_sheet.update(f"D{i}:F{i}", [[True, False, False]])
                label = "تم إلغاء صلاحية الأدمن"
            elif (new_role == "user" and cur_allow == "TRUE"
                  and cur_adm != "TRUE" and cur_own != "TRUE"):
                users_sheet.update(f"D{i}:F{i}", [[False, False, False]])
                label = "⛔ تم إلغاء الصلاحية"
                try: bot.send_message(int(target_uid), "⛔ تم إلغاء صلاحيتك.")
                except: pass
                notify_owners_decision(int(target_uid), t_name, t_phone,
                                       decided_by, False)
            elif new_role == "owner":
                users_sheet.update(f"D{i}:F{i}", [[True, True, True]])
                label = "👑 تم تعيين مالك"
                try: bot.send_message(int(target_uid), "👑 تمت ترقيتك إلى مالك!")
                except: pass
                notify_owners_decision(int(target_uid), t_name, t_phone,
                                       decided_by, True)
            elif new_role == "admin":
                users_sheet.update(f"D{i}:F{i}", [[True, True, False]])
                label = "⭐ تم تعيين أدمن"
                try: bot.send_message(int(target_uid), "⭐ تمت ترقيتك إلى أدمن!")
                except: pass
                notify_owners_decision(int(target_uid), t_name, t_phone,
                                       decided_by, True)
            else:
                users_sheet.update(f"D{i}:F{i}", [[True, False, False]])
                label = "👤 تم تعيين مستخدم"
                try: bot.send_message(int(target_uid), bt("رسالة_موافقة"))
                except: pass
                notify_owners_decision(int(target_uid), t_name, t_phone,
                                       decided_by, True)
            # تحديث البطاقة
            try:
                rows2 = users_sheet.get_all_values()
                for row2 in rows2[1:]:
                    if len(row2) > 2 and row2[2].strip().lstrip("'") == target_uid:
                        o2 = row2[5].strip().upper() if len(row2) > 5 else "FALSE"
                        a2 = row2[4].strip().upper() if len(row2) > 4 else "FALSE"
                        l2 = row2[3].strip().upper() if len(row2) > 3 else "FALSE"
                        ic = ("👑" if o2 == "TRUE" else ("⭐" if a2 == "TRUE" else
                               ("👤" if l2 == "TRUE" else "❌")))
                        ph2 = (f"\n📞 `{row2[1].strip()}`"
                               if len(row2) > 1 and row2[1].strip() else "")
                        new_text = (f"{ic} *{row2[0].strip()}*\n"
                                    f"🆔 `{target_uid}`{ph2}\n{'─'*23}")
                        bot.edit_message_text(
                            new_text, call.message.chat.id,
                            call.message.message_id,
                            parse_mode="Markdown",
                            reply_markup=user_card_markup(target_uid))
                        break
            except Exception as e2:
                if "message is not modified" not in str(e2):
                    log_error(f"role edit: {e2}")
            bot.answer_callback_query(call.id, label); return
        bot.answer_callback_query(call.id, "❌ المستخدم غير موجود")
    except Exception as e:
        log_error(f"handle_role: {e}")
        bot.answer_callback_query(call.id, "❌ خطأ")


@bot.callback_query_handler(func=lambda call: (call.data.startswith("approve_") or
                                                call.data.startswith("reject_")))
def handle_approval(call):
    caller_id = call.from_user.id
    if not is_owner_id(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح"); return
    decided_by = (f"@{call.from_user.username}" if call.from_user.username
                  else call.from_user.full_name)
    if call.data.startswith("approve_"):
        parts          = call.data.split("_", 2)
        requester_id   = int(parts[1])
        requester_name = parts[2] if len(parts) > 2 else "مستخدم"
        phone = ""
        try:
            uid_str = str(requester_id)
            rows    = users_sheet.get_all_values()
            for row in rows[1:]:
                if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                    phone = row[1].strip() if len(row) > 1 else ""; break
            found = False; es = 0
            for i, row in enumerate(rows[1:], start=2):
                if not row or not any(c.strip() for c in row):
                    es += 1
                    if es >= 5: break
                    continue
                es = 0
                if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                    users_sheet.update_cell(i, 4, True)
                    found = True; break
            if not found:
                add_user_to_sheet(requester_name, requester_id)
            pending_requests.discard(requester_id)
            try: bot.send_message(requester_id, bt("رسالة_موافقة"))
            except: pass
            notify_owners_decision(requester_id, requester_name, phone,
                                   decided_by, True)
        except Exception as e:
            log_error(f"approve: {e}")
            bot.answer_callback_query(call.id, "❌ خطأ في الحفظ"); return
    else:
        requester_id = int(call.data.split("_")[1])
        phone = ""; requester_name = ""
        try:
            for row in users_sheet.get_all_values()[1:]:
                if len(row) > 2 and row[2].strip().lstrip("'") == str(requester_id):
                    phone          = row[1].strip() if len(row) > 1 else ""
                    requester_name = row[0].strip(); break
        except: pass
        pending_requests.discard(requester_id)
        try: bot.send_message(requester_id, bt("رسالة_رفض_طلب"))
        except: pass
        notify_owners_decision(requester_id, requester_name, phone,
                               decided_by, False)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: (call.data.startswith("ms_subj:") or
                                                call.data.startswith("ms_type:")))
def handle_multiselect(call):
    uid    = call.from_user.id
    state  = user_state.get(uid, {})
    parts  = call.data.split(":", 1)
    prefix = parts[0]; value = parts[1]

    if prefix == "ms_subj":
        subjects = get_subjects()
        sel_key  = "sel_subjects"
        items    = [(s, s) for s in subjects]
        all_vals = subjects
    elif prefix == "ms_type":
        sel_key  = "sel_types"
        items    = [("محاضرات", "محاضرات"), ("تكاليف", "تكاليف"),
                    ("ملخصات", "ملخصات")]
        all_vals = ["محاضرات", "تكاليف", "ملخصات"]
    else:
        bot.answer_callback_query(call.id); return

    selected = set(state.get(sel_key, []))

    if value == "__all__":
        if "__all__" in selected or set(all_vals) == selected:
            selected = set()
        else:
            selected = set(all_vals) | {"__all__"}
    elif value == "__done__":
        real_sel = [v for v in selected if v != "__all__"]
        if not real_sel:
            bot.answer_callback_query(call.id, "⚠️ اختر واحداً على الأقل")
            return
        user_state[uid][sel_key] = real_sel
        bot.answer_callback_query(call.id)
        if prefix == "ms_subj":
            user_state[uid]["step"] = "choose_type"
            items2 = [("محاضرات", "محاضرات"), ("تكاليف", "تكاليف"),
                      ("ملخصات", "ملخصات")]
            kb = build_multiselect_kb(items2, set(), "ms_type")
            try:
                bot.edit_message_text("📋 اختر المطلوب:",
                                      call.message.chat.id,
                                      call.message.message_id,
                                      reply_markup=kb)
            except:
                bot.send_message(call.message.chat.id,
                                 "📋 اختر المطلوب:", reply_markup=kb)
        else:
            # تحديد طريقة العرض تلقائياً أو سؤال
            search_mode = state.get("search_mode", "day")
            sel_subjs   = [v for v in state.get("sel_subjects", [])
                           if v != "__all__"]
            if search_mode == "range" and len(sel_subjs) > 1:
                user_state[uid]["step"] = "choose_display"
                try:
                    bot.edit_message_text("📊 اختر طريقة العرض:",
                                          call.message.chat.id,
                                          call.message.message_id,
                                          reply_markup=telebot.types.InlineKeyboardMarkup())
                except: pass
                bot.send_message(call.message.chat.id,
                                 "📊 اختر طريقة العرض:",
                                 reply_markup=display_mode_menu())
            else:
                # تلقائي: مادة واحدة → حسب التاريخ | متعدد+يوم → حسب المادة
                user_state[uid]["display_mode"] = (
                    "date" if len(sel_subjs) == 1 else "subject")
                _execute_search(call.message.chat.id, uid)
        return
    else:
        if value in selected:
            selected.discard(value); selected.discard("__all__")
        else:
            selected.add(value)
        if set(all_vals) <= selected: selected.add("__all__")
        else: selected.discard("__all__")

    user_state[uid][sel_key] = list(selected)
    kb = build_multiselect_kb(items, selected, prefix)
    try:
        bot.edit_message_reply_markup(call.message.chat.id,
                                      call.message.message_id,
                                      reply_markup=kb)
    except: pass
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("file_req:"))
def handle_file_request_decision(call):
    caller_id = call.from_user.id
    if not _is_admin_or_owner(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح"); return
    parts     = call.data.split(":")
    action    = parts[1]; req_uid  = int(parts[2])
    date_val  = parts[3]; subject  = parts[4]
    col       = int(parts[5]); file_id = parts[6]
    decided_by = (f"@{call.from_user.username}" if call.from_user.username
                  else call.from_user.full_name)
    if action == "approve":
        save_file_to_cell(date_val, subject, col, [file_id])
        try:
            bot.send_message(
                req_uid,
                f"✅ تمت الموافقة على ملفك!\n📌 {subject}\n📅 {date_val}")
        except: pass
        try:
            bot.edit_message_reply_markup(
                call.message.chat.id, call.message.message_id,
                reply_markup=telebot.types.InlineKeyboardMarkup())
            bot.send_message(call.message.chat.id,
                             f"✅ موافقة بواسطة {decided_by} | {subject} {date_val}")
        except: pass
    else:
        try:
            bot.send_message(
                req_uid,
                f"❌ تم رفض طلب رفع ملف\n📌 {subject}\n📅 {date_val}")
        except: pass
        try:
            bot.edit_message_reply_markup(
                call.message.chat.id, call.message.message_id,
                reply_markup=telebot.types.InlineKeyboardMarkup())
            bot.send_message(call.message.chat.id,
                             f"❌ رفض بواسطة {decided_by} | {subject} {date_val}")
        except: pass
    bot.answer_callback_query(call.id)


def _execute_search(chat_id, uid):
    state        = user_state.get(uid, {})
    df           = state.get("date_filter")
    subjs        = [v for v in state.get("sel_subjects", []) if v != "__all__"]
    types_f      = [v for v in state.get("sel_types", [])    if v != "__all__"]
    display_mode = state.get("display_mode", "subject")
    user_state.pop(uid, None)
    welcome, _ = get_settings()
    allowed, admins, owners, open_all, admin_all, _ = get_users()
    adm = admin_all or uid in admins; own = uid in owners
    send_search_results(chat_id, uid, df, subjs, types_f, display_mode)
    bot.send_message(chat_id, welcome,
                     reply_markup=main_menu(uid, admin=adm, owner=own))


# ─────────────────────────────────────────────────────
# Command handlers
# ─────────────────────────────────────────────────────
@bot.message_handler(commands=['start'])
def start_message(message):
    uid = message.from_user.id
    load_user_lang(uid)
    welcome, rejection = get_settings()
    allowed, admins, owners, open_all, admin_all, _ = get_users()
    is_allowed = open_all or uid in allowed
    if not is_allowed:
        if not is_pending(uid): pending_requests.add(uid)
        bot.send_message(message.chat.id, rejection)
        cm = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        cm.add(telebot.types.KeyboardButton("📱 مشاركة جهة الاتصال", request_contact=True))
        bot.send_message(message.chat.id, "📲 شارك جهة اتصالك لتسهيل التواصل معك:", reply_markup=cm)
        return
    user_state.pop(uid, None)
    admin = admin_all or uid in admins
    owner = uid in owners
    log_info("START", uid)
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin, owner=owner))


@bot.message_handler(commands=['server'])
def server_command(message):
    inline = telebot.types.InlineKeyboardMarkup()
    inline.add(telebot.types.InlineKeyboardButton(
        "🔄 تشغيل البوت", url="https://telegram-bot1-cxnc.onrender.com"))
    bot.send_message(message.chat.id, "اضغط الزر لتشغيل البوت:", reply_markup=inline)


@bot.message_handler(commands=['lang'])
def language_command(message):
    uid = message.from_user.id
    load_user_lang(uid)
    _, rejection = get_settings()
    allowed, _, _, open_all, _, _ = get_users()
    if not (open_all or uid in allowed):
        bot.send_message(message.chat.id, rejection); return
    user_state[uid] = {"choosing_lang": True}
    bot.send_message(message.chat.id, "🌐 اختر اللغة / Choose Language", reply_markup=lang_menu())


@bot.message_handler(commands=['help'])
def help_message(message):
    uid = message.from_user.id
    load_user_lang(uid)
    _, admins, owners, _, admin_all, _ = get_users()
    admin = admin_all or uid in admins
    owner = uid in owners
    if admin or owner:
        user_state[uid] = {"viewing_help": True}
        bot.send_message(message.chat.id, "اختر:", reply_markup=help_view_menu())
    else:
        send_help_materials(message.chat.id, uid, "user")

# ─────────────────────────────────────────────────────
# Contact handler
# ─────────────────────────────────────────────────────
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    uid   = message.from_user.id
    phone = message.contact.phone_number if message.contact else ""
    name  = message.from_user.full_name or "مجهول"
    try:
        rows = users_sheet.get_all_values()
        uid_str = str(uid); found = False; es = 0
        for i, row in enumerate(rows[1:], start=2):
            if not row or not any(c.strip() for c in row):
                es += 1
                if es >= 5: break
                continue
            es = 0
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                users_sheet.update(f"A{i}:B{i}", [[name, phone]])
                found = True; break
        if not found:
            users_sheet.append_row([name, phone, uid, False, False, False, False, False],
                                    value_input_option="USER_ENTERED")
    except Exception as e:
        log_error(f"handle_contact: {e}")
    notify_owners_new_request(uid, name, phone)
    bot.send_message(message.chat.id, "✅ شكراً! تم إرسال معلوماتك.",
                     reply_markup=telebot.types.ReplyKeyboardRemove())

# ─────────────────────────────────────────────────────
# File handler
# ─────────────────────────────────────────────────────
@bot.message_handler(content_types=['document', 'photo', 'video', 'audio', 'voice'])
def handle_file(message):
    uid = message.from_user.id
    load_user_lang(uid)
    _, rejection = get_settings()
    allowed, admins, owners, open_all, admin_all, _ = get_users()
    if not (open_all or uid in allowed):
        bot.send_message(message.chat.id, rejection); return
    auto_register_user(message, open_all=open_all)
    f_admin = admin_all or uid in admins
    f_owner = uid in owners
    state   = user_state.get(uid, {})

    if   message.document: file_id, ftype = message.document.file_id, "document"
    elif message.photo:    file_id, ftype = message.photo[-1].file_id, "photo"
    elif message.video:    file_id, ftype = message.video.file_id,     "video"
    elif message.audio:    file_id, ftype = message.audio.file_id,     "audio"
    elif message.voice:    file_id, ftype = message.voice.file_id,     "voice"
    else: return

    def _reset_timer(key, fn):
        t_old = user_state.get(uid, {}).get("_timer")
        if t_old:
            try: t_old.cancel()
            except: pass
        t = threading.Timer(3.0, fn)
        user_state[uid]["_timer"] = t
        t.start()

    # رفع ملف أدمن — يستمر باستقبال حتى "إرسال"
    if state.get("uploading") and state.get("step") in ("waiting_files", "confirm_files"):
        if not (f_admin or f_owner):
            bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
        user_state[uid]["step"] = "waiting_files"
        user_state[uid].setdefault("pending_files", []).append(
            {"file_id": file_id, "file_type": ftype})
        def _finish_upload():
            st = user_state.get(uid, {})
            if st.get("step") == "waiting_files":
                user_state[uid]["step"] = "confirm_files"
                n = len(st.get("pending_files", []))
                bot.send_message(message.chat.id,
                    f"📎 تم استلام {n} ملف.\nأرسل المزيد أو اضغط *إرسال*:",
                    parse_mode="Markdown", reply_markup=upload_confirm_menu())
        _reset_timer("uploading", _finish_upload)
        return

    # طلب رفع مستخدم — يستمر باستقبال حتى "إرسال"
    if state.get("requesting_upload") and state.get("step") in ("waiting_files_req", "confirm_req"):
        user_state[uid]["step"] = "waiting_files_req"
        user_state[uid].setdefault("pending_files", []).append(
            {"file_id": file_id, "file_type": ftype})
        def _finish_req():
            st = user_state.get(uid, {})
            if st.get("step") == "waiting_files_req":
                user_state[uid]["step"] = "confirm_req"
                n = len(st.get("pending_files", []))
                bot.send_message(message.chat.id,
                    f"📎 تم استلام {n} ملف.\nاضغط *إرسال* لإرسال الطلب:",
                    parse_mode="Markdown", reply_markup=upload_confirm_menu())
        _reset_timer("requesting_upload", _finish_req)
        return

    # رفع تعليمات
    if state.get("uploading_help") and state.get("step") == "waiting_file_help":
        if not (f_admin or f_owner):
            bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
        user_state[uid].setdefault("pending_files", []).append(
            {"file_id": file_id, "file_type": ftype})
        def _finish_help():
            st = user_state.get(uid, {})
            if st.get("step") == "waiting_file_help":
                files    = st.get("pending_files", [])
                audience = st.get("audience", "user")
                note     = st.get("note", "")
                if save_help_material(files, audience, note):
                    bot.send_message(message.chat.id, "✅ تم الحفظ!",
                                     reply_markup=main_menu(uid, admin=f_admin, owner=f_owner))
                else:
                    bot.send_message(message.chat.id, bt("رسالة_خطأ"))
                user_state.pop(uid, None)
        _reset_timer("uploading_help", _finish_help)
        return

    # بث
    if state.get("broadcasting") and state.get("step") == "waiting_file_or_send":
        if not (f_admin or f_owner):
            bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
        user_state[uid].setdefault("broadcast_files", []).append(
            {"file_id": file_id, "file_type": ftype})
        return

    if not (f_admin or f_owner):
        bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
    bot.send_message(message.chat.id, "📤 لرفع ملف اضغط *رفع ملف* أولاً.",
                     parse_mode="Markdown")


# ─────────────────────────────────────────────────────
# helper: معالجة وقت المحاضرة
# ─────────────────────────────────────────────────────
def _process_lecture_time(chat_id, uid, state, time_val, admin, owner):
    subj = state.get("subject", ""); date = state.get("date", "")
    room = state.get("room", "")
    if time_val == "لا يوجد":
        if save_lecture(date, subj, time_val, room):
            mk = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            mk.add("➕ إضافة محاضرة أخرى", bt("زر_عوده"))
            user_state[uid]["step"] = "lecture_done"
            bot.send_message(chat_id,
                f"✅ تم الحفظ!\n📌 {subj}\n📅 {date}\n📍 {room}",
                reply_markup=mk)
        else:
            bot.send_message(chat_id, bt("رسالة_خطأ"))
            user_state.pop(uid, None)
        return
    conflict = check_lecture_conflict(date, time_val)
    if conflict:
        user_state[uid]["step"]     = "confirm_lecture_overwrite"
        user_state[uid]["time_val"] = time_val
        mk2 = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        mk2.row("🔄 استبدال", bt("زر_عوده"))
        bot.send_message(chat_id,
            f"⚠️ تداخل في الوقت!\n\n📌 {conflict['subject']}\n"
            f"🕐 {conflict['time']}\n📍 {conflict['room']}\n\n"
            f"الوقت `{time_val}` يتداخل معها.\nماذا تريد؟",
            parse_mode="Markdown", reply_markup=mk2)
    else:
        if save_lecture(date, subj, time_val, room):
            mk3 = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            mk3.add("➕ إضافة محاضرة أخرى", bt("زر_عوده"))
            user_state[uid]["step"]     = "lecture_done"
            user_state[uid]["time_val"] = time_val
            bot.send_message(chat_id,
                f"✅ تم حفظ المحاضرة!\n📌 {subj}\n📅 {date}\n🕐 {time_val}\n📍 {room}",
                reply_markup=mk3)
        else:
            bot.send_message(chat_id, bt("رسالة_خطأ"))
            user_state.pop(uid, None)

# ─────────────────────────────────────────────────────
# Main message handler
# ─────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    uid = message.from_user.id
    load_user_lang(uid)
    welcome, rejection = get_settings()
    allowed, admins, owners, open_all, admin_all, _ = get_users()
    is_allowed = open_all or uid in allowed
    admin      = admin_all or uid in admins
    owner      = uid in owners
    text       = (message.text or "").strip()
    state      = user_state.get(uid, {})
    back_btn   = bt("زر_عوده")

    # ── اختيار اللغة ──────────────────────────────
    if state.get("choosing_lang") or text in ["🇾🇪 العربية", "🇬🇧 English"]:
        if text == "🇾🇪 العربية":   user_lang[uid] = "ar"
        elif text == "🇬🇧 English": user_lang[uid] = "en"
        else:
            bot.send_message(message.chat.id, "🌐 اختر اللغة / Choose Language",
                             reply_markup=lang_menu()); return
        user_state.pop(uid, None)
        save_user_lang_to_sheet(uid, user_lang[uid])
        bot.send_message(message.chat.id, "✅ تم تغيير اللغة!",
                         reply_markup=telebot.types.ReplyKeyboardRemove())
        return

    # ── غير مسموح ─────────────────────────────────
    if not is_allowed:
        # كود سري
        code = calc_secret_code(uid)
        if text == code:
            try:
                uid_str = str(uid); rows = users_sheet.get_all_values()
                found = False; es = 0
                for i, row in enumerate(rows[1:], start=2):
                    if not row or not any(c.strip() for c in row):
                        es += 1
                        if es >= 5: break
                        continue
                    es = 0
                    if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                        users_sheet.update_cell(i, 4, True)
                        found = True; break
                if not found:
                    add_user_to_sheet(message.from_user.full_name or "مجهول", uid)
                pending_requests.discard(uid)
                bot.send_message(message.chat.id, bt("رسالة_موافقة"),
                                 reply_markup=telebot.types.ReplyKeyboardRemove())
                log_info(f"كود سري صحيح", uid)
            except Exception as e:
                log_error(f"secret_code activate: {e}")
                bot.send_message(message.chat.id, bt("رسالة_خطأ"))
            return
        if not is_pending(uid): pending_requests.add(uid)
        bot.send_message(message.chat.id, rejection)
        cm = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        cm.add(telebot.types.KeyboardButton("📱 مشاركة جهة الاتصال", request_contact=True))
        bot.send_message(message.chat.id, "📲 شارك جهة اتصالك:", reply_markup=cm)
        return

    if sheet is None:
        bot.send_message(message.chat.id, "❌ لا يوجد اتصال بقاعدة البيانات."); return

    auto_register_user(message, open_all=open_all)

    try:
        subjects_kb, subjects_list = subjects_menu_kb()
        data = get_data()

        # ══════════════════════════════════════════
        # زر العودة
        # ══════════════════════════════════════════
        if text == back_btn:
            if state.get("date_search"):
                step = state.get("step", "")
                if step == "choose_date_input":
                    user_state.pop(uid, None)
                    bot.send_message(message.chat.id, welcome,
                                     reply_markup=main_menu(uid, admin=admin, owner=owner))
                elif step == "choose_subjects":
                    user_state[uid]["step"] = "choose_date_input"
                    bot.send_message(message.chat.id,
                                     "📅 أدخل التاريخ أو الفترة:",
                                     reply_markup=back_only_menu())
                elif step == "choose_type":
                    user_state[uid]["step"] = "choose_subjects"
                    subjects = get_subjects()
                    sel      = set(state.get("sel_subjects", []))
                    kb       = build_multiselect_kb([(s, s) for s in subjects], sel, "ms_subj")
                    bot.send_message(message.chat.id, "📚 اختر المواد:", reply_markup=kb)
                elif step == "choose_display":
                    user_state[uid]["step"] = "choose_type"
                    items2 = [("محاضرات", "محاضرات"), ("تكاليف", "تكاليف"),
                              ("ملخصات", "ملخصات")]
                    sel2   = set(state.get("sel_types", []))
                    kb2    = build_multiselect_kb(items2, sel2, "ms_type")
                    bot.send_message(message.chat.id, "📋 اختر المطلوب:", reply_markup=kb2)
                else:
                    user_state.pop(uid, None)
                    bot.send_message(message.chat.id, welcome,
                                     reply_markup=main_menu(uid, admin=admin, owner=owner))
                return
            if state.get("uploading") or state.get("uploading_help") \
               or state.get("requesting_upload") or state.get("broadcasting") \
               or state.get("adding_data") or state.get("editing_data") \
               or state.get("managing_users") or state.get("viewing_help"):
                user_state.pop(uid, None)
                bot.send_message(message.chat.id, welcome,
                                 reply_markup=main_menu(uid, admin=admin, owner=owner)); return
            user_state.pop(uid, None)
            bot.send_message(message.chat.id, welcome,
                             reply_markup=main_menu(uid, admin=admin, owner=owner))
            return

        # ══════════════════════════════════════════
        # تعليمات (help)
        # ══════════════════════════════════════════
        if state.get("viewing_help"):
            if text == "👤 تعليمات المستخدم":
                send_help_materials(message.chat.id, uid, "user")
            elif text == "👑 تعليمات الأدمن":
                send_help_materials(message.chat.id, uid, "admin")
            else:
                bot.send_message(message.chat.id, "اختر:",
                                 reply_markup=help_view_menu()); return
            user_state.pop(uid, None)
            bot.send_message(message.chat.id, welcome,
                             reply_markup=main_menu(uid, admin=admin, owner=owner)); return

        # ══════════════════════════════════════════
        # 📅 البحث بالتاريخ
        # ══════════════════════════════════════════
        if text == bt("زر_التاريخ"):
            user_state[uid] = {"date_search": True, "step": "choose_date_type"}
            bot.send_message(message.chat.id, "📅 اختر نوع البحث:",
                             reply_markup=date_type_menu()); return

        if state.get("date_search"):
            step = state.get("step", "")

            if step == "choose_date_type":
                if text == bt("زر_يوم"):
                    user_state[uid]["search_mode"] = "day"
                    user_state[uid]["step"]        = "choose_date_input"
                    bot.send_message(message.chat.id,
                        "📅 أدخل اليوم (مثال: 27) أو التاريخ كاملاً (27/02/2026):",
                        reply_markup=back_only_menu())
                elif text == bt("زر_فتره"):
                    user_state[uid]["search_mode"] = "range"
                    user_state[uid]["step"]        = "choose_date_input"
                    bot.send_message(message.chat.id,
                        "📅 أدخل الفترة:\nمثال: 15-27\nأو تاريخين: 01/02/2026-28/02/2026",
                        reply_markup=back_only_menu())
                return

            if step == "choose_date_input":
                mode = state.get("search_mode", "day")
                if mode == "day":
                    d = parse_smart_date(text)
                    if not d:
                        bot.send_message(message.chat.id,
                            "❌ صيغة غير صحيحة.\nمثال: 27 أو 27/02/2026"); return
                    user_state[uid]["date_filter"] = d
                else:
                    d1, d2 = parse_date_range(text)
                    if not d1:
                        bot.send_message(message.chat.id,
                            "❌ صيغة غير صحيحة.\nمثال: 15-27"); return
                    user_state[uid]["date_filter"] = (d1, d2)
                user_state[uid]["step"] = "choose_subjects"
                subjects = get_subjects()
                kb = build_multiselect_kb([(s, s) for s in subjects], set(), "ms_subj")
                bot.send_message(message.chat.id, "📚 اختر المواد:", reply_markup=kb)
                return

            if step == "choose_display":
                if text == bt("زر_حسب_الماده"):
                    user_state[uid]["display_mode"] = "subject"
                elif text == bt("زر_حسب_التاريخ"):
                    user_state[uid]["display_mode"] = "date"
                else:
                    bot.send_message(message.chat.id, "📊 اختر طريقة العرض:",
                                     reply_markup=display_mode_menu()); return
                _execute_search(message.chat.id, uid)
            return

        # ══════════════════════════════════════════
        # 📚 المواد
        # ══════════════════════════════════════════
        if text == bt("زر_المواد"):
            user_state.pop(uid, None)
            bot.send_message(message.chat.id, "📌 اختر المادة:",
                             reply_markup=subjects_kb); return

        if text in subjects_list:
            user_state[uid] = {"subject": text}
            bot.send_message(message.chat.id,
                             f"📌 *{text}*\nماذا تحتاج؟",
                             parse_mode="Markdown",
                             reply_markup=subject_options_menu()); return

        SUBJ_OPTS = [bt(k) for k in ["خيار_الجدول", "خيار_التكاليف",
                                      "خيار_السعر", "خيار_الملخص", "خيار_التنبيهات"]]
        if state.get("subject") and text in SUBJ_OPTS:
            subj   = state["subject"]
            rows_s = [r for r in data if safe_get(r, 1) == subj]
            if text == bt("خيار_السعر"):
                price = next((get_text(safe_get(r, 5)) for r in rows_s
                              if safe_get(r, 5)), None)
                msg2  = (f"💰 *{subj}*: {price}" if price
                         else f"لا يوجد سعر لـ *{subj}*")
                bot.send_message(message.chat.id, msg2, parse_mode="Markdown",
                                 reply_markup=subject_options_menu()); return
            col_map3 = {bt("خيار_الجدول"): 2, bt("خيار_التكاليف"): 4,
                        bt("خيار_الملخص"): 6, bt("خيار_التنبيهات"): 7}
            col   = col_map3[text]
            dates = list(dict.fromkeys(
                parse_date(safe_get(r, 0)) for r in rows_s
                if (get_text(safe_get(r, col)) or get_file_ids(safe_get(r, col)))
                and safe_get(r, 0)))
            if not dates:
                no_map = {bt("خيار_الجدول"): "لا توجد محاضرات",
                          bt("خيار_التكاليف"): "لا توجد تكاليف",
                          bt("خيار_الملخص"): "لا توجد ملخصات",
                          bt("خيار_التنبيهات"): "لا توجد تنبيهات"}
                bot.send_message(message.chat.id,
                    f"{no_map.get(text, 'لا توجد بيانات')} لـ *{subj}*",
                    parse_mode="Markdown",
                    reply_markup=subject_options_menu()); return
            user_state[uid] = {"subject": subj, "action": text,
                               "awaiting_date": True, "col": col, "dates": dates}
            bot.send_message(message.chat.id, "📅 اختر التاريخ:",
                             reply_markup=dates_menu_kb(dates)); return

        if state.get("awaiting_date"):
            subj  = state["subject"]; col = state["col"]
            dates = state.get("dates", [])
            matched = [r for r in data
                       if safe_get(r, 1) == subj
                       and parse_date(safe_get(r, 0)) == text]
            if not matched:
                bot.send_message(message.chat.id, bt("رسالة_لا_بيانات"),
                                 reply_markup=dates_menu_kb(dates)); return
            day     = get_day_name(text, uid)
            d_ar    = format_date_ar(text)
            day_str = f" ({day})" if day else ""
            header  = f"*{subj}* — {d_ar}{day_str}\n{'─'*25}\n"
            all_text = header; all_fids = []
            for row in matched:
                cell = safe_get(row, col)
                val  = get_text(cell); fids = get_file_ids(cell)
                col_icon = {2: "🕐", 4: "📝", 6: "📖", 7: "⚠️"}.get(col, "")
                if val: all_text += f"{col_icon} {val}\n"
                all_fids.extend(fids)
            send_files_with_text(message.chat.id, all_text, all_fids,
                                 reply_markup=dates_menu_kb(dates)); return

        # ══════════════════════════════════════════
        # أزرار القائمة الرئيسية
        # ══════════════════════════════════════════
        if text == bt("زر_التكاليف"):
            ld = get_last_date(data, 4)
            if not ld:
                bot.send_message(message.chat.id, "📭 لا توجد تكاليف.",
                                 reply_markup=main_menu(uid, admin=admin, owner=owner)); return
            rows_s = [r for r in data if parse_date(safe_get(r, 0)) == ld
                      and (get_text(safe_get(r, 4)) or get_file_ids(safe_get(r, 4)))]
            day   = get_day_name(ld, uid); d_ar = format_date_ar(ld)
            header = f"📝 *{d_ar} — {day}*\n{'─'*25}\n"
            all_fids = []
            for row in rows_s:
                cell = safe_get(row, 4); tx = get_text(cell); fids = get_file_ids(cell)
                subj_n = safe_get(row, 1)
                if tx:   header += f"📌 {subj_n}: {tx}\n"
                elif fids: header += f"📌 {subj_n}: 📎 ملف\n"
                all_fids.extend(fids)
            send_files_with_text(message.chat.id, header, all_fids,
                                 reply_markup=main_menu(uid, admin=admin, owner=owner)); return

        if text == bt("زر_الجدول"):
            ld = get_last_date(data, 2)
            if not ld:
                bot.send_message(message.chat.id, "📭 لا توجد محاضرات.",
                                 reply_markup=main_menu(uid, admin=admin, owner=owner)); return
            rows_s = [r for r in data if parse_date(safe_get(r, 0)) == ld
                      and get_text(safe_get(r, 2))]
            day   = get_day_name(ld, uid); d_ar = format_date_ar(ld)
            resp  = f"🕐 *{d_ar} — {day}:*\n{'─'*25}\n"
            for r in rows_s: resp += f"📌 {safe_get(r, 1)}: {get_text(safe_get(r, 2))}\n"
            bot.send_message(message.chat.id, resp, parse_mode="Markdown",
                             reply_markup=main_menu(uid, admin=admin, owner=owner)); return

        if text == bt("زر_الملخصات"):
            ld = get_last_date(data, 6)
            if not ld:
                bot.send_message(message.chat.id, "📭 لا توجد ملخصات.",
                                 reply_markup=main_menu(uid, admin=admin, owner=owner)); return
            rows_s = [r for r in data if parse_date(safe_get(r, 0)) == ld
                      and (get_text(safe_get(r, 6)) or get_file_ids(safe_get(r, 6)))]
            day   = get_day_name(ld, uid); d_ar = format_date_ar(ld)
            header = f"📖 *{d_ar} — {day}*\n{'─'*25}\n"
            all_fids = []
            for row in rows_s:
                cell = safe_get(row, 6); tx = get_text(cell); fids = get_file_ids(cell)
                subj_n = safe_get(row, 1)
                if tx:   header += f"📌 {subj_n}: {tx}\n"
                elif fids: header += f"📌 {subj_n}: 📎 ملف\n"
                all_fids.extend(fids)
            send_files_with_text(message.chat.id, header, all_fids,
                                 reply_markup=main_menu(uid, admin=admin, owner=owner)); return

        if text == bt("زر_الاسعار"):
            seen = {}
            for r in data:
                s = safe_get(r, 1); p = get_text(safe_get(r, 5))
                if s and p and s not in seen: seen[s] = p
            if not seen:
                bot.send_message(message.chat.id, "📭 لا توجد أسعار.",
                                 reply_markup=main_menu(uid, admin=admin, owner=owner)); return
            mx    = max(len(s) for s in seen.keys())
            lines = "".join(f"📖 {s:<{mx}} : {p}\n" for s, p in seen.items())
            bot.send_message(message.chat.id,
                             f"💰 *أسعار الملازم:*\n```\n{lines}```",
                             parse_mode="Markdown",
                             reply_markup=main_menu(uid, admin=admin, owner=owner)); return

        if text == bt("زر_التنبيهات"):
            alerts = [(safe_get(r, 1), parse_date(safe_get(r, 0)),
                       get_text(safe_get(r, 7)))
                      for r in data if get_text(safe_get(r, 7))]
            if not alerts:
                bot.send_message(message.chat.id, "✅ لا توجد تنبيهات.",
                                 reply_markup=main_menu(uid, admin=admin, owner=owner)); return
            resp = "*⚠️ التنبيهات:*\n" + "─" * 25 + "\n"
            for s, d, a in alerts:
                d_ar = format_date_ar(d)
                resp += f"🔔 {s} ({d_ar}):\n{a}\n\n"
            bot.send_message(message.chat.id, resp, parse_mode="Markdown",
                             reply_markup=main_menu(uid, admin=admin, owner=owner)); return


        # ══════════════════════════════════════════
        # 📨 طلب رفع ملف (مستخدم)
        # ══════════════════════════════════════════
        if text == bt("زر_طلب_رفع"):
            user_state[uid] = {"requesting_upload": True, "step": "choose_subject"}
            bot.send_message(message.chat.id, "📌 اختر المادة:",
                             reply_markup=subjects_kb); return

        if state.get("requesting_upload"):
            step = state.get("step", "")

            if step == "choose_subject" and text in subjects_list:
                user_state[uid]["subject"] = text
                user_state[uid]["step"]    = "choose_type"
                bot.send_message(message.chat.id,
                    f"📌 *{text}*\nاختر النوع:",
                    parse_mode="Markdown",
                    reply_markup=file_type_menu()); return

            if step == "choose_type":
                if text == bt("زر_اضافة_تكليف"):
                    user_state[uid]["col"] = 4
                elif text == bt("زر_اضافة_ملخص"):
                    user_state[uid]["col"] = 6
                else: return
                user_state[uid]["step"] = "choose_date"
                subj = state.get("subject", "")
                bot.send_message(message.chat.id, "📅 أدخل التاريخ:",
                                 reply_markup=back_only_menu())
                send_date_suggestions(message.chat.id, subject=subj); return

            if step == "choose_date":
                d = parse_smart_date(text)
                if not d:
                    bot.send_message(message.chat.id,
                        "❌ صيغة غير صحيحة.\nمثال: `27/02/2026`",
                        parse_mode="Markdown"); return
                user_state[uid]["date"] = d
                user_state[uid]["step"] = "waiting_files_req"
                bot.send_message(message.chat.id,
                    "📎 أرسل الملف أو الملفات:",
                    reply_markup=back_only_menu()); return

            if step == "confirm_req":
                if text == "✅ إرسال":
                    files  = state.get("pending_files", [])
                    col    = state.get("col", 4)
                    subj   = state.get("subject", "")
                    date   = state.get("date", "")
                    req_uid = uid
                    if not files:
                        bot.send_message(message.chat.id, "⚠️ لم يتم استلام أي ملف."); return
                    # إرسال إشعار للأدمن/المالك مع inline موافقة/رفض
                    _, admins2, owners2, _, admin_all2, _ = get_users()
                    targets = list(set(admins2 + owners2))
                    col_label = "تكليف" if col == 4 else "ملخص"
                    for fdata in files:
                        fid = fdata["file_id"]
                        mk_req = telebot.types.InlineKeyboardMarkup()
                        mk_req.row(
                            telebot.types.InlineKeyboardButton(
                                "✅ قبول",
                                callback_data=f"file_req:approve:{req_uid}:{date}:{subj}:{col}:{fid}"),
                            telebot.types.InlineKeyboardButton(
                                "❌ رفض",
                                callback_data=f"file_req:reject:{req_uid}:{date}:{subj}:{col}:{fid}")
                        )
                        caption = (f"📨 طلب رفع {col_label}\n"
                                   f"👤 من: {message.from_user.full_name}\n"
                                   f"📌 {subj} | 📅 {date}")
                        for tid in targets:
                            try:
                                _try_send_file(tid, fid, caption=caption)
                                bot.send_message(tid, "👆 اختر:", reply_markup=mk_req)
                            except: pass
                    bot.send_message(message.chat.id,
                        "✅ تم إرسال الطلب! سيتم إخبارك بالنتيجة.",
                        reply_markup=main_menu(uid, admin=admin, owner=owner))
                    user_state.pop(uid, None)
                return
            return

        # ══════════════════════════════════════════
        # 👥 إدارة المستخدمين
        # ══════════════════════════════════════════
        if text == bt("زر_المستخدمين"):
            if not owner:
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
            user_state[uid] = {"managing_users": True, "step": "menu"}
            rows_all = users_sheet.get_all_values()
            entries  = []; es = 0
            for row in rows_all[1:]:
                if not row or not any(c.strip() for c in row):
                    es += 1
                    if es >= 5: break
                    continue
                es = 0
                name    = row[0].strip()
                uid_str = row[2].strip().lstrip("'") if len(row) > 2 else ""
                own_v   = row[5].strip().upper() if len(row) > 5 else "FALSE"
                adm_v   = row[4].strip().upper() if len(row) > 4 else "FALSE"
                if not name or name == "الكل" or not uid_str: continue
                entries.append((name, uid_str, own_v, adm_v, row))
            entries.sort(key=lambda x: (0 if x[2] == "TRUE" else 1 if x[3] == "TRUE" else 2))
            bot.send_message(message.chat.id,
                             "👥 *قائمة المستخدمين:*\n" + "─" * 25,
                             parse_mode="Markdown",
                             reply_markup=manage_users_menu())
            for _, _, _, _, row in entries:
                send_user_card(message.chat.id, row)
            return

        if state.get("managing_users"):
            step = state.get("step", "menu")
            if step == "menu":
                if text == "🔍 بحث بالID":
                    user_state[uid]["step"] = "search_id"
                    bot.send_message(message.chat.id, "🔍 أدخل الـ ID:",
                                     reply_markup=back_only_menu())
                elif text == "🔍 بحث بالرقم":
                    user_state[uid]["step"] = "search_phone"
                    bot.send_message(message.chat.id, "🔍 أدخل رقم الهاتف:",
                                     reply_markup=back_only_menu())
                return
            if step == "search_id":
                _, row = find_user_row_by_id(text.strip())
                if row: send_user_card(message.chat.id, row)
                else:   bot.send_message(message.chat.id, "❌ لم يُعثر على مستخدم")
                user_state[uid]["step"] = "menu"
                bot.send_message(message.chat.id, "↩️", reply_markup=manage_users_menu())
                return
            if step == "search_phone":
                _, row = find_user_row_by_phone(text.strip())
                if row: send_user_card(message.chat.id, row)
                else:   bot.send_message(message.chat.id, "❌ لم يُعثر على مستخدم")
                user_state[uid]["step"] = "menu"
                bot.send_message(message.chat.id, "↩️", reply_markup=manage_users_menu())
                return
            return

        # ══════════════════════════════════════════
        # 📢 بث الإشعارات
        # ══════════════════════════════════════════
        if text == bt("زر_اشعار"):
            if not (admin or owner):
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
            user_state[uid] = {"broadcasting": True, "step": "waiting_text"}
            m_bcast = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            m_bcast.add("📤 إرسال بدون نص", back_btn)
            bot.send_message(message.chat.id,
                             "اكتب نص الإشعار أو اضغط إرسال بدون نص:",
                             reply_markup=m_bcast); return

        if state.get("broadcasting"):
            step = state.get("step", "")
            if step == "waiting_text":
                if text == "📤 إرسال بدون نص": user_state[uid]["broadcast_text"] = ""
                else:                            user_state[uid]["broadcast_text"] = text
                user_state[uid]["step"] = "waiting_file_or_send"
                m_bcast2 = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                m_bcast2.add("📤 إرسال الآن", back_btn)
                bot.send_message(message.chat.id,
                                 "أرسل ملفاً (اختياري) أو اضغط إرسال الآن:",
                                 reply_markup=m_bcast2); return
            if step == "waiting_file_or_send":
                if text == "📤 إرسال الآن":
                    _do_broadcast(message.chat.id, uid, admin, owner,
                                  state.get("broadcast_text", ""),
                                  state.get("broadcast_files", []))
                    user_state.pop(uid, None)
                return

        # ══════════════════════════════════════════
        # 📹 رفع التعليمات
        # ══════════════════════════════════════════
        if text == bt("زر_رفع_تعليمات"):
            if not (admin or owner):
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
            user_state[uid] = {"uploading_help": True, "step": "choose_audience"}
            bot.send_message(message.chat.id, "👥 هذه التعليمات لمن؟",
                             reply_markup=help_audience_menu()); return

        if state.get("uploading_help"):
            step = state.get("step", "")
            if step == "choose_audience":
                if text == "👤 للمستخدمين":   user_state[uid]["audience"] = "user"
                elif text == "👑 للأدمن":      user_state[uid]["audience"] = "admin"
                else: return
                user_state[uid]["step"] = "enter_note"
                bot.send_message(message.chat.id,
                    "📝 أدخل نصاً توضيحياً (اختياري) أو اضغط تخطي:",
                    reply_markup=back_skip_menu()); return
            if step == "enter_note":
                user_state[uid]["note"] = "" if text == "⏭️ تخطي" else text
                user_state[uid]["step"] = "waiting_file_help"
                bot.send_message(message.chat.id,
                    "📎 أرسل الملف أو الملفات:",
                    reply_markup=back_skip_menu()); return
            if step == "waiting_file_help":
                if text == "⏭️ تخطي":
                    note = state.get("note", "")
                    if not note:
                        bot.send_message(message.chat.id,
                            "⚠️ لازم ترسل نص أو ملف على الأقل."); return
                    if save_help_material([], state.get("audience", "user"), note):
                        bot.send_message(message.chat.id, "✅ تم الحفظ!",
                                         reply_markup=main_menu(uid, admin=admin, owner=owner))
                    else:
                        bot.send_message(message.chat.id, bt("رسالة_خطأ"))
                    user_state.pop(uid, None)
                return

        # ══════════════════════════════════════════
        # 📤 رفع ملف (أدمن)
        # ══════════════════════════════════════════
        if text == bt("زر_رفع_ملف"):
            if not (admin or owner):
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
            user_state[uid] = {"uploading": True, "step": "choose_subject"}
            bot.send_message(message.chat.id, "📌 اختر المادة:",
                             reply_markup=subjects_kb); return

        if state.get("uploading"):
            step = state.get("step", "")
            if step == "choose_subject" and text in subjects_list:
                user_state[uid]["subject"] = text
                user_state[uid]["step"]    = "choose_type"
                bot.send_message(message.chat.id,
                    f"📌 *{text}*\nاختر النوع:",
                    parse_mode="Markdown",
                    reply_markup=file_type_menu()); return
            if step == "choose_type":
                if text == bt("زر_اضافة_تكليف"):   user_state[uid]["col"] = 4
                elif text == bt("زر_اضافة_ملخص"):  user_state[uid]["col"] = 6
                else: return
                user_state[uid]["step"] = "choose_date"
                subj = state.get("subject", "")
                bot.send_message(message.chat.id, "📅 أدخل التاريخ:",
                                 reply_markup=back_only_menu())
                send_date_suggestions(message.chat.id, subject=subj); return
            if step == "choose_date":
                d = parse_smart_date(text)
                if not d:
                    bot.send_message(message.chat.id,
                        "❌ صيغة غير صحيحة. مثال: `27/02/2026`",
                        parse_mode="Markdown")
                    send_date_suggestions(message.chat.id,
                                         subject=state.get("subject", "")); return
                user_state[uid]["date"] = d
                user_state[uid]["step"] = "waiting_files"
                bot.send_message(message.chat.id,
                    "📎 أرسل الملف أو الملفات:",
                    reply_markup=back_only_menu()); return
            if step == "confirm_files":
                if text == "✅ إرسال":
                    files = state.get("pending_files", [])
                    col   = state.get("col", 4)
                    subj  = state.get("subject", "")
                    date  = state.get("date", "")
                    fids  = [f["file_id"] for f in files]
                    if save_file_to_cell(date, subj, col, fids, merge=False):
                        bot.send_message(message.chat.id, bt("رسالة_تم_الحفظ"),
                                         reply_markup=main_menu(uid, admin=admin, owner=owner))
                    else:
                        bot.send_message(message.chat.id, bt("رسالة_خطأ"))
                    user_state.pop(uid, None)
                return
            return


        # ══════════════════════════════════════════
        # ➕ إضافة بيانات
        # ══════════════════════════════════════════
        if text == bt("زر_اضافة"):
            if not (admin or owner):
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
            user_state[uid] = {"adding_data": True, "step": "choose_type"}
            bot.send_message(message.chat.id, "اختر نوع البيانات:",
                             reply_markup=add_data_menu()); return

        if state.get("adding_data"):
            step = state.get("step", "")
            ADD_MAP = {
                bt("زر_اضافة_محاضره"): "lecture",
                bt("زر_اضافة_تكليف"):  "task",
                bt("زر_اضافة_ملخص"):   "summary",
                bt("زر_اضافة_سعر"):    "price",
                bt("زر_اضافة_تنبيه"):  "alert",
            }

            if step == "choose_type" and text in ADD_MAP:
                dtype = ADD_MAP[text]
                user_state[uid]["data_type"] = dtype
                if dtype == "lecture":
                    user_state[uid]["step"] = "enter_date"
                    bot.send_message(message.chat.id, "📅 أدخل تاريخ المحاضرة:",
                                     reply_markup=back_only_menu())
                    send_date_suggestions(message.chat.id, for_lecture=True)
                elif dtype in ("task", "summary", "alert", "price"):
                    user_state[uid]["step"] = "choose_subject"
                    bot.send_message(message.chat.id, "📌 اختر المادة:",
                                     reply_markup=subjects_kb)
                return

            if step == "choose_subject" and text in subjects_list:
                user_state[uid]["subject"] = text
                dtype = state.get("data_type", "")
                if dtype == "lecture":
                    user_state[uid]["step"] = "choose_building"
                    bot.send_message(message.chat.id, "🏛 اختر المبنى:",
                                     reply_markup=buildings_menu())
                elif dtype == "price":
                    user_state[uid]["step"] = "enter_value"
                    bot.send_message(message.chat.id, "💰 أدخل سعر الملزمة:",
                                     reply_markup=back_with_noexist())
                else:
                    user_state[uid]["step"] = "enter_date"
                    bot.send_message(message.chat.id, "📅 أدخل التاريخ:",
                                     reply_markup=back_only_menu())
                    send_date_suggestions(message.chat.id, subject=text,
                                         for_alert=(dtype == "alert"))
                return

            if step == "enter_date":
                d = parse_smart_date(text)
                if not d:
                    bot.send_message(message.chat.id,
                        "❌ صيغة غير صحيحة. مثال: `27/02/2026`",
                        parse_mode="Markdown")
                    send_date_suggestions(
                        message.chat.id,
                        for_lecture=(state.get("data_type") == "lecture"),
                        for_alert=(state.get("data_type") == "alert")); return
                user_state[uid]["date"] = d
                dtype = state.get("data_type", "")
                if dtype == "lecture":
                    user_state[uid]["step"] = "choose_building"
                    bot.send_message(message.chat.id, "🏛 اختر المبنى:",
                                     reply_markup=buildings_menu())
                elif dtype in ("task", "summary"):
                    user_state[uid]["step"] = "enter_value"
                    col_lbl = "التكليف" if dtype == "task" else "الملخص"
                    bot.send_message(message.chat.id,
                        f"📝 أدخل نص {col_lbl}:", reply_markup=back_with_noexist())
                elif dtype == "alert":
                    user_state[uid]["step"] = "enter_value"
                    bot.send_message(message.chat.id, "⚠️ أدخل نص التنبيه:",
                                     reply_markup=back_with_noexist())
                return

            if step == "choose_building":
                bmap = {"🏛 القديم": "القديم", "🏫 الاداب": "الاداب"}
                if text in bmap:
                    user_state[uid]["building"]       = bmap[text]
                    user_state[uid]["building_label"] = text
                    mk_rooms, rooms = rooms_menu_kb(bmap[text])
                    if not rooms:
                        bot.send_message(message.chat.id, "⚠️ لا توجد قاعات."); return
                    user_state[uid]["step"] = "choose_room"
                    bot.send_message(message.chat.id, "🚪 اختر القاعة:",
                                     reply_markup=mk_rooms)
                return

            if step == "choose_room":
                user_state[uid]["room"] = f"{state.get('building_label', '')}: {text}"
                dtype = state.get("data_type", "")
                if dtype == "lecture":
                    # bug fix: بعد اختيار الغرفة → اختيار المادة
                    if state.get("subject"):
                        user_state[uid]["step"] = "enter_time"
                        bot.send_message(message.chat.id, "🕐 اختر وقت المحاضرة:",
                                         reply_markup=lecture_time_menu())
                    else:
                        user_state[uid]["step"] = "choose_subject"
                        bot.send_message(message.chat.id, "📌 اختر المادة:",
                                         reply_markup=subjects_kb)
                return

            if step == "enter_time":
                TIME_MAP = {
                    "🕐 08:00 - 10:00": "08:00 - 10:00",
                    "🕐 10:00 - 12:00": "10:00 - 12:00",
                    "🕐 12:00 - 14:00": "12:00 - 14:00",
                }
                if text in TIME_MAP:
                    time_val = TIME_MAP[text]
                elif text == "⏰ توقيت آخر":
                    user_state[uid]["step"] = "enter_time_custom"
                    bot.send_message(message.chat.id,
                        "أدخل الوقت:\n`08:00 - 09:30`",
                        parse_mode="Markdown",
                        reply_markup=back_with_noexist()); return
                elif text == "لا يوجد":
                    time_val = "لا يوجد"
                else:
                    time_val = normalize_time(text)
                _process_lecture_time(message.chat.id, uid, state, time_val, admin, owner)
                return

            if step == "enter_time_custom":
                time_val = "لا يوجد" if text == "لا يوجد" else normalize_time(text)
                _process_lecture_time(message.chat.id, uid, state, time_val, admin, owner)
                return

            if step == "confirm_lecture_overwrite":
                subj     = state.get("subject", "")
                date     = state.get("date", "")
                room     = state.get("room", "")
                time_val = state.get("time_val", "")
                if text == "🔄 استبدال":
                    if save_lecture(date, subj, time_val, room):
                        mk_done = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
                        mk_done.add("➕ إضافة محاضرة أخرى", back_btn)
                        user_state[uid]["step"] = "lecture_done"
                        bot.send_message(message.chat.id,
                            f"✅ تم الاستبدال!\n📌 {subj}\n📅 {date}\n🕐 {time_val}\n📍 {room}",
                            reply_markup=mk_done)
                    else:
                        bot.send_message(message.chat.id, bt("رسالة_خطأ"))
                        user_state.pop(uid, None)
                return

            if step == "lecture_done":
                if text == "➕ إضافة محاضرة أخرى":
                    user_state[uid] = {
                        "adding_data":    True,
                        "step":           "choose_subject",
                        "data_type":      "lecture",
                        "date":           state.get("date", ""),
                        "room":           state.get("room", ""),
                        "building":       state.get("building", ""),
                        "building_label": state.get("building_label", ""),
                    }
                    bot.send_message(message.chat.id, "📌 اختر المادة:",
                                     reply_markup=subjects_kb)
                return

            if step == "enter_value":
                dtype = state.get("data_type", "")
                subj  = state.get("subject", "")
                date  = state.get("date", "")
                val   = text
                if dtype == "price":
                    rows_s = sheet.get_all_values(); updated = False
                    for i, row in enumerate(rows_s[1:], start=2):
                        if safe_get(row, 1) == subj:
                            sheet.update_cell(i, 6, val); updated = True; break
                    if not updated:
                        sheet.append_row(["", subj, "", "", "", val, "", ""],
                                         value_input_option="USER_ENTERED")
                    bot.send_message(message.chat.id, bt("رسالة_تم_الحفظ"),
                                     reply_markup=main_menu(uid, admin=admin, owner=owner))
                    user_state.pop(uid, None)
                else:
                    col_map2 = {"task": 4, "summary": 6, "alert": 7}
                    col      = col_map2.get(dtype, 4)
                    matched  = [r for r in data
                                if safe_get(r, 1) == subj
                                and parse_date(safe_get(r, 0)) == date]
                    existing = get_text(safe_get(matched[0], col)) if matched else ""
                    if existing:
                        user_state[uid]["step"]        = "confirm_overwrite"
                        user_state[uid]["existing_val"] = existing
                        user_state[uid]["pending_val"]  = val
                        mk_ow = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                        mk_ow.add("✏️ بجانبه", "🔄 بدله"); mk_ow.add(back_btn)
                        bot.send_message(message.chat.id,
                            f"⚠️ يوجد مدخل سابق:\n`{existing}`\n\nماذا تريد؟",
                            parse_mode="Markdown", reply_markup=mk_ow)
                    else:
                        ok = save_text_to_cell(date, subj, col, val)
                        bot.send_message(message.chat.id,
                            bt("رسالة_تم_الحفظ") if ok else bt("رسالة_خطأ"),
                            reply_markup=main_menu(uid, admin=admin, owner=owner))
                        user_state.pop(uid, None)
                return

            if step == "confirm_overwrite":
                dtype    = state.get("data_type", "")
                subj     = state.get("subject", "")
                date     = state.get("date", "")
                col      = {"task": 4, "summary": 6, "alert": 7}.get(dtype, 4)
                existing = state.get("existing_val", "")
                pending  = state.get("pending_val", "")
                if text == "✏️ بجانبه":   final = existing + " | " + pending
                elif text == "🔄 بدله":   final = pending
                else:
                    bot.send_message(message.chat.id, welcome,
                                     reply_markup=main_menu(uid, admin=admin, owner=owner))
                    user_state.pop(uid, None); return
                ok = save_text_to_cell(date, subj, col, final)
                bot.send_message(message.chat.id,
                    bt("رسالة_تم_الحفظ") if ok else bt("رسالة_خطأ"),
                    reply_markup=main_menu(uid, admin=admin, owner=owner))
                user_state.pop(uid, None)
                return
            return

        # ══════════════════════════════════════════
        # ✏️ تعديل/حذف بيانات
        # ══════════════════════════════════════════
        if text == bt("زر_تعديل"):
            if not (admin or owner):
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
            user_state[uid] = {"editing_data": True, "step": "choose_type"}
            bot.send_message(message.chat.id, "اختر نوع البيانات:",
                             reply_markup=edit_data_menu()); return

        if state.get("editing_data"):
            step = state.get("step", "")
            EDIT_MAP = {
                bt("زر_تعديل_محاضره"): "lecture",
                bt("زر_تعديل_تكليف"):  "task",
                bt("زر_تعديل_ملخص"):   "summary",
                bt("زر_تعديل_سعر"):    "price",
                bt("زر_تعديل_تنبيه"):  "alert",
            }
            COL_MAP = {"lecture": 2, "task": 4, "summary": 6, "price": 5, "alert": 7}

            if step == "choose_type" and text in EDIT_MAP:
                user_state[uid]["data_type"] = EDIT_MAP[text]
                user_state[uid]["step"]      = "choose_subject"
                bot.send_message(message.chat.id, "📌 اختر المادة:",
                                 reply_markup=subjects_kb); return

            if step == "choose_subject" and text in subjects_list:
                user_state[uid]["subject"] = text
                dtype = state.get("data_type", "")
                col   = COL_MAP.get(dtype, 2)
                if dtype == "price":
                    matched  = [r for r in data if safe_get(r, 1) == text]
                    current  = next((get_text(safe_get(r, 5)) for r in matched
                                     if safe_get(r, 5)), "")
                    user_state[uid]["step"]        = "choose_action"
                    user_state[uid]["current_val"] = current
                    user_state[uid]["date"]        = ""
                    bot.send_message(message.chat.id,
                        f"القيمة الحالية: *{current or 'فارغ'}*",
                        parse_mode="Markdown", reply_markup=edit_action_menu())
                else:
                    matched = [r for r in data if safe_get(r, 1) == text]
                    dates   = list(dict.fromkeys(
                        parse_date(safe_get(r, 0)) for r in matched
                        if (get_text(safe_get(r, col)) or get_file_ids(safe_get(r, col)))
                        and safe_get(r, 0)))
                    if not dates:
                        bot.send_message(message.chat.id, bt("رسالة_لا_بيانات"),
                                         reply_markup=edit_data_menu())
                        user_state[uid] = {"editing_data": True, "step": "choose_type"}
                    else:
                        user_state[uid]["step"] = "choose_date_edit"
                        user_state[uid]["col"]  = col
                        bot.send_message(message.chat.id, "📅 اختر التاريخ:",
                                         reply_markup=dates_menu_kb(dates))
                return

            if step == "choose_date_edit":
                subj    = state.get("subject", "")
                col     = state.get("col", 2)
                matched = [r for r in data
                           if safe_get(r, 1) == subj
                           and parse_date(safe_get(r, 0)) == text]
                if not matched:
                    bot.send_message(message.chat.id, bt("رسالة_لا_بيانات")); return
                current = get_text(safe_get(matched[0], col))
                user_state[uid]["date"]        = text
                user_state[uid]["current_val"] = current
                user_state[uid]["step"]        = "choose_action"
                bot.send_message(message.chat.id,
                    f"القيمة الحالية: *{current or 'فارغ'}*",
                    parse_mode="Markdown", reply_markup=edit_action_menu()); return

            if step == "choose_action":
                if text == bt("زر_تعديل_زرار"):
                    user_state[uid]["step"] = "enter_new_val"
                    bot.send_message(message.chat.id, "أدخل القيمة الجديدة:",
                                     reply_markup=back_only_menu())
                elif text == bt("زر_حذف_زرار"):
                    user_state[uid]["step"] = "confirm_delete"
                    cur = state.get("current_val", "")
                    mk_del = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                    mk_del.add("✅ نعم، احذف", "❌ إلغاء")
                    bot.send_message(message.chat.id,
                        f"⚠️ هل أنت متأكد من حذف:\n*{cur}*؟",
                        parse_mode="Markdown", reply_markup=mk_del)
                return

            if step == "confirm_delete":
                if text == "✅ نعم، احذف":
                    dtype = state.get("data_type", "")
                    subj  = state.get("subject", "")
                    date  = state.get("date", "")
                    col   = COL_MAP.get(dtype, 2)
                    if dtype == "price":
                        rows_s = sheet.get_all_values()
                        for i, row in enumerate(rows_s[1:], start=2):
                            if safe_get(row, 1) == subj:
                                sheet.update_cell(i, 6, ""); break
                        bot.send_message(message.chat.id, bt("رسالة_تم_الحذف"),
                                         reply_markup=main_menu(uid, admin=admin, owner=owner))
                    else:
                        ok = delete_cell(date, subj, col)
                        bot.send_message(message.chat.id,
                            bt("رسالة_تم_الحذف") if ok else bt("رسالة_خطأ"),
                            reply_markup=main_menu(uid, admin=admin, owner=owner))
                    user_state.pop(uid, None)
                elif text == "❌ إلغاء":
                    user_state[uid]["step"] = "choose_action"
                    bot.send_message(message.chat.id, "تم الإلغاء.",
                                     reply_markup=edit_action_menu())
                return

            if step == "enter_new_val":
                dtype = state.get("data_type", "")
                subj  = state.get("subject", "")
                date  = state.get("date", "")
                col   = COL_MAP.get(dtype, 2)
                if dtype == "price":
                    rows_s = sheet.get_all_values()
                    for i, row in enumerate(rows_s[1:], start=2):
                        if safe_get(row, 1) == subj:
                            sheet.update_cell(i, 6, text); break
                    bot.send_message(message.chat.id, bt("رسالة_تم_التعديل"),
                                     reply_markup=main_menu(uid, admin=admin, owner=owner))
                else:
                    ok = save_text_to_cell(date, subj, col, text)
                    bot.send_message(message.chat.id,
                        bt("رسالة_تم_التعديل") if ok else bt("رسالة_خطأ"),
                        reply_markup=main_menu(uid, admin=admin, owner=owner))
                user_state.pop(uid, None)
                return
            return

        bot.send_message(message.chat.id, "❓ اختر من القائمة.",
                         reply_markup=main_menu(uid, admin=admin, owner=owner))

    except Exception as e:
        bot.send_message(message.chat.id, bt("رسالة_خطأ"))
        log_error(f"handle_message uid={uid}: {e}", uid)


# ─────────────────────────────────────────────────────
# run
# ─────────────────────────────────────────────────────
def run():
    load_bot_texts()
    threading.Thread(target=_watch_sheet_loop, daemon=True).start()
    log_info("بوت الدراسة يعمل ✅")
    bot.infinity_polling()
