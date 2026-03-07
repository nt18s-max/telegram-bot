# ====================================================
# study_bot.py — بوت الدراسة (النسخة الكاملة)
# ====================================================
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import os, json, re, threading
from dotenv import load_dotenv
import pytz, logging
import requests as _requests

load_dotenv()

YEMEN_TZ        = pytz.timezone('Asia/Aden')
LOG_BOT_TOKEN   = os.environ.get("STUDY_BOT_LOG_TOKEN", "")
STUDY_BOT_TOKEN = os.environ.get("STUDY_BOT_TOKEN", "")
SHEET_KEY       = os.environ.get("SHEET_KEY", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("StudyBot")

bot   = telebot.TeleBot(STUDY_BOT_TOKEN)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    gcreds = os.environ.get("GOOGLE_CREDENTIALS")
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(gcreds), scope) if gcreds else \
             ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client          = gspread.authorize(creds)
    spreadsheet     = client.open_by_key(SHEET_KEY)
    sheet           = spreadsheet.sheet1
    users_sheet     = spreadsheet.worksheet("المستخدمين")
    help_sheet      = spreadsheet.worksheet("المساعدة")
    bot_texts_sheet = spreadsheet.worksheet("bot_texts")
    try:    rooms_sheet = spreadsheet.worksheet("القاعات")
    except: rooms_sheet = None
except Exception as e:
    logger.critical(f"خطأ Google Sheets: {e}")
    sheet = users_sheet = help_sheet = bot_texts_sheet = rooms_sheet = None

# ─────────────────────────────────────────────────────
# BOT_TEXTS
# ─────────────────────────────────────────────────────
DEFAULT_BOT_TEXTS = {
    "رسالة_الترحيب":    "مرحبًا! اختر أحد الخيارات:",
    "رسالة_الرفض":      "⛔ غير مسموح لك باستخدام البوت\n\nالرجاء طلب الصلاحية من منشئ البوت @nt18s",
    "رسالة_انتظار":     "⏳ تم إرسال طلبك، انتظر موافقة المالك.",
    "رسالة_موافقة":     "✅ تمت الموافقة على طلبك! أرسل /start للبدء.",
    "رسالة_رفض_طلب":   "❌ تم رفض طلبك.",
    "زر_المواد":        "📚 المواد",
    "زر_التاريخ":       "📅 التاريخ",
    "زر_التكاليف":      "📝 التكاليف",
    "زر_الجدول":        "🕐 أوقات المحاضرات",
    "زر_التنبيهات":     "⚠️ تنبيهات",
    "زر_الاسعار":       "💰 أسعار الملازم",
    "زر_رفع_ملف":       "📤 رفع ملف",
    "زر_رفع_تعليمات":   "📹 رفع التعليمات",
    "زر_اشعار":         "📢 إرسال إشعار",
    "زر_اضافة":         "➕ إضافة بيانات",
    "زر_تعديل":         "✏️ تعديل/حذف بيانات",
    "زر_المستخدمين":    "👥 إدارة المستخدمين",
    "زر_عوده":          "🔙 العودة",
    "زر_يوم":           "🔍 يوم",
    "زر_فتره":          "📆 فترة",
    "زر_تحديد_الكل":   "تحديد الكل",
    "زر_تم_التحديد":   "✔️ تم التحديد",
    "زر_حسب_الماده":   "📌 حسب الماده",
    "زر_حسب_التاريخ":  "📅 حسب التاريخ",
    "زر_اضافة_محاضره": "🕐 إضافة محاضرة",
    "زر_اضافة_تكليف":  "📝 إضافة تكليف",
    "زر_اضافة_ملخص":   "📖 إضافة ملخص",
    "زر_اضافة_سعر":    "💰 إضافة سعر ملزمة",
    "زر_اضافة_تنبيه":  "⚠️ إضافة تنبيه",
    "زر_تعديل_محاضره": "🕐 تعديل/حذف محاضرة",
    "زر_تعديل_تكليف":  "📝 تعديل/حذف تكليف",
    "زر_تعديل_ملخص":   "📖 تعديل/حذف ملخص",
    "زر_تعديل_سعر":    "💰 تعديل/حذف سعر",
    "زر_تعديل_تنبيه":  "⚠️ تعديل/حذف تنبيه",
    "زر_تعديل_زرار":   "✏️ تعديل",
    "زر_حذف_زرار":     "🗑 حذف",
    "رسالة_لا_بيانات":  "لا توجد بيانات",
    "رسالة_خطأ":        "❌ حدث خطأ، حاول مرة أخرى.",
    "رسالة_تم_الحفظ":   "✅ تم حفظ البيانات بنجاح!",
    "رسالة_تم_الحذف":   "✅ تم الحذف!",
    "رسالة_تم_التعديل": "✅ تم التعديل!",
    "رسالة_ادمن_فقط":   "⛔ فقط المدير يستطيع القيام بهذا.",
    "خيار_الجدول":      "🕐 أوقات المحاضرات",
    "خيار_التكاليف":    "📝 التكاليف",
    "خيار_السعر":       "💰 سعر الملزمة",
    "خيار_الملخص":      "📖 الملخص",
    "خيار_التنبيهات":   "⚠️ تنبيهات",
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
request_msg_ids  = {}  # {requester_id: {owner_id: msg_id}}

DAYS_AR   = {0:"الاثنين",1:"الثلاثاء",2:"الأربعاء",3:"الخميس",4:"الجمعة",5:"السبت",6:"الأحد"}
DAYS_EN   = {0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",4:"Friday",5:"Saturday",6:"Sunday"}
MONTHS_AR = {1:"يناير",2:"فبراير",3:"مارس",4:"أبريل",5:"مايو",6:"يونيو",
             7:"يوليو",8:"أغسطس",9:"سبتمبر",10:"أكتوبر",11:"نوفمبر",12:"ديسمبر"}

# ─────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────
def tg_log(level, msg):
    icons = {"INFO":"ℹ️","WARNING":"⚠️","ERROR":"❌","CRITICAL":"🚨"}
    now   = datetime.now(YEMEN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    text  = f"{icons.get(level,'📋')} *{level}*\n`{now}`\n\n{msg}"
    if LOG_BOT_TOKEN and users_sheet:
        try:
            es = 0
            for row in users_sheet.get_all_values()[1:]:
                if not row or not any(c.strip() for c in row):
                    es += 1
                    if es >= 5: break
                    continue
                es = 0
                uid_str = row[2].strip().lstrip("'") if len(row)>2 else ""
                if uid_str.isdigit() and (row[7].strip().upper() if len(row)>7 else "") == "TRUE":
                    try:
                        _requests.post(f"https://api.telegram.org/bot{LOG_BOT_TOKEN}/sendMessage",
                                       json={"chat_id":int(uid_str),"text":text,"parse_mode":"Markdown"},timeout=5)
                    except: pass
        except: pass
    getattr(logger, level.lower(), logger.info)(msg)

def log_info(m):     tg_log("INFO",m)
def log_warning(m):  tg_log("WARNING",m)
def log_error(m):    tg_log("ERROR",m)
def log_critical(m): tg_log("CRITICAL",m)

# ─────────────────────────────────────────────────────
# Google Sheets — قراءة
# ─────────────────────────────────────────────────────
def get_subjects():
    try:
        seen, result = set(), []
        for row in sheet.get_all_values()[1:]:
            s = row[1].strip() if len(row)>1 else ""
            if s and s not in seen: seen.add(s); result.append(s)
        return result
    except Exception as e:
        log_error(f"get_subjects: {e}"); return []

def get_rooms(building):
    try:
        if not rooms_sheet: return []
        return [r[1].strip() for r in rooms_sheet.get_all_values()
                if len(r)>1 and r[0].strip()==building and r[1].strip()]
    except: return []

def get_users():
    try:
        allowed,admins,owners,log_ids = [],[],[],[]
        open_all = admin_all = False
        es = 0
        for row in users_sheet.get_all_values()[1:]:
            if not row or not any(c.strip() for c in row):
                es += 1
                if es >= 5: break
                continue
            es = 0
            name        = row[0].strip()
            uid_str     = row[2].strip().lstrip("'") if len(row)>2 else ""
            allowed_val = row[3].strip().upper() if len(row)>3 else "FALSE"
            admin_val   = row[4].strip().upper() if len(row)>4 else "FALSE"
            owner_val   = row[5].strip().upper() if len(row)>5 else "FALSE"
            log_val     = row[7].strip().upper() if len(row)>7 else "FALSE"
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
        log_error(f"get_users: {e}"); return [],[],[],False,False,[]

def get_user_lang_from_sheet(uid):
    try:
        for row in users_sheet.get_all_values()[1:]:
            if len(row)>2 and row[2].strip().lstrip("'").isdigit() and int(row[2].strip().lstrip("'"))==uid:
                return "en" if (row[6].strip().upper() if len(row)>6 else "")=="TRUE" else "ar"
        return "ar"
    except: return "ar"

def save_user_lang_to_sheet(uid, lang):
    try:
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if len(row)>2 and row[2].strip().lstrip("'").isdigit() and int(row[2].strip().lstrip("'"))==uid:
                users_sheet.update_cell(i, 7, lang=="en"); return True
        return False
    except: return False

def load_user_lang(uid):
    if uid not in user_lang:
        user_lang[uid] = get_user_lang_from_sheet(uid)

def get_owner_ids():
    _,_,owners,_,_,_ = get_users(); return owners

def is_owner_id(uid): return uid in get_owner_ids()
def is_owner(msg):    return is_owner_id(msg.from_user.id)

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
            if len(row)>2 and row[2].strip().lstrip("'")==uid_str: return True
    except: pass
    return False

def add_user_to_sheet(name, uid, auto=False, allowed=True):
    try:
        display = f"🆕 {name}" if auto else name
        users_sheet.append_row([display,"",uid,allowed,False,False,False,False], value_input_option="USER_ENTERED")
        return True
    except: return False

def auto_register_user(message, open_all=None):
    try:
        if open_all is None: _,_,_,open_all,_,_ = get_users()
        if not open_all: return
        uid_str = str(message.from_user.id)
        for row in users_sheet.get_all_values()[1:]:
            if len(row)>2 and row[2].strip().lstrip("'")==uid_str: return
        add_user_to_sheet(message.from_user.full_name or "مجهول", message.from_user.id, auto=True, allowed=False)
    except: pass

def find_user_row_by_id(search_id):
    try:
        sid = str(search_id).strip()
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows, start=1):
            if len(row)>2 and row[2].strip().lstrip("'")==sid: return i, row
        return None, None
    except: return None, None

def find_user_row_by_phone(phone):
    try:
        pc = re.sub(r'[\s\-\+]','',phone.strip())
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows, start=1):
            rp = re.sub(r'[\s\-\+]','', row[1].strip() if len(row)>1 else "")
            if rp and rp==pc: return i, row
        return None, None
    except: return None, None

def get_all_user_ids():
    allowed,_,_,open_all,_,_ = get_users(); return allowed, open_all

def get_all_registered_uids():
    try:
        uids = []; es = 0
        for row in users_sheet.get_all_values()[1:]:
            if not row or not any(c.strip() for c in row):
                es += 1
                if es >= 5: break
                continue
            es = 0
            uid_str = row[2].strip().lstrip("'") if len(row)>2 else ""
            if uid_str.isdigit(): uids.append(int(uid_str))
        return uids
    except: return []


# ─────────────────────────────────────────────────────
# Data helpers
# ─────────────────────────────────────────────────────
def safe_get(row, idx):
    v = row[idx].strip() if len(row)>idx else ""
    return v.lstrip("'").strip() if v else ""

def get_text(cell):
    return cell.split("|")[0].strip() if "|" in cell else cell.strip()

def get_file_ids(cell):
    if "|" not in cell: return []
    part = cell.split("|",1)[1].strip()
    return [f.strip() for f in part.split(",") if f.strip()] if part else []

def merge_cell(text, fids):
    if not fids: return text
    fids_str = ",".join(fids) if isinstance(fids, list) else fids
    return f"{text}|{fids_str}" if fids_str else text

def parse_date(d):
    for fmt in ("%d/%m/%Y","%Y-%m-%d","%m/%d/%Y"):
        try: return datetime.strptime(d.strip(),fmt).strftime("%d/%m/%Y")
        except: continue
    return d.strip()

def is_valid_date(d):
    for fmt in ("%d/%m/%Y","%Y-%m-%d","%m/%d/%Y"):
        try: datetime.strptime(d.strip(),fmt); return True
        except: continue
    return False

def smart_date_from_day(day):
    now = datetime.now(YEMEN_TZ)
    if day > now.day:
        try: return now.replace(day=day).strftime("%d/%m/%Y")
        except: return now.strftime("%d/%m/%Y")
    else:
        first = now.replace(day=1)
        last_m = first - timedelta(days=1)
        try: return last_m.replace(day=day).strftime("%d/%m/%Y")
        except: return now.strftime("%d/%m/%Y")

def parse_smart_date(text):
    text = text.strip()
    if is_valid_date(text): return parse_date(text)
    if text.isdigit():
        d = int(text)
        if 1 <= d <= 31: return smart_date_from_day(d)
    return None

def parse_date_range(text):
    text = text.strip()
    m = re.match(r'(\d{1,2}/\d{1,2}/\d{4})\s*-\s*(\d{1,2}/\d{1,2}/\d{4})', text)
    if m and is_valid_date(m.group(1)) and is_valid_date(m.group(2)):
        return parse_date(m.group(1)), parse_date(m.group(2))
    m2 = re.match(r'^(\d{1,2})-(\d{1,2})$', text)
    if m2:
        return smart_date_from_day(int(m2.group(1))), smart_date_from_day(int(m2.group(2)))
    return None, None

def normalize_time(t):
    t = t.strip().replace("–","-").replace("—","-")
    t = re.sub(r'\s*-\s*',' - ',t)
    def pad(m): return f"{int(m.group(1)):02d}:{m.group(2)}"
    return re.sub(r'(\d{1,2}):(\d{2})',pad,t)

def parse_time_range(t):
    t = normalize_time(t)
    parts = re.split(r'\s*-\s*',t)
    if len(parts)!=2: return None, None
    def mins(s):
        s = s.strip()
        h,m = s.split(":") if ":" in s else (s,"0")
        return int(h)*60+int(m)
    try: return mins(parts[0]), mins(parts[1])
    except: return None, None

def check_lecture_conflict(date, time_val):
    try:
        ns, ne = parse_time_range(time_val)
        if ns is None: return None
        for row in get_data():
            rd = parse_date(safe_get(row,0))
            rt = safe_get(row,2)
            if rd!=date or not rt: continue
            es, ee = parse_time_range(rt)
            if es is None: continue
            if ns<ee and es<ne:
                return {"subject":safe_get(row,1),"room":safe_get(row,3),"time":normalize_time(rt)}
    except: pass
    return None

def get_day_name(date_str, uid=None):
    try:
        dt = datetime.strptime(date_str,"%d/%m/%Y")
        return DAYS_EN[dt.weekday()] if uid and user_lang.get(uid,"ar")=="en" else DAYS_AR[dt.weekday()]
    except: return ""

def format_date_ar(date_str):
    try:
        dt = datetime.strptime(date_str,"%d/%m/%Y")
        return f"{dt.day} {MONTHS_AR[dt.month]}"
    except: return date_str

def dates_in_range(date_str, d1, d2):
    try:
        dt  = datetime.strptime(date_str,"%d/%m/%Y")
        dt1 = datetime.strptime(d1,"%d/%m/%Y")
        dt2 = datetime.strptime(d2,"%d/%m/%Y")
        if dt1 > dt2: dt1, dt2 = dt2, dt1
        return dt1 <= dt <= dt2
    except: return False

def get_last_date(data, col):
    dates = []
    for r in data:
        d = safe_get(r,0)
        if d and (get_text(safe_get(r,col)) or get_file_ids(safe_get(r,col))):
            try: dates.append(parse_date(d))
            except: pass
    return sorted(dates, key=lambda x: datetime.strptime(x,"%d/%m/%Y"))[-1] if dates else None

def get_data():
    try:
        useful = []
        for r in sheet.get_all_values()[1:]:
            if any(len(r)>i and r[i].strip() for i in range(2,8)):
                useful.append(r)
        return useful
    except: return []

def get_last_lectures_for_subject(subject, n=3):
    try:
        seen, dates = set(), []
        for r in get_data():
            s=safe_get(r,1); d=safe_get(r,0); t=safe_get(r,2)
            if s==subject and d and t:
                p = parse_date(d)
                if p not in seen: seen.add(p); dates.append(p)
        dates.sort(key=lambda x: datetime.strptime(x,"%d/%m/%Y"), reverse=True)
        return dates[:n]
    except: return []

# ─────────────────────────────────────────────────────
# Sheet write helpers
# ─────────────────────────────────────────────────────
def save_file_to_cell(date, subject, col, fids, merge=False):
    try:
        fids = fids if isinstance(fids,list) else [fids]
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row,0) and parse_date(safe_get(row,0))==date and safe_get(row,1)==subject:
                current = safe_get(row,col)
                if merge:
                    all_fids = get_file_ids(current) + fids
                else:
                    all_fids = fids
                sheet.update_cell(i, col+1, merge_cell(get_text(current), all_fids))
                return True
        new_row=[""]*8; new_row[0]=date; new_row[1]=subject; new_row[col]=f"|{','.join(fids)}"
        sheet.append_row(new_row, value_input_option="USER_ENTERED"); return True
    except Exception as e:
        log_error(f"save_file_to_cell: {e}"); return False

def save_text_to_cell(date, subject, col, text_val):
    try:
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row,0) and parse_date(safe_get(row,0))==date and safe_get(row,1)==subject:
                existing_fids = get_file_ids(safe_get(row,col))
                sheet.update_cell(i, col+1, merge_cell(text_val, existing_fids)); return True
        new_row=[""]*8; new_row[0]=date; new_row[1]=subject; new_row[col]=text_val
        sheet.append_row(new_row, value_input_option="USER_ENTERED"); return True
    except Exception as e:
        log_error(f"save_text_to_cell: {e}"); return False

def save_lecture(date, subject, time_val, room):
    try:
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row,0) and parse_date(safe_get(row,0))==date and safe_get(row,1)==subject:
                sheet.update_cell(i,3,time_val); sheet.update_cell(i,4,room); return True
        new_row=[""]*8; new_row[0]=date; new_row[1]=subject; new_row[2]=time_val; new_row[3]=room
        sheet.append_row(new_row, value_input_option="USER_ENTERED"); return True
    except Exception as e:
        log_error(f"save_lecture: {e}"); return False

def delete_cell(date, subject, col):
    try:
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row,0) and parse_date(safe_get(row,0))==date and safe_get(row,1)==subject:
                sheet.update_cell(i, col+1, ""); return True
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
            fid   = row[1].strip() if len(row)>1 else ""
            ftype = row[2].strip() if len(row)>2 else ""
            aud   = row[3].strip() if len(row)>3 else "user"
            note  = row[4].strip() if len(row)>4 else ""
            if fid or note: mats.append({"file_id":fid,"file_type":ftype,"audience":aud,"note":note})
        return mats
    except: return []

def save_help_material(files_data, audience, note=""):
    try:
        rows = help_sheet.get_all_values()
        nrow = len(rows)+1
        if note:
            help_sheet.update([[f"note_{nrow}","","",audience,note]], f"A{nrow}:E{nrow}")
            nrow += 1
        for fd in files_data:
            help_sheet.update([[f"file_{nrow}",fd["file_id"],fd["file_type"],audience,""]], f"A{nrow}:E{nrow}")
            nrow += 1
        return True
    except Exception as e:
        log_error(f"save_help_material: {e}"); return False

def get_settings():
    return bt("رسالة_الترحيب"), bt("رسالة_الرفض")


# ─────────────────────────────────────────────────────
# إرسال الملفات (media group)
# ─────────────────────────────────────────────────────
def send_files_with_text(chat_id, text, fids, reply_markup=None):
    if not fids:
        if text: bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=reply_markup)
        return
    cap   = text[:1024] if text else None
    parse = "Markdown" if cap else None
    if len(fids)==1:
        fid = fids[0]
        for sender in [bot.send_photo, bot.send_video, bot.send_document, bot.send_audio, bot.send_voice]:
            try: sender(chat_id, fid, caption=cap, parse_mode=parse, reply_markup=reply_markup); return
            except: continue
        if text: bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        from telebot.types import InputMediaPhoto, InputMediaDocument
        sent = False
        for MediaType in [InputMediaPhoto, InputMediaDocument]:
            try:
                media = [MediaType(fid, caption=(cap if i==0 else None), parse_mode=(parse if i==0 else None))
                         for i, fid in enumerate(fids)]
                bot.send_media_group(chat_id, media)
                if reply_markup: bot.send_message(chat_id, ".", reply_markup=reply_markup)
                sent = True; break
            except: continue
        if not sent:
            if text: bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=reply_markup)
            for fid in fids:
                for sender in [bot.send_photo, bot.send_video, bot.send_document, bot.send_audio, bot.send_voice]:
                    try: sender(chat_id, fid); break
                    except: continue

# ─────────────────────────────────────────────────────
# إشعارات المالكين
# ─────────────────────────────────────────────────────
def notify_owners_new_request(requester_id, requester_name, phone=""):
    owners = get_owner_ids()
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("✅ قبول", callback_data=f"approve_{requester_id}_{requester_name}"),
        telebot.types.InlineKeyboardButton("❌ رفض",  callback_data=f"reject_{requester_id}")
    )
    ph  = f"📞 الرقم: `{phone}`\n" if phone else ""
    msg = f"📩 طلب انضمام جديد!\n\n👤 الاسم: `{requester_name}`\n🆔 المعرف: `{requester_id}`\n{ph}"
    if requester_id not in request_msg_ids: request_msg_ids[requester_id] = {}
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
    result = f"{status}:\n👤 `{requester_name}`\n🆔 `{requester_id}`\n{ph}من قِبل: {decided_by}"
    for oid in owners:
        try: bot.send_message(oid, result, parse_mode="Markdown")
        except: pass

# ─────────────────────────────────────────────────────
# Keyboards
# ─────────────────────────────────────────────────────
def main_menu(uid, admin=False, owner=False):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row(bt("زر_المواد"),     bt("زر_التاريخ"))
    m.row(bt("زر_التكاليف"),  bt("زر_الجدول"))
    m.row(bt("زر_التنبيهات"), bt("زر_الاسعار"))
    if admin or owner:
        m.row(bt("زر_اضافة"), bt("زر_تعديل"))
        m.row(bt("زر_رفع_تعليمات"), bt("زر_رفع_ملف"), bt("زر_اشعار"))
    if owner: m.add(bt("زر_المستخدمين"))
    return m

def back_only_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add(bt("زر_عوده")); return m

def back_skip_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row("⏭️ تخطي", bt("زر_عوده")); return m

def back_with_noexist(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("لا يوجد", bt("زر_عوده")); return m

def subjects_menu_kb(uid):
    subjects = get_subjects()
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for s in subjects: m.add(s)
    m.add(bt("زر_عوده")); return m, subjects

def subject_options_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for k in ["خيار_الجدول","خيار_التكاليف","خيار_السعر","خيار_الملخص","خيار_التنبيهات"]:
        m.add(bt(k))
    m.add(bt("زر_عوده")); return m

def dates_menu_kb(uid, dates):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for d in dates: m.add(d)
    m.add(bt("زر_عوده")); return m

def file_type_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(bt("زر_اضافة_تكليف"), bt("زر_اضافة_ملخص"))
    m.add(bt("زر_عوده")); return m

def add_data_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row(bt("زر_اضافة_محاضره"), bt("زر_اضافة_تكليف"))
    m.row(bt("زر_اضافة_ملخص"),   bt("زر_اضافة_سعر"))
    m.add(bt("زر_اضافة_تنبيه")); m.add(bt("زر_عوده")); return m

def edit_data_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row(bt("زر_تعديل_محاضره"), bt("زر_تعديل_تكليف"))
    m.row(bt("زر_تعديل_ملخص"),   bt("زر_تعديل_سعر"))
    m.add(bt("زر_تعديل_تنبيه")); m.add(bt("زر_عوده")); return m

def edit_action_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(bt("زر_تعديل_زرار"), bt("زر_حذف_زرار"))
    m.add(bt("زر_عوده")); return m

def buildings_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("🏛 القديم","🏫 الاداب"); m.add(bt("زر_عوده")); return m

def rooms_menu_kb(uid, building):
    rooms = get_rooms(building)
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for r in rooms: m.add(r)
    m.add(bt("زر_عوده")); return m, rooms

def lecture_time_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("🕐 08:00 - 10:00","🕐 10:00 - 12:00")
    m.add("🕐 12:00 - 14:00","⏰ توقيت آخر")
    m.add(bt("زر_عوده")); return m

def manage_users_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row("🔍 بحث بالID","🔍 بحث بالرقم")
    m.add(bt("زر_عوده")); return m

def display_mode_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row(bt("زر_حسب_الماده"), bt("زر_حسب_التاريخ"))
    m.add(bt("زر_عوده")); return m

def date_type_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row(bt("زر_يوم"), bt("زر_فتره"))
    m.add(bt("زر_عوده")); return m

def help_audience_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("👤 للمستخدمين","👑 للأدمن"); m.add(bt("زر_عوده")); return m

def help_view_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("👤 تعليمات المستخدم","👑 تعليمات الأدمن"); m.add(bt("زر_عوده")); return m

def lang_menu():
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("🇾🇪 العربية","🇬🇧 English"); return m


# ─────────────────────────────────────────────────────
# Inline multi-select keyboard
# ─────────────────────────────────────────────────────
def build_multiselect_kb(items, selected, prefix):
    keyboard = []; row = []
    for label, value in items:
        lbl = f"✅ {label}" if value in selected else label
        row.append(telebot.types.InlineKeyboardButton(lbl, callback_data=f"{prefix}:{value}"))
        if len(row)==2: keyboard.append(row); row=[]
    all_lbl  = f"✅ {bt('زر_تحديد_الكل')}" if "__all__" in selected else bt("زر_تحديد_الكل")
    done_lbl = bt("زر_تم_التحديد")
    if row:
        row.append(telebot.types.InlineKeyboardButton(all_lbl, callback_data=f"{prefix}:__all__"))
        keyboard.append(row)
        keyboard.append([telebot.types.InlineKeyboardButton(done_lbl, callback_data=f"{prefix}:__done__")])
    else:
        keyboard.append([
            telebot.types.InlineKeyboardButton(all_lbl,  callback_data=f"{prefix}:__all__"),
            telebot.types.InlineKeyboardButton(done_lbl, callback_data=f"{prefix}:__done__"),
        ])
    return telebot.types.InlineKeyboardMarkup(keyboard)

# ─────────────────────────────────────────────────────
# اقتراح التاريخ
# ─────────────────────────────────────────────────────
def send_date_suggestions(chat_id, subject=None, for_lecture=False):
    now = datetime.now(YEMEN_TZ)
    if for_lecture:
        tmrw = now + timedelta(days=1)
        d    = tmrw.strftime("%d/%m/%Y")
        day  = DAYS_AR[tmrw.weekday()]
        bot.send_message(chat_id, f"📅 مقترح (غداً): {day}\n`{d}`", parse_mode="Markdown")
    else:
        today = now.strftime("%d/%m/%Y")
        lines = [f"`{today}`"]
        if subject:
            lects = get_last_lectures_for_subject(subject, 3)
            for d in lects:
                if d != today: lines.append(f"`{d}`")
        lines = lines[:4]
        msg = "📅 اختر تاريخاً أو انسخه:\n\n" + "\n".join(lines)
        bot.send_message(chat_id, msg, parse_mode="Markdown")

# ─────────────────────────────────────────────────────
# عرض نتائج البحث
# ─────────────────────────────────────────────────────
def format_entry(row, col_map, uid):
    lines = []
    for col, icon, lbl in col_map:
        cell = safe_get(row, col)
        text = get_text(cell)
        fids = get_file_ids(cell)
        if text or fids:
            lines.append((icon, text, fids))
    return lines

def send_search_results(chat_id, uid, date_filter, subjects_filter, types_filter, display_mode):
    data = get_data()
    TYPE_COL = {"محاضرات":2,"تكاليف":4,"ملخصات":6}

    if display_mode == "date":
        # تجميع حسب التاريخ
        all_dates = sorted(set(
            parse_date(safe_get(r,0)) for r in data
            if safe_get(r,0) and safe_get(r,1) in subjects_filter
        ), key=lambda x: datetime.strptime(x,"%d/%m/%Y"))

        if isinstance(date_filter, tuple):
            d1, d2 = date_filter
            all_dates = [d for d in all_dates if dates_in_range(d,d1,d2)]
        else:
            all_dates = [d for d in all_dates if d==date_filter]

        found = False
        for d in all_dates:
            rows = [r for r in data if parse_date(safe_get(r,0))==d and safe_get(r,1) in subjects_filter]
            if not rows: continue
            day   = get_day_name(d, uid)
            d_ar  = format_date_ar(d)
            header = f"📅 {d_ar} — {day}\n{'━'*14}"
            bot.send_message(chat_id, header)
            for row in rows:
                subj    = safe_get(row,1)
                subj_hdr= f"\n📌 *{subj}*"
                text_parts = []
                files_all  = []
                if "محاضرات" in types_filter:
                    t = safe_get(row,2)
                    if t: text_parts.append(f"🕐 {t}")
                if "تكاليف" in types_filter:
                    cell = safe_get(row,4)
                    tx = get_text(cell); fids = get_file_ids(cell)
                    if tx: text_parts.append(f"📝 {tx}")
                    files_all.extend(fids)
                if "ملخصات" in types_filter:
                    cell = safe_get(row,6)
                    tx = get_text(cell); fids = get_file_ids(cell)
                    if tx: text_parts.append(f"📖 {tx}")
                    files_all.extend(fids)
                if text_parts or files_all:
                    found = True
                    full_text = subj_hdr + "\n" + "\n".join(text_parts) if text_parts else subj_hdr
                    send_files_with_text(chat_id, full_text, files_all)
        if not found:
            bot.send_message(chat_id, bt("رسالة_لا_بيانات"))

    else:
        # تجميع حسب الماده
        found = False
        for subj in subjects_filter:
            rows = [r for r in data if safe_get(r,1)==subj]
            if isinstance(date_filter, tuple):
                d1, d2 = date_filter
                rows = [r for r in rows if safe_get(r,0) and dates_in_range(parse_date(safe_get(r,0)),d1,d2)]
            else:
                rows = [r for r in rows if safe_get(r,0) and parse_date(safe_get(r,0))==date_filter]
            rows.sort(key=lambda r: datetime.strptime(parse_date(safe_get(r,0)),"%d/%m/%Y") if safe_get(r,0) else datetime.min)
            if not rows: continue
            bot.send_message(chat_id, f"📌 *{subj}*\n{'━'*14}", parse_mode="Markdown")
            for row in rows:
                d    = parse_date(safe_get(row,0))
                day  = get_day_name(d, uid)
                d_ar = format_date_ar(d)
                date_hdr   = f"📅 {d_ar} — {day}"
                text_parts = []
                files_all  = []
                if "محاضرات" in types_filter:
                    t = safe_get(row,2)
                    if t: text_parts.append(f"🕐 {t}")
                if "تكاليف" in types_filter:
                    cell = safe_get(row,4)
                    tx = get_text(cell); fids = get_file_ids(cell)
                    if tx: text_parts.append(f"📝 {tx}")
                    files_all.extend(fids)
                if "ملخصات" in types_filter:
                    cell = safe_get(row,6)
                    tx = get_text(cell); fids = get_file_ids(cell)
                    if tx: text_parts.append(f"📖 {tx}")
                    files_all.extend(fids)
                if text_parts or files_all:
                    found = True
                    full_text = date_hdr + "\n" + "\n".join(text_parts) if text_parts else date_hdr
                    send_files_with_text(chat_id, full_text, files_all)
        if not found:
            bot.send_message(chat_id, bt("رسالة_لا_بيانات"))

# ─────────────────────────────────────────────────────
# بث الإشعارات
# ─────────────────────────────────────────────────────
def _do_broadcast(chat_id, uid, admin, owner, text_msg, files_data):
    uids, open_all = get_all_user_ids()
    if open_all:
        registered = get_all_registered_uids()
        if registered: uids = registered
        if not uids:
            bot.send_message(chat_id, "⚠️ لا يوجد مستخدمون مسجلون بعد."); return
    success = fail = 0
    for user_id in uids:
        try:
            if text_msg:
                bot.send_message(user_id, f"📢 *إشعار:*\n\n{text_msg}", parse_mode="Markdown")
            if files_data:
                for fd in files_data:
                    fid, ftype = fd["file_id"], fd["file_type"]
                    for sender_name, ftype_match in [("send_photo","photo"),("send_video","video"),
                                                     ("send_audio","audio"),("send_voice","voice"),("send_document","document")]:
                        if ftype == ftype_match:
                            getattr(bot, sender_name)(user_id, fid); break
                    else:
                        bot.send_document(user_id, fid)
            success += 1
        except: fail += 1
    bot.send_message(chat_id, f"✅ تم الإرسال!\n✅ {success} | ❌ {fail}",
                     reply_markup=main_menu(uid, admin=admin, owner=owner))

# ─────────────────────────────────────────────────────
# عرض مواد المساعدة
# ─────────────────────────────────────────────────────
def send_help_materials(chat_id, uid, audience_filter):
    mats = [m for m in get_help_materials() if m["audience"]==audience_filter]
    if not mats:
        bot.send_message(chat_id, "📭 لا توجد تعليمات حالياً."); return
    title = "📖 تعليمات المستخدم" if audience_filter=="user" else "📖 تعليمات الأدمن"
    bot.send_message(chat_id, f"*{title}*", parse_mode="Markdown")
    for m in mats:
        fid, ftype, note = m["file_id"], m["file_type"], m["note"]
        send_files_with_text(chat_id, note if note else None, [fid] if fid else [])


# ─────────────────────────────────────────────────────
# Callback handlers
# ─────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda call: call.data.startswith("role_"))
def handle_role(call):
    caller_id = call.from_user.id
    if not is_owner_id(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح"); return
    parts      = call.data.split("_",2)
    new_role   = parts[1]
    target_uid = parts[2]
    try:
        rows = users_sheet.get_all_values(); es = 0
        for i, row in enumerate(rows[1:], start=2):
            if not row or not any(c.strip() for c in row):
                es += 1
                if es >= 5: break
                continue
            es = 0
            cell_id = row[2].strip().lstrip("'") if len(row)>2 else ""
            if cell_id != target_uid: continue
            cur_own   = row[5].strip().upper() if len(row)>5 else "FALSE"
            cur_adm   = row[4].strip().upper() if len(row)>4 else "FALSE"
            cur_allow = row[3].strip().upper() if len(row)>3 else "FALSE"
            if new_role=="owner" and cur_own=="TRUE":
                users_sheet.update(f"D{i}:F{i}",[[True,False,False]]); label="تم إلغاء صلاحية المالك"; new_own=new_adm="FALSE"
            elif new_role=="admin" and cur_adm=="TRUE" and cur_own!="TRUE":
                users_sheet.update(f"D{i}:F{i}",[[True,False,False]]); label="تم إلغاء صلاحية الأدمن"; new_own=new_adm="FALSE"
            elif new_role=="user" and cur_allow=="TRUE" and cur_adm!="TRUE" and cur_own!="TRUE":
                users_sheet.update(f"D{i}:F{i}",[[False,False,False]]); label="⛔ تم إلغاء الصلاحية"
                new_own=new_adm="FALSE"; new_allow="FALSE"
                try: bot.send_message(int(target_uid),"⛔ تم إلغاء صلاحيتك.")
                except: pass
            elif new_role=="owner":
                users_sheet.update(f"D{i}:F{i}",[[True,True,True]]); label="👑 تم تعيين مالك"; new_own=new_adm="TRUE"
                try: bot.send_message(int(target_uid),"👑 تمت ترقيتك إلى مالك!")
                except: pass
            elif new_role=="admin":
                users_sheet.update(f"D{i}:F{i}",[[True,True,False]]); label="⭐ تم تعيين أدمن"; new_own="FALSE"; new_adm="TRUE"
                try: bot.send_message(int(target_uid),"⭐ تمت ترقيتك إلى أدمن!")
                except: pass
            else:
                users_sheet.update(f"D{i}:F{i}",[[True,False,False]]); label="👤 تم تعيين مستخدم"; new_own=new_adm="FALSE"
                try: bot.send_message(int(target_uid), bt("رسالة_موافقة"))
                except: pass
            new_allow = locals().get("new_allow","TRUE")
            try:
                rows2 = users_sheet.get_all_values()
                t_name=t_phone=""
                for row2 in rows2[1:]:
                    if len(row2)>2 and row2[2].strip().lstrip("'")==target_uid:
                        t_name=row2[0].strip(); t_phone=row2[1].strip() if len(row2)>1 else ""; break
                role_icon = "👑" if new_own=="TRUE" else ("⭐" if new_adm=="TRUE" else ("👤" if new_allow=="TRUE" else "❌"))
                ph_line   = f"\n📞 `{t_phone}`" if t_phone else ""
                new_text  = f"{role_icon} *{t_name}*\n🆔 `{target_uid}`{ph_line}\n───────────────────────"
                new_markup = telebot.types.InlineKeyboardMarkup(row_width=3)
                new_markup.row(
                    telebot.types.InlineKeyboardButton("👑 مالك",    callback_data=f"role_owner_{target_uid}"),
                    telebot.types.InlineKeyboardButton("⭐ أدمن",    callback_data=f"role_admin_{target_uid}"),
                    telebot.types.InlineKeyboardButton("👤 مستخدم",  callback_data=f"role_user_{target_uid}"),
                )
                bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id,
                                      parse_mode="Markdown", reply_markup=new_markup)
            except Exception as e2:
                if "message is not modified" not in str(e2): log_error(f"role edit: {e2}")
            bot.answer_callback_query(call.id, label); return
        bot.answer_callback_query(call.id, "❌ المستخدم غير موجود")
    except Exception as e:
        log_error(f"handle_role: {e}"); bot.answer_callback_query(call.id, "❌ خطأ")


@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def handle_approval(call):
    caller_id = call.from_user.id
    if not is_owner_id(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح"); return
    decided_by = f"@{call.from_user.username}" if call.from_user.username else call.from_user.full_name
    if call.data.startswith("approve_"):
        parts = call.data.split("_",2)
        requester_id   = int(parts[1])
        requester_name = parts[2] if len(parts)>2 else "مستخدم"
        try:
            rows = users_sheet.get_all_values(); uid_str=str(requester_id); found=False; es=0
            phone = ""
            for row in rows[1:]:
                if len(row)>2 and row[2].strip().lstrip("'")==uid_str:
                    phone = row[1].strip() if len(row)>1 else ""; break
            for i, row in enumerate(rows[1:], start=2):
                if not row or not any(c.strip() for c in row):
                    es += 1
                    if es >= 5: break
                    continue
                es = 0
                if len(row)>2 and row[2].strip().lstrip("'")==uid_str:
                    users_sheet.update_cell(i,4,True); found=True; break
            if not found: add_user_to_sheet(requester_name, requester_id)
            pending_requests.discard(requester_id)
            try: bot.send_message(requester_id, bt("رسالة_موافقة"))
            except: pass
            notify_owners_decision(requester_id, requester_name, phone, decided_by, True)
        except Exception as e:
            log_error(f"approve: {e}"); bot.answer_callback_query(call.id, "❌ خطأ في الحفظ"); return
    elif call.data.startswith("reject_"):
        requester_id = int(call.data.split("_")[1])
        phone = ""
        try:
            for row in users_sheet.get_all_values()[1:]:
                if len(row)>2 and row[2].strip().lstrip("'")==str(requester_id):
                    phone = row[1].strip() if len(row)>1 else ""; break
            requester_name = ""
            for row in users_sheet.get_all_values()[1:]:
                if len(row)>2 and row[2].strip().lstrip("'")==str(requester_id):
                    requester_name = row[0].strip(); break
        except: phone=""; requester_name=""
        pending_requests.discard(requester_id)
        try: bot.send_message(requester_id, bt("رسالة_رفض_طلب"))
        except: pass
        notify_owners_decision(requester_id, requester_name, phone, decided_by, False)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("ms_subj:") or
                                               call.data.startswith("ms_type:"))
def handle_multiselect(call):
    uid   = call.from_user.id
    state = user_state.get(uid, {})
    parts = call.data.split(":",1)
    prefix, value = parts[0], parts[1]

    if prefix == "ms_subj":
        subjects  = get_subjects()
        sel_key   = "sel_subjects"
        items     = [(s,s) for s in subjects]
        next_step = "choose_type"
        all_vals  = [s for s,_ in items]
    elif prefix == "ms_type":
        sel_key   = "sel_types"
        items     = [("محاضرات","محاضرات"),("تكاليف","تكاليف"),("ملخصات","ملخصات")]
        next_step = "choose_display"
        all_vals  = ["محاضرات","تكاليف","ملخصات"]
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
            bot.answer_callback_query(call.id, "⚠️ اختر واحداً على الأقل"); return
        user_state[uid][sel_key] = real_sel
        bot.answer_callback_query(call.id)
        if next_step == "choose_type":
            user_state[uid]["step"] = "choose_type"
            items2 = [("محاضرات","محاضرات"),("تكاليف","تكاليف"),("ملخصات","ملخصات")]
            kb = build_multiselect_kb(items2, set(), "ms_type")
            bot.send_message(call.message.chat.id, "📋 اختر المطلوب:", reply_markup=kb)
        else:
            user_state[uid]["step"] = "choose_display"
            bot.send_message(call.message.chat.id, "📊 كيف تريد عرض النتائج؟",
                             reply_markup=display_mode_menu(uid))
        return
    else:
        if value in selected: selected.discard(value); selected.discard("__all__")
        else: selected.add(value)
        if set(all_vals) <= selected: selected.add("__all__")
        else: selected.discard("__all__")

    user_state[uid][sel_key] = list(selected)
    kb = build_multiselect_kb(items, selected, prefix)
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb)
    except: pass
    bot.answer_callback_query(call.id)


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
        if not is_pending(uid):
            pending_requests.add(uid)
        bot.send_message(message.chat.id, rejection)
        cm = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        cm.add(telebot.types.KeyboardButton("📱 مشاركة جهة الاتصال", request_contact=True))
        bot.send_message(message.chat.id, "📲 شارك جهة اتصالك لتسهيل التواصل معك:", reply_markup=cm)
        return
    user_state.pop(uid, None)
    admin = admin_all or uid in admins
    owner = uid in owners
    log_info(f"START | uid={uid} | name={message.from_user.full_name} | admin={admin} | owner={owner}")
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin, owner=owner))


@bot.message_handler(commands=['server'])
def server_command(message):
    inline = telebot.types.InlineKeyboardMarkup()
    inline.add(telebot.types.InlineKeyboardButton("🔄 تشغيل البوت", url="https://telegram-bot1-cxnc.onrender.com"))
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
        bot.send_message(message.chat.id, "اختر:", reply_markup=help_view_menu(uid))
    else:
        send_help_materials(message.chat.id, uid, "user")


# ─────────────────────────────────────────────────────
# Contact handler
# ─────────────────────────────────────────────────────
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    uid     = message.from_user.id
    contact = message.contact
    phone   = contact.phone_number if contact else ""
    name    = message.from_user.full_name or "مجهول"
    try:
        rows    = users_sheet.get_all_values()
        uid_str = str(uid); found = False; es = 0
        for i, row in enumerate(rows[1:], start=2):
            if not row or not any(c.strip() for c in row):
                es += 1
                if es >= 5: break
                continue
            es = 0
            if len(row)>2 and row[2].strip().lstrip("'")==uid_str:
                users_sheet.update(f"A{i}:B{i}",[[name,phone]]); found=True; break
        if not found:
            users_sheet.append_row([name,phone,uid,False,False,False,False,False], value_input_option="USER_ENTERED")
    except Exception as e:
        log_error(f"handle_contact save: {e}")
    notify_owners_new_request(uid, name, phone)
    bot.send_message(message.chat.id, "✅ شكراً! تم إرسال معلوماتك.",
                     reply_markup=telebot.types.ReplyKeyboardRemove())


# ─────────────────────────────────────────────────────
# File handler
# ─────────────────────────────────────────────────────
@bot.message_handler(content_types=['document','photo','video','audio','voice'])
def handle_file(message):
    uid = message.from_user.id
    load_user_lang(uid)
    _, rejection = get_settings()
    allowed, admins, owners, open_all, admin_all, _ = get_users()
    is_allowed = open_all or uid in allowed
    if not is_allowed:
        bot.send_message(message.chat.id, rejection); return
    auto_register_user(message, open_all=open_all)
    f_admin = admin_all or uid in admins
    f_owner = uid in owners
    state   = user_state.get(uid, {})

    if message.document: file_id, ftype = message.document.file_id, "document"
    elif message.photo:  file_id, ftype = message.photo[-1].file_id, "photo"
    elif message.video:  file_id, ftype = message.video.file_id, "video"
    elif message.audio:  file_id, ftype = message.audio.file_id, "audio"
    elif message.voice:  file_id, ftype = message.voice.file_id, "voice"
    else: return

    # رفع ملف (تكليف/ملخص) — جمع media group
    if state.get("uploading") and state.get("step") == "waiting_files":
        if not (f_admin or f_owner):
            bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
        pending = user_state[uid].setdefault("pending_files", [])
        pending.append({"file_id": file_id, "file_type": ftype})
        # timer لإنهاء الجمع بعد 3 ثوانٍ
        def _finish_collect():
            st = user_state.get(uid, {})
            if st.get("step") == "waiting_files":
                user_state[uid]["step"] = "confirm_files"
                files = st.get("pending_files", [])
                bot.send_message(message.chat.id,
                    f"📎 تم استلام {len(files)} ملف.\n\nاضغط *إرسال* لحفظها أو أرسل المزيد:",
                    parse_mode="Markdown",
                    reply_markup=_upload_confirm_menu(uid))
        if hasattr(user_state[uid], "_timer") and user_state[uid]["_timer"]:
            user_state[uid]["_timer"].cancel()
        t = threading.Timer(3.0, _finish_collect)
        user_state[uid]["_timer"] = t
        t.start()
        return

    # رفع تعليمات — جمع media group
    if state.get("uploading_help") and state.get("step") == "waiting_file_help":
        if not (f_admin or f_owner):
            bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
        pending = user_state[uid].setdefault("pending_files", [])
        pending.append({"file_id": file_id, "file_type": ftype})
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
        if user_state[uid].get("_timer"): user_state[uid]["_timer"].cancel()
        t = threading.Timer(3.0, _finish_help)
        user_state[uid]["_timer"] = t; t.start()
        return

    # بث الإشعارات
    if state.get("broadcasting") and state.get("step") == "waiting_file_or_send":
        if not (f_admin or f_owner):
            bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
        bfiles = user_state[uid].setdefault("broadcast_files", [])
        bfiles.append({"file_id": file_id, "file_type": ftype})
        return

    if not (f_admin or f_owner):
        bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط"))
        return
    bot.send_message(message.chat.id, "📤 لرفع ملف اضغط *رفع ملف* أولاً.", parse_mode="Markdown")


def _upload_confirm_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row("✅ إرسال", bt("زر_عوده")); return m


# ─────────────────────────────────────────────────────
# helper — user card inline keyboard
# ─────────────────────────────────────────────────────
def user_card_markup(uid_str):
    mk = telebot.types.InlineKeyboardMarkup(row_width=3)
    mk.row(
        telebot.types.InlineKeyboardButton("👑 مالك",   callback_data=f"role_owner_{uid_str}"),
        telebot.types.InlineKeyboardButton("⭐ أدمن",   callback_data=f"role_admin_{uid_str}"),
        telebot.types.InlineKeyboardButton("👤 مستخدم", callback_data=f"role_user_{uid_str}"),
    )
    return mk

def send_user_card(chat_id, row):
    name      = row[0].strip() if row else ""
    uid_str   = row[2].strip().lstrip("'") if len(row)>2 else ""
    phone     = row[1].strip() if len(row)>1 else ""
    own       = row[5].strip().upper() if len(row)>5 else "FALSE"
    adm       = row[4].strip().upper() if len(row)>4 else "FALSE"
    allow_val = row[3].strip().upper() if len(row)>3 else "FALSE"
    icon      = "👑" if own=="TRUE" else ("⭐" if adm=="TRUE" else ("👤" if allow_val=="TRUE" else "❌"))
    ph_line   = f"\n📞 `{phone}`" if phone else ""
    text      = f"{icon} *{name}*\n🆔 `{uid_str}`{ph_line}\n───────────────────────"
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=user_card_markup(uid_str))

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
    text       = message.text or ""
    state      = user_state.get(uid, {})
    back_btn   = bt("زر_عوده")

    # ── اختيار اللغة ──────────────────────────────────
    if state.get("choosing_lang") or text in ["🇾🇪 العربية","🇬🇧 English"]:
        if text=="🇾🇪 العربية":   user_lang[uid]="ar"
        elif text=="🇬🇧 English": user_lang[uid]="en"
        else:
            bot.send_message(message.chat.id,"🌐 اختر اللغة / Choose Language",reply_markup=lang_menu()); return
        user_state.pop(uid,None)
        save_user_lang_to_sheet(uid, user_lang[uid])
        bot.send_message(message.chat.id,"✅ تم تغيير اللغة!",reply_markup=telebot.types.ReplyKeyboardRemove())
        return

    # ── غير مسموح ─────────────────────────────────────
    if not is_allowed:
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
        subjects_kb, subjects_list = subjects_menu_kb(uid)
        data = get_data()

        # ══════════════════════════════════════════
        # زر العودة العام
        # ══════════════════════════════════════════
        if text == back_btn:
            # من داخل البحث بالتاريخ - خطوة اختيار النوع أو العرض
            if state.get("date_search"):
                step = state.get("step","")
                if step == "choose_date_input":
                    user_state.pop(uid,None)
                    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid,admin=admin,owner=owner))
                elif step == "choose_subjects":
                    user_state[uid]["step"] = "choose_date_input"
                    bot.send_message(message.chat.id,"📅 أدخل التاريخ أو الفترة:", reply_markup=back_only_menu(uid))
                elif step == "choose_type":
                    user_state[uid]["step"] = "choose_subjects"
                    subjects = get_subjects()
                    sel = set(state.get("sel_subjects",[]))
                    kb  = build_multiselect_kb([(s,s) for s in subjects], sel, "ms_subj")
                    bot.send_message(message.chat.id,"📚 اختر المواد:", reply_markup=kb)
                elif step == "choose_display":
                    user_state[uid]["step"] = "choose_type"
                    items2 = [("محاضرات","محاضرات"),("تكاليف","تكاليف"),("ملخصات","ملخصات")]
                    sel2   = set(state.get("sel_types",[]))
                    kb2    = build_multiselect_kb(items2, sel2, "ms_type")
                    bot.send_message(message.chat.id,"📋 اختر المطلوب:", reply_markup=kb2)
                else:
                    user_state.pop(uid,None)
                    bot.send_message(message.chat.id,welcome,reply_markup=main_menu(uid,admin=admin,owner=owner))
                return
            # من داخل رفع ملف خطوة اختيار المادة → للقائمة الرئيسية
            if state.get("uploading") and state.get("step") in ("choose_subject","choose_type","choose_date","confirm_files","waiting_files"):
                user_state.pop(uid,None)
                bot.send_message(message.chat.id,welcome,reply_markup=main_menu(uid,admin=admin,owner=owner)); return
            # من إدخال وقت المحاضرة - رجوع لخطوة إدخال الوقت
            if state.get("adding_data") and state.get("step") in ("confirm_lecture_overwrite","enter_time_custom"):
                user_state[uid]["step"] = "enter_time"
                bot.send_message(message.chat.id,"اختر وقت المحاضرة:", reply_markup=lecture_time_menu(uid)); return
            # من إدارة المستخدمين
            if state.get("managing_users"):
                user_state.pop(uid,None)
                bot.send_message(message.chat.id,welcome,reply_markup=main_menu(uid,admin=admin,owner=owner)); return
            # عودة عامة
            user_state.pop(uid,None)
            bot.send_message(message.chat.id,welcome,reply_markup=main_menu(uid,admin=admin,owner=owner))
            return

        # ══════════════════════════════════════════
        # تعليمات (help view)
        # ══════════════════════════════════════════
        if state.get("viewing_help"):
            if text=="👤 تعليمات المستخدم":
                send_help_materials(message.chat.id, uid, "user")
            elif text=="👑 تعليمات الأدمن":
                send_help_materials(message.chat.id, uid, "admin")
            else:
                bot.send_message(message.chat.id,"اختر:", reply_markup=help_view_menu(uid)); return
            user_state.pop(uid,None)
            bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid,admin=admin,owner=owner))
            return

        # ══════════════════════════════════════════
        # 📅 التاريخ (البحث بالتاريخ)
        # ══════════════════════════════════════════
        if text == bt("زر_التاريخ"):
            user_state[uid] = {"date_search":True,"step":"choose_date_type"}
            bot.send_message(message.chat.id,"📅 اختر نوع البحث:", reply_markup=date_type_menu(uid))
            return

        if state.get("date_search"):
            step = state.get("step","")

            if step == "choose_date_type":
                if text == bt("زر_يوم"):
                    user_state[uid]["search_mode"] = "day"
                    user_state[uid]["step"]        = "choose_date_input"
                    bot.send_message(message.chat.id,
                        "📅 أدخل اليوم (مثال: 27) أو التاريخ كاملاً (27/02/2026):",
                        reply_markup=back_only_menu(uid))
                elif text == bt("زر_فتره"):
                    user_state[uid]["search_mode"] = "range"
                    user_state[uid]["step"]        = "choose_date_input"
                    bot.send_message(message.chat.id,
                        "📅 أدخل الفترة بالشكل: 15-27\nأو تاريخين: 01/02/2026-28/02/2026",
                        reply_markup=back_only_menu(uid))
                return

            if step == "choose_date_input":
                mode = state.get("search_mode","day")
                if mode == "day":
                    d = parse_smart_date(text)
                    if not d:
                        bot.send_message(message.chat.id,"❌ صيغة غير صحيحة.\nمثال: 27 أو 27/02/2026"); return
                    user_state[uid]["date_filter"] = d
                else:
                    d1, d2 = parse_date_range(text)
                    if not d1:
                        bot.send_message(message.chat.id,"❌ صيغة غير صحيحة.\nمثال: 15-27"); return
                    user_state[uid]["date_filter"] = (d1, d2)
                user_state[uid]["step"] = "choose_subjects"
                subjects = get_subjects()
                kb = build_multiselect_kb([(s,s) for s in subjects], set(), "ms_subj")
                bot.send_message(message.chat.id,"📚 اختر المواد:", reply_markup=kb)
                return

            if step == "choose_display":
                if text == bt("زر_حسب_الماده"):   display_mode = "subject"
                elif text == bt("زر_حسب_التاريخ"): display_mode = "date"
                else:
                    bot.send_message(message.chat.id,"📊 كيف تريد عرض النتائج؟",
                                     reply_markup=display_mode_menu(uid)); return
                df    = state.get("date_filter")
                subjs = [v for v in state.get("sel_subjects",[]) if v!="__all__"]
                types = [v for v in state.get("sel_types",[])    if v!="__all__"]
                user_state.pop(uid,None)
                send_search_results(message.chat.id, uid, df, subjs, types, display_mode)
                bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid,admin=admin,owner=owner))
            return

        # ══════════════════════════════════════════
        # إدارة المستخدمين
        # ══════════════════════════════════════════
        if text == bt("زر_المستخدمين"):
            if not owner:
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
            user_state[uid] = {"managing_users":True,"step":"menu"}
            rows = users_sheet.get_all_values()
            entries = []; es=0
            for row in rows[1:]:
                if not row or not any(c.strip() for c in row):
                    es += 1
                    if es >= 5: break
                    continue
                es=0
                name    = row[0].strip(); uid_str = row[2].strip().lstrip("'") if len(row)>2 else ""
                own_v   = row[5].strip().upper() if len(row)>5 else "FALSE"
                adm_v   = row[4].strip().upper() if len(row)>4 else "FALSE"
                allow_v = row[3].strip().upper() if len(row)>3 else "FALSE"
                if not name or name=="الكل" or not uid_str: continue
                entries.append((name, uid_str, own_v, adm_v, allow_v, row))
            entries.sort(key=lambda x:(0 if x[2]=="TRUE" else 1 if x[3]=="TRUE" else 2))
            bot.send_message(message.chat.id,"👥 *قائمة المستخدمين:*\n"+("─"*25),
                             parse_mode="Markdown", reply_markup=manage_users_menu(uid))
            for name, uid_str, own_v, adm_v, allow_v, row in entries:
                send_user_card(message.chat.id, row)
            return

        if state.get("managing_users"):
            step = state.get("step","menu")
            if step == "menu":
                if text == "🔍 بحث بالID":
                    user_state[uid]["step"] = "search_id"
                    bot.send_message(message.chat.id,"🔍 أدخل الـ ID:", reply_markup=back_only_menu(uid))
                elif text == "🔍 بحث بالرقم":
                    user_state[uid]["step"] = "search_phone"
                    bot.send_message(message.chat.id,"🔍 أدخل رقم الهاتف:", reply_markup=back_only_menu(uid))
                return
            if step == "search_id":
                _, row = find_user_row_by_id(text.strip())
                if row: send_user_card(message.chat.id, row)
                else: bot.send_message(message.chat.id,"❌ لم يتم العثور على مستخدم")
                user_state[uid]["step"] = "menu"
                bot.send_message(message.chat.id,"↩️", reply_markup=manage_users_menu(uid))
                return
            if step == "search_phone":
                _, row = find_user_row_by_phone(text.strip())
                if row: send_user_card(message.chat.id, row)
                else: bot.send_message(message.chat.id,"❌ لم يتم العثور على مستخدم")
                user_state[uid]["step"] = "menu"
                bot.send_message(message.chat.id,"↩️", reply_markup=manage_users_menu(uid))
                return
            return

        # ══════════════════════════════════════════
        # بث الإشعارات
        # ══════════════════════════════════════════
        if text == bt("زر_اشعار"):
            if not (admin or owner):
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
            user_state[uid] = {"broadcasting":True,"step":"waiting_text"}
            m = telebot.types.ReplyKeyboardMarkup(row_width=1,resize_keyboard=True)
            m.add("📤 إرسال بدون نص", back_btn)
            bot.send_message(message.chat.id,"اكتب نص الإشعار أو اضغط إرسال بدون نص:", reply_markup=m)
            return

        if state.get("broadcasting"):
            step = state.get("step","")
            if step == "waiting_text":
                if text=="📤 إرسال بدون نص": user_state[uid]["broadcast_text"]=""
                else: user_state[uid]["broadcast_text"]=text
                user_state[uid]["step"]="waiting_file_or_send"
                m2 = telebot.types.ReplyKeyboardMarkup(row_width=1,resize_keyboard=True)
                m2.add("📤 إرسال الآن", back_btn)
                bot.send_message(message.chat.id,"أرسل ملفاً (اختياري) أو اضغط إرسال الآن:", reply_markup=m2)
                return
            if step == "waiting_file_or_send":
                if text=="📤 إرسال الآن":
                    _do_broadcast(message.chat.id, uid, admin, owner,
                                  state.get("broadcast_text",""), state.get("broadcast_files",[]))
                    user_state.pop(uid,None)
                return

        # ══════════════════════════════════════════
        # رفع التعليمات
        # ══════════════════════════════════════════
        if text == bt("زر_رفع_تعليمات"):
            if not (admin or owner):
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
            user_state[uid] = {"uploading_help":True,"step":"choose_audience"}
            bot.send_message(message.chat.id,"👥 هذه التعليمات لمن؟", reply_markup=help_audience_menu(uid))
            return

        if state.get("uploading_help"):
            step = state.get("step","")
            if step == "choose_audience":
                if text=="👤 للمستخدمين":   user_state[uid]["audience"]="user"
                elif text=="👑 للأدمن":    user_state[uid]["audience"]="admin"
                else: return
                user_state[uid]["step"]="enter_note"
                bot.send_message(message.chat.id,
                    "📝 أدخل نصاً توضيحياً (اختياري) أو اضغط تخطي:",
                    reply_markup=back_skip_menu(uid))
                return
            if step == "enter_note":
                if text=="⏭️ تخطي": user_state[uid]["note"]=""
                else: user_state[uid]["note"]=text
                user_state[uid]["step"]="waiting_file_help"
                bot.send_message(message.chat.id,
                    "📎 أرسل الملف أو الملفات (أو اضغط تخطي إذا تريد نص فقط):",
                    reply_markup=back_skip_menu(uid))
                return
            if step == "waiting_file_help":
                if text=="⏭️ تخطي":
                    note = state.get("note","")
                    if not note:
                        bot.send_message(message.chat.id,"⚠️ لازم ترسل نص أو ملف على الأقل."); return
                    if save_help_material([], state.get("audience","user"), note):
                        bot.send_message(message.chat.id,"✅ تم الحفظ!", reply_markup=main_menu(uid,admin=admin,owner=owner))
                    else:
                        bot.send_message(message.chat.id, bt("رسالة_خطأ"))
                    user_state.pop(uid,None)
                return

        # ══════════════════════════════════════════
        # رفع ملف (تكليف/ملخص)
        # ══════════════════════════════════════════
        if text == bt("زر_رفع_ملف"):
            if not (admin or owner):
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
            user_state[uid] = {"uploading":True,"step":"choose_subject"}
            bot.send_message(message.chat.id,"📌 اختر المادة:", reply_markup=subjects_kb)
            return

        if state.get("uploading"):
            step = state.get("step","")
            if step=="choose_subject" and text in subjects_list:
                user_state[uid]["subject"]=text
                user_state[uid]["step"]="choose_type"
                bot.send_message(message.chat.id,f"📌 *{text}*\nاختر النوع:",
                                 parse_mode="Markdown", reply_markup=file_type_menu(uid))
                return
            if step=="choose_type":
                if text==bt("زر_اضافة_تكليف"):   user_state[uid]["col"]=4
                elif text==bt("زر_اضافة_ملخص"):  user_state[uid]["col"]=6
                else: return
                user_state[uid]["step"]="choose_date"
                subj = state.get("subject","")
                bot.send_message(message.chat.id,"📅 أدخل التاريخ:", reply_markup=back_only_menu(uid))
                send_date_suggestions(message.chat.id, subject=subj, for_lecture=False)
                return
            if step=="choose_date":
                d = parse_smart_date(text)
                if not d:
                    bot.send_message(message.chat.id,"❌ صيغة غير صحيحة. مثال: `27/02/2026`",parse_mode="Markdown")
                    send_date_suggestions(message.chat.id, subject=state.get("subject",""), for_lecture=False); return
                user_state[uid]["date"]=d
                col  = state.get("col",4)
                subj = state.get("subject","")
                # فحص تعارض
                existing_rows = [r for r in data if safe_get(r,1)==subj and parse_date(safe_get(r,0))==d]
                has_existing  = existing_rows and get_file_ids(safe_get(existing_rows[0],col))
                if has_existing:
                    user_state[uid]["step"]="confirm_file_conflict"
                    mk = telebot.types.ReplyKeyboardMarkup(row_width=3,resize_keyboard=True)
                    mk.row("🔗 دمج","🔄 استبدال", back_btn)
                    bot.send_message(message.chat.id,"⚠️ يوجد ملفات مسبقة لهذه المادة والتاريخ!\n\nماذا تريد؟",
                                     reply_markup=mk)
                else:
                    user_state[uid]["step"]="waiting_files"
                    user_state[uid]["pending_files"]=[]
                    bot.send_message(message.chat.id,"📎 أرسل الملفات:", reply_markup=back_only_menu(uid))
                return
            if step=="confirm_file_conflict":
                if text=="🔗 دمج":
                    user_state[uid]["file_merge"]=True
                    user_state[uid]["step"]="waiting_files"
                    user_state[uid]["pending_files"]=[]
                    bot.send_message(message.chat.id,"📎 أرسل الملفات:", reply_markup=back_only_menu(uid))
                elif text=="🔄 استبدال":
                    user_state[uid]["file_merge"]=False
                    user_state[uid]["step"]="waiting_files"
                    user_state[uid]["pending_files"]=[]
                    bot.send_message(message.chat.id,"📎 أرسل الملفات:", reply_markup=back_only_menu(uid))
                return
            if step=="confirm_files":
                if text=="✅ إرسال":
                    files  = state.get("pending_files",[])
                    col    = state.get("col",4)
                    subj   = state.get("subject","")
                    date   = state.get("date","")
                    fids   = [f["file_id"] for f in files]
                    merge  = state.get("file_merge", False)
                    if save_file_to_cell(date, subj, col, fids, merge=merge):
                        bot.send_message(message.chat.id, bt("رسالة_تم_الحفظ"),
                                         reply_markup=main_menu(uid,admin=admin,owner=owner))
                    else:
                        bot.send_message(message.chat.id, bt("رسالة_خطأ"))
                    user_state.pop(uid,None)
                return
            return

        # ══════════════════════════════════════════
        # إضافة بيانات
        # ══════════════════════════════════════════
        if text == bt("زر_اضافة"):
            if not (admin or owner):
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
            user_state[uid] = {"adding_data":True,"step":"choose_type"}
            bot.send_message(message.chat.id,"اختر نوع البيانات:", reply_markup=add_data_menu(uid))
            return

        if state.get("adding_data"):
            step = state.get("step","")
            ADD_MAP = {
                bt("زر_اضافة_محاضره"):"lecture",
                bt("زر_اضافة_تكليف"): "task",
                bt("زر_اضافة_ملخص"):  "summary",
                bt("زر_اضافة_سعر"):   "price",
                bt("زر_اضافة_تنبيه"): "alert",
            }

            if step=="choose_type" and text in ADD_MAP:
                dtype = ADD_MAP[text]
                user_state[uid]["data_type"] = dtype
                if dtype=="lecture":
                    user_state[uid]["step"]="enter_date"
                    bot.send_message(message.chat.id,"📅 أدخل تاريخ المحاضرة:", reply_markup=back_only_menu(uid))
                    send_date_suggestions(message.chat.id, for_lecture=True)
                elif dtype in ("task","summary","alert"):
                    user_state[uid]["step"]="choose_subject"
                    bot.send_message(message.chat.id,"📌 اختر المادة:", reply_markup=subjects_kb)
                elif dtype=="price":
                    user_state[uid]["step"]="choose_subject"
                    bot.send_message(message.chat.id,"📌 اختر المادة:", reply_markup=subjects_kb)
                return

            if step=="choose_subject" and text in subjects_list:
                user_state[uid]["subject"]=text
                dtype = state.get("data_type","")
                if dtype=="lecture":
                    user_state[uid]["step"]="choose_building"
                    bot.send_message(message.chat.id,"🏛 اختر المبنى:", reply_markup=buildings_menu(uid))
                elif dtype=="price":
                    user_state[uid]["step"]="enter_value"
                    bot.send_message(message.chat.id,"💰 أدخل سعر الملزمة:", reply_markup=back_with_noexist(uid))
                else:
                    user_state[uid]["step"]="enter_date"
                    bot.send_message(message.chat.id,"📅 أدخل التاريخ:", reply_markup=back_only_menu(uid))
                    send_date_suggestions(message.chat.id, subject=text, for_lecture=False)
                return

            if step=="enter_date":
                d = parse_smart_date(text)
                if not d:
                    bot.send_message(message.chat.id,"❌ صيغة غير صحيحة. مثال: `27/02/2026`",parse_mode="Markdown")
                    send_date_suggestions(message.chat.id, for_lecture=state.get("data_type")=="lecture"); return
                user_state[uid]["date"]=d
                dtype = state.get("data_type","")
                if dtype=="lecture":
                    user_state[uid]["step"]="choose_building"
                    bot.send_message(message.chat.id,"🏛 اختر المبنى:", reply_markup=buildings_menu(uid))
                elif dtype in ("task","summary"):
                    user_state[uid]["step"]="enter_value"
                    col_lbl = "التكليف" if dtype=="task" else "الملخص"
                    bot.send_message(message.chat.id,f"📝 أدخل نص {col_lbl}:", reply_markup=back_with_noexist(uid))
                elif dtype=="alert":
                    user_state[uid]["step"]="enter_value"
                    bot.send_message(message.chat.id,"⚠️ أدخل نص التنبيه:", reply_markup=back_with_noexist(uid))
                return

            if step=="choose_building":
                bmap = {"🏛 القديم":"القديم","🏫 الاداب":"الاداب"}
                if text in bmap:
                    user_state[uid]["building"]       = bmap[text]
                    user_state[uid]["building_label"] = text
                    mk, rooms = rooms_menu_kb(uid, bmap[text])
                    if not rooms:
                        bot.send_message(message.chat.id,"⚠️ لا توجد قاعات."); return
                    user_state[uid]["step"]="choose_room"
                    bot.send_message(message.chat.id,"🚪 اختر القاعة:", reply_markup=mk)
                return

            if step=="choose_room":
                user_state[uid]["room"] = f"{state.get('building_label','')}: {text}"
                user_state[uid]["step"] = "choose_subject"
                bot.send_message(message.chat.id,"📌 اختر المادة:", reply_markup=subjects_kb)
                return

            if step=="enter_time":
                TIME_MAP = {
                    "🕐 08:00 - 10:00":"08:00 - 10:00",
                    "🕐 10:00 - 12:00":"10:00 - 12:00",
                    "🕐 12:00 - 14:00":"12:00 - 14:00",
                }
                if text in TIME_MAP:
                    time_val = TIME_MAP[text]
                elif text=="⏰ توقيت آخر":
                    user_state[uid]["step"]="enter_time_custom"
                    bot.send_message(message.chat.id,"أدخل الوقت:\n`08:00 - 09:30`",
                                     parse_mode="Markdown", reply_markup=back_with_noexist(uid)); return
                elif text=="لا يوجد":
                    time_val="لا يوجد"
                else:
                    time_val=normalize_time(text)
                _process_lecture_time(message.chat.id, uid, state, time_val, admin, owner)
                return

            if step=="enter_time_custom":
                time_val = "لا يوجد" if text=="لا يوجد" else normalize_time(text)
                _process_lecture_time(message.chat.id, uid, state, time_val, admin, owner)
                return

            if step=="confirm_lecture_overwrite":
                subj=state.get("subject",""); date=state.get("date","")
                room=state.get("room","");    time_val=state.get("time_val","")
                if text=="🔄 استبدال":
                    if save_lecture(date,subj,time_val,room):
                        mk2=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
                        mk2.add("➕ إضافة محاضرة أخرى",back_btn)
                        user_state[uid]["step"]="lecture_done"
                        bot.send_message(message.chat.id,f"✅ تم استبدال المحاضرة!\n📌 {subj}\n📅 {date}\n🕐 {time_val}\n📍 {room}",
                                         reply_markup=mk2)
                    else:
                        bot.send_message(message.chat.id, bt("رسالة_خطأ")); user_state.pop(uid,None)
                return

            if step=="lecture_done":
                if text=="➕ إضافة محاضرة أخرى":
                    user_state[uid]={"adding_data":True,"step":"choose_subject","data_type":"lecture",
                                     "date":state.get("date",""),"room":state.get("room",""),
                                     "building":state.get("building",""),"building_label":state.get("building_label","")}
                    bot.send_message(message.chat.id,"📌 اختر المادة:", reply_markup=subjects_kb)
                return

            if step=="enter_value":
                dtype=state.get("data_type",""); subj=state.get("subject",""); date=state.get("date","")
                val=text
                if dtype=="price":
                    rows_s=sheet.get_all_values(); updated=False
                    for i,row in enumerate(rows_s[1:],start=2):
                        if safe_get(row,1)==subj:
                            sheet.update_cell(i,6,val); updated=True; break
                    if not updated:
                        sheet.append_row(["",subj,"","","",val,"",""], value_input_option="USER_ENTERED")
                    bot.send_message(message.chat.id,bt("رسالة_تم_الحفظ"),reply_markup=main_menu(uid,admin=admin,owner=owner))
                else:
                    col_map2={"task":4,"summary":6,"alert":7}
                    col=col_map2.get(dtype,4)
                    matched=[r for r in data if safe_get(r,1)==subj and parse_date(safe_get(r,0))==date]
                    existing=get_text(safe_get(matched[0],col)) if matched else ""
                    if existing and existing.strip():
                        user_state[uid]["step"]="confirm_overwrite"
                        user_state[uid]["existing_val"]=existing
                        user_state[uid]["pending_val"]=val
                        mk3=telebot.types.ReplyKeyboardMarkup(row_width=2,resize_keyboard=True)
                        mk3.add("✏️ بجانبه","🔄 بدله"); mk3.add(back_btn)
                        bot.send_message(message.chat.id,f"⚠️ يوجد مدخل سابق:\n`{existing}`\n\nماذا تريد؟",
                                         parse_mode="Markdown", reply_markup=mk3); return
                    ok=save_text_to_cell(date,subj,col,val)
                    bot.send_message(message.chat.id,bt("رسالة_تم_الحفظ") if ok else bt("رسالة_خطأ"),
                                     reply_markup=main_menu(uid,admin=admin,owner=owner))
                user_state.pop(uid,None)
                return

            if step=="confirm_overwrite":
                dtype=state.get("data_type",""); subj=state.get("subject",""); date=state.get("date","")
                col={"task":4,"summary":6,"alert":7}.get(dtype,4)
                existing=state.get("existing_val",""); pending=state.get("pending_val","")
                if text=="✏️ بجانبه":   final=existing+" | "+pending
                elif text=="🔄 بدله":   final=pending
                else:
                    bot.send_message(message.chat.id,welcome,reply_markup=main_menu(uid,admin=admin,owner=owner))
                    user_state.pop(uid,None); return
                ok=save_text_to_cell(date,subj,col,final)
                bot.send_message(message.chat.id,bt("رسالة_تم_الحفظ") if ok else bt("رسالة_خطأ"),
                                 reply_markup=main_menu(uid,admin=admin,owner=owner))
                user_state.pop(uid,None)
                return
            return

        # ══════════════════════════════════════════
        # تعديل/حذف بيانات
        # ══════════════════════════════════════════
        if text == bt("زر_تعديل"):
            if not (admin or owner):
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط")); return
            user_state[uid]={"editing_data":True,"step":"choose_type"}
            bot.send_message(message.chat.id,"اختر نوع البيانات:", reply_markup=edit_data_menu(uid))
            return

        if state.get("editing_data"):
            step=state.get("step","")
            EDIT_MAP={
                bt("زر_تعديل_محاضره"):"lecture",
                bt("زر_تعديل_تكليف"): "task",
                bt("زر_تعديل_ملخص"):  "summary",
                bt("زر_تعديل_سعر"):   "price",
                bt("زر_تعديل_تنبيه"): "alert",
            }
            COL_MAP={"lecture":2,"task":4,"summary":6,"price":5,"alert":7}

            if step=="choose_type" and text in EDIT_MAP:
                user_state[uid]["data_type"]=EDIT_MAP[text]
                user_state[uid]["step"]="choose_subject"
                bot.send_message(message.chat.id,"📌 اختر المادة:", reply_markup=subjects_kb); return

            if step=="choose_subject" and text in subjects_list:
                user_state[uid]["subject"]=text
                dtype=state.get("data_type","")
                col=COL_MAP.get(dtype,2)
                if dtype=="price":
                    matched=[r for r in data if safe_get(r,1)==text]
                    current=next((get_text(safe_get(r,5)) for r in matched if safe_get(r,5)),"")
                    user_state[uid]["step"]="choose_action"; user_state[uid]["current_val"]=current; user_state[uid]["date"]=""
                    bot.send_message(message.chat.id,f"القيمة الحالية: *{current or 'فارغ'}*",
                                     parse_mode="Markdown", reply_markup=edit_action_menu(uid))
                else:
                    matched=[r for r in data if safe_get(r,1)==text]
                    dates=list(dict.fromkeys(parse_date(safe_get(r,0)) for r in matched
                                            if (get_text(safe_get(r,col)) or get_file_ids(safe_get(r,col))) and safe_get(r,0)))
                    if not dates:
                        bot.send_message(message.chat.id,bt("رسالة_لا_بيانات"),reply_markup=edit_data_menu(uid))
                        user_state[uid]={"editing_data":True,"step":"choose_type"}; return
                    user_state[uid]["step"]="choose_date_edit"; user_state[uid]["col"]=col
                    bot.send_message(message.chat.id,"📅 اختر التاريخ:", reply_markup=dates_menu_kb(uid,dates))
                return

            if step=="choose_date_edit":
                subj=state.get("subject",""); col=state.get("col",2)
                matched=[r for r in data if safe_get(r,1)==subj and parse_date(safe_get(r,0))==text]
                if not matched:
                    bot.send_message(message.chat.id,bt("رسالة_لا_بيانات")); return
                current=get_text(safe_get(matched[0],col))
                user_state[uid]["date"]=text; user_state[uid]["current_val"]=current; user_state[uid]["step"]="choose_action"
                bot.send_message(message.chat.id,f"القيمة الحالية: *{current or 'فارغ'}*",
                                 parse_mode="Markdown", reply_markup=edit_action_menu(uid)); return

            if step=="choose_action":
                if text==bt("زر_تعديل_زرار"):
                    user_state[uid]["step"]="enter_new_val"
                    bot.send_message(message.chat.id,"أدخل القيمة الجديدة:", reply_markup=back_only_menu(uid))
                elif text==bt("زر_حذف_زرار"):
                    user_state[uid]["step"]="confirm_delete"
                    cur=state.get("current_val","")
                    mk4=telebot.types.ReplyKeyboardMarkup(row_width=2,resize_keyboard=True)
                    mk4.add("✅ نعم، احذف","❌ إلغاء")
                    bot.send_message(message.chat.id,f"⚠️ هل أنت متأكد من حذف:\n*{cur}*؟",
                                     parse_mode="Markdown", reply_markup=mk4)
                return

            if step=="confirm_delete":
                if text=="✅ نعم، احذف":
                    dtype=state.get("data_type",""); subj=state.get("subject",""); date=state.get("date","")
                    col=COL_MAP.get(dtype,2)
                    if dtype=="price":
                        rows_s=sheet.get_all_values()
                        for i,row in enumerate(rows_s[1:],start=2):
                            if safe_get(row,1)==subj: sheet.update_cell(i,6,""); break
                        bot.send_message(message.chat.id,bt("رسالة_تم_الحذف"),reply_markup=main_menu(uid,admin=admin,owner=owner))
                    else:
                        ok=delete_cell(date,subj,col)
                        bot.send_message(message.chat.id,bt("رسالة_تم_الحذف") if ok else bt("رسالة_خطأ"),
                                         reply_markup=main_menu(uid,admin=admin,owner=owner))
                    user_state.pop(uid,None)
                elif text=="❌ إلغاء":
                    user_state[uid]["step"]="choose_action"
                    bot.send_message(message.chat.id,"تم الإلغاء.", reply_markup=edit_action_menu(uid))
                return

            if step=="enter_new_val":
                dtype=state.get("data_type",""); subj=state.get("subject",""); date=state.get("date","")
                col=COL_MAP.get(dtype,2)
                if dtype=="price":
                    rows_s=sheet.get_all_values()
                    for i,row in enumerate(rows_s[1:],start=2):
                        if safe_get(row,1)==subj: sheet.update_cell(i,6,text); break
                    bot.send_message(message.chat.id,bt("رسالة_تم_التعديل"),reply_markup=main_menu(uid,admin=admin,owner=owner))
                else:
                    ok=save_text_to_cell(date,subj,col,text)
                    bot.send_message(message.chat.id,bt("رسالة_تم_التعديل") if ok else bt("رسالة_خطأ"),
                                     reply_markup=main_menu(uid,admin=admin,owner=owner))
                user_state.pop(uid,None)
                return
            return

        # ══════════════════════════════════════════
        # 📚 المواد
        # ══════════════════════════════════════════
        if text == bt("زر_المواد"):
            user_state.pop(uid,None)
            bot.send_message(message.chat.id,"📌 اختر المادة:", reply_markup=subjects_kb); return

        if text in subjects_list:
            user_state[uid]={"subject":text}
            bot.send_message(message.chat.id,f"📌 *{text}*\nماذا تحتاج؟",
                             parse_mode="Markdown", reply_markup=subject_options_menu(uid)); return

        SUBJ_OPTS=[bt(k) for k in ["خيار_الجدول","خيار_التكاليف","خيار_السعر","خيار_الملخص","خيار_التنبيهات"]]
        if state.get("subject") and text in SUBJ_OPTS:
            subj=state["subject"]
            rows_s=[r for r in data if safe_get(r,1)==subj]
            if text==bt("خيار_السعر"):
                price=next((get_text(safe_get(r,5)) for r in rows_s if safe_get(r,5)),None)
                msg2=f"💰 *{subj}*: {price}" if price else f"لا يوجد سعر لـ *{subj}*"
                bot.send_message(message.chat.id,msg2,parse_mode="Markdown",reply_markup=subject_options_menu(uid)); return
            col_map3={bt("خيار_الجدول"):2,bt("خيار_التكاليف"):4,bt("خيار_الملخص"):6,bt("خيار_التنبيهات"):7}
            col=col_map3[text]
            dates=list(dict.fromkeys(parse_date(safe_get(r,0)) for r in rows_s
                                     if (get_text(safe_get(r,col)) or get_file_ids(safe_get(r,col))) and safe_get(r,0)))
            if not dates:
                no_map={bt("خيار_الجدول"):"لا توجد محاضرات",bt("خيار_التكاليف"):"لا توجد تكاليف",
                        bt("خيار_الملخص"):"لا توجد ملخصات",bt("خيار_التنبيهات"):"لا توجد تنبيهات"}
                bot.send_message(message.chat.id,f"{no_map.get(text,'لا توجد بيانات')} لـ *{subj}*",
                                 parse_mode="Markdown", reply_markup=subject_options_menu(uid)); return
            user_state[uid]={"subject":subj,"action":text,"awaiting_date":True,"col":col,"dates":dates}
            bot.send_message(message.chat.id,"📅 اختر التاريخ:", reply_markup=dates_menu_kb(uid,dates)); return

        if state.get("awaiting_date"):
            subj=state["subject"]; col=state["col"]; dates=state.get("dates",[])
            matched=[r for r in data if safe_get(r,1)==subj and parse_date(safe_get(r,0))==text]
            if not matched:
                bot.send_message(message.chat.id,bt("رسالة_لا_بيانات"),reply_markup=dates_menu_kb(uid,dates)); return
            day=get_day_name(text,uid); d_ar=format_date_ar(text)
            day_str=f" ({day})" if day else ""
            header=f"*{subj}* — {d_ar}{day_str}\n{'─'*25}\n"
            all_text=header; all_fids=[]
            for row in matched:
                cell=safe_get(row,col); val=get_text(cell); fids=get_file_ids(cell)
                col_icon={2:"🕐",4:"📝",6:"📖",7:"⚠️"}.get(col,"")
                if val: all_text+=f"{col_icon} {val}\n"
                all_fids.extend(fids)
            send_files_with_text(message.chat.id, all_text, all_fids,
                                  reply_markup=dates_menu_kb(uid,dates)); return

        # ══════════════════════════════════════════
        # زرارات القائمة الرئيسية المباشرة
        # ══════════════════════════════════════════
        if text == bt("زر_التكاليف"):
            ld=get_last_date(data,4)
            if not ld:
                bot.send_message(message.chat.id,"📭 لا توجد تكاليف.",reply_markup=main_menu(uid,admin=admin,owner=owner)); return
            rows_s=[r for r in data if parse_date(safe_get(r,0))==ld and (get_text(safe_get(r,4)) or get_file_ids(safe_get(r,4)))]
            day=get_day_name(ld,uid); d_ar=format_date_ar(ld)
            header=f"📝 *{d_ar} — {day}*\n{'─'*25}\n"
            all_fids=[]
            for row in rows_s:
                cell=safe_get(row,4); tx=get_text(cell); fids=get_file_ids(cell)
                subj_n=safe_get(row,1)
                if tx: header+=f"📌 {subj_n}: {tx}\n"
                elif fids: header+=f"📌 {subj_n}: 📎 ملف\n"
                all_fids.extend(fids)
            send_files_with_text(message.chat.id, header, all_fids,
                                  reply_markup=main_menu(uid,admin=admin,owner=owner)); return

        if text == bt("زر_الجدول"):
            ld=get_last_date(data,2)
            if not ld:
                bot.send_message(message.chat.id,"📭 لا توجد محاضرات.",reply_markup=main_menu(uid,admin=admin,owner=owner)); return
            rows_s=[r for r in data if parse_date(safe_get(r,0))==ld and get_text(safe_get(r,2))]
            day=get_day_name(ld,uid); d_ar=format_date_ar(ld)
            response=f"🕐 *{d_ar} — {day}:*\n{'─'*25}\n"
            for r in rows_s: response+=f"📌 {safe_get(r,1)}: {get_text(safe_get(r,2))}\n"
            bot.send_message(message.chat.id,response,parse_mode="Markdown",reply_markup=main_menu(uid,admin=admin,owner=owner)); return

        if text == bt("زر_الاسعار"):
            seen={}
            for r in data:
                s=safe_get(r,1); p=get_text(safe_get(r,5))
                if s and p and s not in seen: seen[s]=p
            if not seen:
                bot.send_message(message.chat.id,"📭 لا توجد أسعار.",reply_markup=main_menu(uid,admin=admin,owner=owner)); return
            mx=max(len(s) for s in seen.keys())
            lines="".join(f"📖 {s:<{mx}} : {p}\n" for s,p in seen.items())
            bot.send_message(message.chat.id,f"💰 *أسعار الملازم:*\n```\n{lines}```",
                             parse_mode="Markdown",reply_markup=main_menu(uid,admin=admin,owner=owner)); return

        if text == bt("زر_التنبيهات"):
            alerts=[(safe_get(r,1),parse_date(safe_get(r,0)),get_text(safe_get(r,7))) for r in data if get_text(safe_get(r,7))]
            if not alerts:
                bot.send_message(message.chat.id,"✅ لا توجد تنبيهات.",reply_markup=main_menu(uid,admin=admin,owner=owner)); return
            response="*⚠️ التنبيهات:*\n"+"─"*25+"\n"
            for s,d,a in alerts:
                d_ar=format_date_ar(d); response+=f"🔔 {s} ({d_ar}):\n{a}\n\n"
            bot.send_message(message.chat.id,response,parse_mode="Markdown",reply_markup=main_menu(uid,admin=admin,owner=owner)); return

        bot.send_message(message.chat.id,"❓ اختر من القائمة.", reply_markup=main_menu(uid,admin=admin,owner=owner))

    except Exception as e:
        bot.send_message(message.chat.id, bt("رسالة_خطأ"))
        log_error(f"handle_message uid={uid}: {e}")


# ─────────────────────────────────────────────────────
# helper — معالجة وقت المحاضرة (مشترك بين enter_time و enter_time_custom)
# ─────────────────────────────────────────────────────
def _process_lecture_time(chat_id, uid, state, time_val, admin, owner):
    subj=state.get("subject",""); date=state.get("date",""); room=state.get("room","")
    if time_val=="لا يوجد":
        if save_lecture(date,subj,time_val,room):
            mk=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            mk.add("➕ إضافة محاضرة أخرى", bt("زر_عوده"))
            user_state[uid]["step"]="lecture_done"
            bot.send_message(chat_id,f"✅ تم الحفظ!\n📌 {subj}\n📅 {date}\n📍 {room}",reply_markup=mk)
        else:
            bot.send_message(chat_id, bt("رسالة_خطأ")); user_state.pop(uid,None)
        return
    conflict=check_lecture_conflict(date,time_val)
    if conflict:
        user_state[uid]["step"]="confirm_lecture_overwrite"
        user_state[uid]["time_val"]=time_val
        mk2=telebot.types.ReplyKeyboardMarkup(row_width=2,resize_keyboard=True)
        mk2.row("🔄 استبدال", bt("زر_عوده"))
        bot.send_message(chat_id,
            f"⚠️ تداخل في الوقت!\n\n📌 {conflict['subject']}\n🕐 {conflict['time']}\n📍 {conflict['room']}\n\nالوقت `{time_val}` يتداخل معها.\nماذا تريد؟",
            parse_mode="Markdown", reply_markup=mk2)
    else:
        if save_lecture(date,subj,time_val,room):
            mk3=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            mk3.add("➕ إضافة محاضرة أخرى", bt("زر_عوده"))
            user_state[uid]["step"]="lecture_done"
            user_state[uid]["time_val"]=time_val
            bot.send_message(chat_id,f"✅ تم حفظ المحاضرة!\n📌 {subj}\n📅 {date}\n🕐 {time_val}\n📍 {room}",reply_markup=mk3)
        else:
            bot.send_message(chat_id, bt("رسالة_خطأ")); user_state.pop(uid,None)


# ─────────────────────────────────────────────────────
# run
# ─────────────────────────────────────────────────────
def run():
    load_bot_texts()
    log_info("بوت الدراسة يعمل...")
    bot.infinity_polling()
