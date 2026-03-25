# ====================================================
# study_bot.py — النسخة النهائية الكاملة
# جميع الميزات المطلوبة مع الأوامر الإدارية عبر AI
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

YEMEN_TZ = pytz.timezone('Asia/Aden')
LOG_BOT_TOKEN = os.environ.get("STUDY_BOT_LOG_TOKEN", "")
STUDY_BOT_TOKEN = os.environ.get("STUDY_BOT_TOKEN", "")
SHEET_KEY = os.environ.get("SHEET_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-8s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("StudyBot")

bot = telebot.TeleBot(STUDY_BOT_TOKEN)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    gcreds = os.environ.get("GOOGLE_CREDENTIALS")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(gcreds), scope) if gcreds else \
        ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_KEY)
    sheet = spreadsheet.sheet1
    users_sheet = spreadsheet.worksheet("المستخدمين")
    help_sheet = spreadsheet.worksheet("المساعدة")
    bot_texts_sheet = spreadsheet.worksheet("bot_texts")
    try:
        rooms_sheet = spreadsheet.worksheet("القاعات")
    except:
        rooms_sheet = None
except Exception as _e:
    logger.critical(f"خطأ Google Sheets: {_e}")
    sheet = users_sheet = help_sheet = bot_texts_sheet = rooms_sheet = None

# ─────────────────────────────────────────────────────
# BOT_TEXTS (دعم اللغتين)
# ─────────────────────────────────────────────────────
DEFAULT_BOT_TEXTS = {
    "رسالة_الترحيب_ar": "مرحبًا! اختر أحد الخيارات:",
    "رسالة_الترحيب_en": "Welcome! Choose an option:",
    "رسالة_الرفض_ar": "⛔ غير مسموح لك باستخدام البوت\n\nالرجاء طلب الصلاحية من منشئ البوت @nt18s",
    "رسالة_الرفض_en": "⛔ You are not allowed to use this bot\n\nPlease request permission from the bot owner @nt18s",
    "رسالة_انتظار_ar": "⏳ تم إرسال طلبك، انتظر موافقة المالك.",
    "رسالة_انتظار_en": "⏳ Your request has been sent, wait for owner approval.",
    "رسالة_موافقة_ar": "✅ تمت الموافقة على طلبك! أرسل /start للبدء.",
    "رسالة_موافقة_en": "✅ Your request has been approved! Send /start to begin.",
    "رسالة_رفض_طلب_ar": "❌ تم رفض طلبك.",
    "رسالة_رفض_طلب_en": "❌ Your request has been rejected.",
    "زر_المواد_ar": "📚 المواد",
    "زر_المواد_en": "📚 Materials",
    "زر_التاريخ_ar": "📅 التاريخ",
    "زر_التاريخ_en": "📅 History",
    "زر_التكاليف_ar": "📝 التكاليف",
    "زر_التكاليف_en": "📝 Assignments",
    "زر_الجدول_ar": "🕐 أوقات المحاضرات",
    "زر_الجدول_en": "🕐 Lecture Times",
    "زر_التنبيهات_ar": "⚠️ تنبيهات",
    "زر_التنبيهات_en": "⚠️ Alerts",
    "زر_الاسعار_ar": "💰 أسعار الملازم",
    "زر_الاسعار_en": "💰 Book Prices",
    "زر_الملخصات_ar": "📖 الملخصات",
    "زر_الملخصات_en": "📖 Summaries",
    "زر_طلب_رفع_ar": "📨 طلب رفع ملف",
    "زر_طلب_رفع_en": "📨 Request Upload",
    "زر_رفع_ملف_ar": "📤 رفع ملف",
    "زر_رفع_ملف_en": "📤 Upload File",
    "زر_رفع_تعليمات_ar": "📹 رفع التعليمات",
    "زر_رفع_تعليمات_en": "📹 Upload Instructions",
    "زر_اشعار_ar": "📢 إرسال إشعار",
    "زر_اشعار_en": "📢 Send Announcement",
    "زر_اضافة_ar": "➕ إضافة بيانات",
    "زر_اضافة_en": "➕ Add Data",
    "زر_تعديل_ar": "✏️ تعديل/حذف بيانات",
    "زر_تعديل_en": "✏️ Edit/Delete Data",
    "زر_المستخدمين_ar": "👥 إدارة المستخدمين",
    "زر_المستخدمين_en": "👥 Manage Users",
    "زر_عوده_ar": "🔙 العودة",
    "زر_عوده_en": "🔙 Back",
    "زر_يوم_ar": "🔍 يوم",
    "زر_يوم_en": "🔍 Day",
    "زر_فتره_ar": "📆 فترة",
    "زر_فتره_en": "📆 Period",
    "زر_تحديد_الكل_ar": "تحديد الكل",
    "زر_تحديد_الكل_en": "Select All",
    "زر_تم_التحديد_ar": "✔️ تم التحديد",
    "زر_تم_التحديد_en": "✔️ Done",
    "زر_حسب_الماده_ar": "📌 حسب المادة",
    "زر_حسب_الماده_en": "📌 By Subject",
    "زر_حسب_التاريخ_ar": "📅 حسب التاريخ",
    "زر_حسب_التاريخ_en": "📅 By Date",
    "زر_اضافة_محاضره_ar": "🕐 إضافة محاضرة",
    "زر_اضافة_محاضره_en": "🕐 Add Lecture",
    "زر_اضافة_تكليف_ar": "📝 إضافة تكليف",
    "زر_اضافة_تكليف_en": "📝 Add Assignment",
    "زر_اضافة_ملخص_ar": "📖 إضافة ملخص",
    "زر_اضافة_ملخص_en": "📖 Add Summary",
    "زر_اضافة_سعر_ar": "💰 إضافة سعر ملزمة",
    "زر_اضافة_سعر_en": "💰 Add Price",
    "زر_اضافة_تنبيه_ar": "⚠️ إضافة تنبيه",
    "زر_اضافة_تنبيه_en": "⚠️ Add Alert",
    "زر_تعديل_محاضره_ar": "🕐 تعديل/حذف محاضرة",
    "زر_تعديل_محاضره_en": "🕐 Edit/Delete Lecture",
    "زر_تعديل_تكليف_ar": "📝 تعديل/حذف تكليف",
    "زر_تعديل_تكليف_en": "📝 Edit/Delete Assignment",
    "زر_تعديل_ملخص_ar": "📖 تعديل/حذف ملخص",
    "زر_تعديل_ملخص_en": "📖 Edit/Delete Summary",
    "زر_تعديل_سعر_ar": "💰 تعديل/حذف سعر",
    "زر_تعديل_سعر_en": "💰 Edit/Delete Price",
    "زر_تعديل_تنبيه_ar": "⚠️ تعديل/حذف تنبيه",
    "زر_تعديل_تنبيه_en": "⚠️ Edit/Delete Alert",
    "زر_تعديل_زرار_ar": "✏️ تعديل",
    "زر_تعديل_زرار_en": "✏️ Edit",
    "زر_حذف_زرار_ar": "🗑 حذف",
    "زر_حذف_زرار_en": "🗑 Delete",
    "رسالة_لا_بيانات_ar": "لا توجد بيانات",
    "رسالة_لا_بيانات_en": "No data found",
    "رسالة_خطأ_ar": "❌ حدث خطأ، حاول مرة أخرى.",
    "رسالة_خطأ_en": "❌ An error occurred, please try again.",
    "رسالة_تم_الحفظ_ar": "✅ تم حفظ البيانات بنجاح!",
    "رسالة_تم_الحفظ_en": "✅ Data saved successfully!",
    "رسالة_تم_الحذف_ar": "✅ تم الحذف!",
    "رسالة_تم_الحذف_en": "✅ Deleted!",
    "رسالة_تم_التعديل_ar": "✅ تم التعديل!",
    "رسالة_تم_التعديل_en": "✅ Updated!",
    "رسالة_ادمن_فقط_ar": "⛔ فقط المدير يستطيع القيام بهذا.",
    "رسالة_ادمن_فقط_en": "⛔ Only admin can do this.",
    "زر_مساعد_نايف_ar": "مساعد نايف",
    "زر_مساعد_نايف_en": "Naif Assistant",
    "رسالة_ai_غير_مفعل_ar": "❌ المساعد الذكي غير مفعّل.",
    "رسالة_ai_غير_مفعل_en": "❌ AI assistant is not enabled.",
    "رسالة_ai_غير_مسموح_ar": "⛔ لا تملك صلاحية استخدام المساعد الذكي.",
    "رسالة_ai_غير_مسموح_en": "⛔ You do not have permission to use the AI assistant.",
    "رسالة_ai_اشتراك_ar": "⛔ هذه الخدمة مدفوعة. للاشتراك تواصل مع منشئ البوت @nt18s",
    "رسالة_ai_اشتراك_en": "⛔ This is a paid service. Contact @nt18s to subscribe.",
    "رسالة_ai_فشل_ar": "❌ فشل الاتصال بخدمة الذكاء الاصطناعي.\nتأكد من صحة المفتاح أو حاول لاحقاً.",
    "رسالة_ai_فشل_en": "❌ Failed to connect to AI service.\nCheck your API key or try again later.",
    "رسالة_ai_تم_الغاء_ar": "🚫 تم إلغاء صلاحية المساعد الذكي.",
    "رسالة_ai_تم_الغاء_en": "🚫 AI assistant permission has been revoked.",
    "رسالة_ai_تفعيل_ar": "🤖 تم تفعيل المساعد الذكي لك!",
    "رسالة_ai_تفعيل_en": "🤖 AI assistant has been enabled for you!",
    "رسالة_ai_تعطيل_ar": "🤖 تم إلغاء صلاحية المساعد الذكي.",
    "رسالة_ai_تعطيل_en": "🤖 AI assistant permission has been revoked.",
    "رسالة_ai_ترحيب_ar": "🤖 *المساعد الذكي*\nالنموذج الحالي: {model}\n\nاكتب سؤالك وسأرد عليك.\nللخروج اضغط 🔙 العودة.",
    "رسالة_ai_ترحيب_en": "🤖 *AI Assistant*\nCurrent model: {model}\n\nType your question and I will answer.\nTo exit press 🔙 Back.",
    "رسالة_تغيير_اللغة_ar": "🌐 اختر اللغة / Choose Language",
    "رسالة_تغيير_اللغة_en": "🌐 Choose Language / اختر اللغة",
    "رسالة_تم_تغيير_اللغة_ar": "✅ تم تغيير اللغة!",
    "رسالة_تم_تغيير_اللغة_en": "✅ Language changed!",
    "رسالة_طلب_جهة_اتصال_ar": "📲 شارك جهة اتصالك لتسهيل التواصل معك:",
    "رسالة_طلب_جهة_اتصال_en": "📲 Share your contact to facilitate communication:",
    "رسالة_شكر_اتصال_ar": "✅ شكراً! تم إرسال معلوماتك.",
    "رسالة_شكر_اتصال_en": "✅ Thank you! Your information has been sent.",
}
BOT_TEXTS = dict(DEFAULT_BOT_TEXTS)

def load_bot_texts():
    global BOT_TEXTS
    try:
        rows = bot_texts_sheet.get_all_values()
        for row in rows:
            if len(row) >= 2 and row[0].strip():
                key = row[0].strip()
                ar_text = row[1].strip() if len(row) > 1 else ""
                en_text = row[2].strip() if len(row) > 2 else ""
                BOT_TEXTS[f"{key}_ar"] = ar_text if ar_text else DEFAULT_BOT_TEXTS.get(f"{key}_ar", key)
                BOT_TEXTS[f"{key}_en"] = en_text if en_text else DEFAULT_BOT_TEXTS.get(f"{key}_en", key)
        logger.info("✅ bot_texts loaded with bilingual support")
    except Exception as e:
        logger.warning(f"bot_texts error: {e}")

def bt(key, uid=None):
    lang = "ar"
    if uid:
        load_user_lang(uid)
        lang = user_lang.get(uid, "ar")
    text_key = f"{key}_{lang}"
    if text_key in BOT_TEXTS:
        return BOT_TEXTS[text_key]
    fallback_key = f"{key}_ar"
    if fallback_key in BOT_TEXTS:
        return BOT_TEXTS[fallback_key]
    return DEFAULT_BOT_TEXTS.get(f"{key}_ar", key)

# ─────────────────────────────────────────────────────
# متغيرات الحالة
# ─────────────────────────────────────────────────────
user_state = {}
user_lang = {}
pending_requests = set()
request_msg_ids = {}
_file_req_store = {}
_file_req_counter = [0]
_approval_store = {}
_approval_counter = [0]
_users_snapshot = {}
user_ai_enabled = {}

# ─────────────────────────────────────────────────────
# 🤖 AI — OpenRouter (نماذج محدثة)
# ─────────────────────────────────────────────────────
AI_MODELS = [
    {"id": "openrouter/free", "name": "Auto (أفضل نموذج مجاني)", "icon": "🎯"},
    {"id": "google/gemini-2.0-flash-exp:free", "name": "Gemini 2.0 Flash", "icon": "✨"},
    {"id": "meta-llama/llama-3.2-3b-instruct:free", "name": "Llama 3.2 3B", "icon": "🦙"},
    {"id": "microsoft/phi-3-mini-128k-instruct:free", "name": "Phi-3 Mini", "icon": "🔵"},
    {"id": "mistralai/mistral-7b-instruct:free", "name": "Mistral 7B", "icon": "💨"},
    {"id": "qwen/qwen-2.5-7b-instruct:free", "name": "Qwen 2.5 7B", "icon": "🐉"},
    {"id": "deepseek/deepseek-chat:free", "name": "DeepSeek Chat", "icon": "🔍"},
]

_ai_current_model = [0]
_ai_histories = {}
_AI_MAX_HISTORY = 20

AI_SYSTEM_PROMPT_BASE = (
    "أنت مساعد ذكي لطلاب الجامعة. أجب دائماً باللغة العربية ما لم يطلب المستخدم غير ذلك. "
    "إجاباتك مختصرة وواضحة ومناسبة للطلاب. لا تستخدم markdown بشكل مبالغ فيه."
)

def _ai_model():
    return AI_MODELS[_ai_current_model[0]]

def _ai_next_model():
    idx = _ai_current_model[0] + 1
    if idx < len(AI_MODELS):
        _ai_current_model[0] = idx
        return AI_MODELS[idx]
    return None

def ai_reset_model():
    _ai_current_model[0] = 0

def ask_ai(uid, user_text, user_role="user", notify_fn=None, send_notify=True):
    if not OPENROUTER_API_KEY:
        log_error(f"OPENROUTER_API_KEY غير موجود", uid)
        return None, None

    if uid not in _ai_histories:
        _ai_histories[uid] = []

    _ai_histories[uid].append({"role": "user", "content": user_text})
    if len(_ai_histories[uid]) > _AI_MAX_HISTORY:
        _ai_histories[uid] = _ai_histories[uid][-_AI_MAX_HISTORY:]

    data_summary = get_data_summary_for_ai(uid, user_role)
    bot_summary = get_bot_code_summary(uid)

    if user_role == "owner":
        role_desc = "أنت مالك البوت. لديك صلاحيات كاملة: إدارة المستخدمين، تغيير الرتب، تفعيل/تعطيل صلاحية AI، بالإضافة إلى كل صلاحيات الأدمن."
    elif user_role == "admin":
        role_desc = "أنت أدمن في البوت. لديك صلاحيات الإضافة والتعديل والحذف على جميع البيانات، ويمكنك إرسال إشعارات ورفع ملفات مباشرة. لا يمكنك رؤية بيانات المستخدمين الآخرين عبر هذه المحادثة."
    else:
        role_desc = "أنت مستخدم عادي. يمكنك فقط عرض البيانات (محاضرات، تكاليف، ملخصات، تنبيهات، أسعار). لا يمكنك رفع ملفات مباشرة، ولكن يمكنك طلب رفع ملف عبر الزر المخصص."

    admin_note = ""
    if user_role in ("admin", "owner"):
        admin_note = (
            "\n\n**ملاحظة للمستخدم (أدمن/مالك):**\n"
            "يمكنك إصدار أوامر لإضافة وتعديل وحذف البيانات مباشرة. مثال:\n"
            "- أضف محاضرة مادة الرياضيات تاريخ 27/03/2026 وقت 08:00-10:00 قاعة القديم:101\n"
            "- أضف تكليف مادة البرمجة تاريخ 28/03/2026 نص: حل المسائل 1-5\n"
            "- احذف محاضرة مادة الفيزياء تاريخ 26/03/2026\n"
            "- أضف سعر مادة الفيزياء 5000\n"
            "- أرسل إشعار سيتم تعطيل البوت غداً\n"
            "- فعّل AI للمستخدم 123456789\n"
            "- اجعل 123456789 مالك\n"
        )

    system_prompt = (
        AI_SYSTEM_PROMPT_BASE + "\n\n" +
        role_desc + "\n\n" +
        f"### قاعدة البيانات ###\n{data_summary}\n\n" +
        f"### شرح البوت ###\n{bot_summary}\n\n" +
        admin_note +
        "**تعليمات مهمة:**\n"
        "1. إذا طلب المستخدم عدداً معيناً من العناصر، أعطه بالضبط العدد الذي طلبه.\n"
        "2. إذا طلب بدون تحديد عدد، أعطه آخر عنصر (أو آخر 2-3 إذا كان ذلك مناسباً).\n"
        "3. استخدم البيانات المتاحة فقط للإجابة.\n"
        "4. لا تقدم معلومات عن المستخدمين الآخرين للمستخدم العادي أو الأدمن.\n"
        "5. كن دقيقاً ومباشراً."
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/study_bot",
        "X-Title": "Study Bot",
    }

    tried = set()
    last_error = None
    while True:
        model = _ai_model()
        if model["id"] in tried:
            break
        tried.add(model["id"])

        payload = {
            "model": model["id"],
            "messages": [
                {"role": "system", "content": system_prompt},
                *_ai_histories[uid],
            ],
            "max_tokens": 1024,
            "temperature": 0.7,
        }

        try:
            resp = _requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers, json=payload, timeout=30
            )

            if resp.status_code == 429:
                log_warning(f"Rate limit على {model['id']}", uid)
                next_m = _ai_next_model()
                if next_m and notify_fn and send_notify:
                    notify_fn(
                        f"⚠️ وصل حد النموذج الحالي.\n"
                        f"🔄 جاري التبديل إلى {next_m['icon']} *{next_m['name']}*..."
                    )
                if not next_m:
                    last_error = "Rate limit exceeded on all models"
                    break
                continue

            if resp.status_code != 200:
                log_error(f"OpenRouter {resp.status_code} {resp.text[:200]} on {model['id']}", uid)
                next_m = _ai_next_model()
                if not next_m:
                    last_error = f"HTTP {resp.status_code}"
                    break
                if notify_fn and send_notify:
                    notify_fn(
                        f"⚠️ فشل النموذج {model['icon']} *{model['name']}*.\n"
                        f"🔄 جاري التبديل إلى النموذج التالي..."
                    )
                continue

            try:
                data = resp.json()
                if "choices" not in data or not data["choices"]:
                    log_error(f"استجابة غير متوقعة من {model['id']}: {data}", uid)
                    next_m = _ai_next_model()
                    continue
                content = data["choices"][0]["message"]["content"].strip()
            except (KeyError, AttributeError, TypeError, json.JSONDecodeError) as e:
                log_error(f"خطأ في تحليل استجابة {model['id']}: {e}", uid)
                next_m = _ai_next_model()
                continue

            _ai_histories[uid].append({"role": "assistant", "content": content})
            if len(_ai_histories[uid]) > _AI_MAX_HISTORY:
                _ai_histories[uid] = _ai_histories[uid][-_AI_MAX_HISTORY:]

            return content, model

        except Exception as e:
            log_error(f"استثناء مع {model['id']}: {e}", uid)
            next_m = _ai_next_model()
            if not next_m:
                last_error = str(e)
                break
            if notify_fn and send_notify:
                notify_fn(
                    f"⚠️ خطأ في النموذج {model['icon']} *{model['name']}*.\n"
                    f"🔄 جاري التبديل إلى النموذج التالي..."
                )
            continue

    _ai_histories[uid].pop()
    log_error(f"فشل جميع النماذج. آخر خطأ: {last_error}", uid)
    ai_reset_model()
    return None, None

# ─────────────────────────────────────────────────────
# دوال مساعدة للشيت
# ─────────────────────────────────────────────────────
AI_ALLOWED_COL = 9

def get_users():
    try:
        allowed, admins, owners, log_ids, ai_allowed = [], [], [], [], []
        open_all = admin_all = False
        es = 0
        for row in users_sheet.get_all_values()[1:]:
            if not row or not any(c.strip() for c in row):
                es += 1
                if es >= 5: break
                continue
            es = 0
            name = row[0].strip()
            uid_str = row[2].strip().lstrip("'") if len(row) > 2 else ""
            allowed_val = row[3].strip().upper() if len(row) > 3 else "FALSE"
            admin_val = row[4].strip().upper() if len(row) > 4 else "FALSE"
            owner_val = row[5].strip().upper() if len(row) > 5 else "FALSE"
            log_val = row[7].strip().upper() if len(row) > 7 else "FALSE"
            ai_val = row[AI_ALLOWED_COL].strip().upper() if len(row) > AI_ALLOWED_COL else "FALSE"
            if name == "الكل":
                if allowed_val == "TRUE": open_all = True
                if admin_val == "TRUE": admin_all = True
                continue
            if not uid_str.isdigit(): continue
            uid = int(uid_str)
            if allowed_val == "TRUE": allowed.append(uid)
            if admin_val == "TRUE": admins.append(uid)
            if owner_val == "TRUE": owners.append(uid)
            if log_val == "TRUE": log_ids.append(uid)
            if ai_val == "TRUE": ai_allowed.append(uid)
        return allowed, admins, owners, open_all, admin_all, log_ids, ai_allowed
    except Exception as e:
        log_error(f"get_users: {e}")
        return [], [], [], False, False, [], []

def get_owner_ids():
    _, _, owners, _, _, _, _ = get_users()
    return owners

def is_owner_id(uid):
    return uid in get_owner_ids()

def is_owner(msg):
    return is_owner_id(msg.from_user.id)

def _is_admin_or_owner(uid):
    _, admins, owners, _, admin_all, _, _ = get_users()
    return admin_all or uid in admins or uid in owners

def get_ai_allowed_users():
    _, _, _, _, _, _, ai = get_users()
    return ai

def is_ai_allowed(uid):
    return uid in get_ai_allowed_users()

def get_user_role(uid):
    _, admins, owners, _, admin_all, _, _ = get_users()
    if uid in owners:
        return "owner"
    if admin_all or uid in admins:
        return "admin"
    return "user"

def get_all_user_ids():
    allowed, _, _, open_all, _, _, _ = get_users()
    return allowed, open_all

def get_all_registered_uids():
    try:
        uids = []
        es = 0
        for row in users_sheet.get_all_values()[1:]:
            if not row or not any(c.strip() for c in row):
                es += 1
                if es >= 5: break
                continue
            es = 0
            uid_str = row[2].strip().lstrip("'") if len(row) > 2 else ""
            if uid_str.isdigit():
                uids.append(int(uid_str))
        return uids
    except:
        return []

def get_user_lang_from_sheet(uid):
    try:
        for row in users_sheet.get_all_values()[1:]:
            if len(row) > 2 and row[2].strip().lstrip("'").isdigit() and int(row[2].strip().lstrip("'")) == uid:
                return "en" if (row[6].strip().upper() if len(row) > 6 else "") == "TRUE" else "ar"
        return "ar"
    except:
        return "ar"

def save_user_lang_to_sheet(uid, lang):
    try:
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if len(row) > 2 and row[2].strip().lstrip("'").isdigit() and int(row[2].strip().lstrip("'")) == uid:
                users_sheet.update_cell(i, 7, lang == "en")
                return True
        return False
    except:
        return False

def load_user_lang(uid):
    if uid not in user_lang:
        user_lang[uid] = get_user_lang_from_sheet(uid)

def add_user_to_sheet(name, uid, auto=False, allowed=True):
    try:
        display = f"🆕 {name}" if auto else name
        users_sheet.append_row([display, "", uid, allowed, False, False, False, False, False],
                                value_input_option="USER_ENTERED")
        return True
    except:
        return False

def set_ai_allowed(uid, allowed):
    try:
        uid_str = str(uid)
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                users_sheet.update_cell(i, AI_ALLOWED_COL + 1, allowed)
                return True
        return False
    except Exception as e:
        log_error(f"set_ai_allowed: {e}")
        return False

def find_user_row_by_id(search_id):
    try:
        sid = str(search_id).strip()
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows, start=1):
            if len(row) > 2 and row[2].strip().lstrip("'") == sid:
                return i, row
        return None, None
    except:
        return None, None

def find_user_row_by_phone(phone):
    try:
        pc = re.sub(r'[\s\-\+]', '', phone.strip())
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows, start=1):
            rp = re.sub(r'[\s\-\+]', '', row[1].strip() if len(row) > 1 else "")
            if rp and rp == pc:
                return i, row
        return None, None
    except:
        return None, None

def get_personal_info(uid):
    try:
        uid_str = str(uid)
        for row in users_sheet.get_all_values()[1:]:
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                name = row[0].strip()
                phone = row[1].strip() if len(row) > 1 else ""
                allowed = (row[3].strip().upper() if len(row) > 3 else "FALSE") == "TRUE"
                admin = (row[4].strip().upper() if len(row) > 4 else "FALSE") == "TRUE"
                owner = (row[5].strip().upper() if len(row) > 5 else "FALSE") == "TRUE"
                ai_allowed = (row[AI_ALLOWED_COL].strip().upper() if len(row) > AI_ALLOWED_COL else "FALSE") == "TRUE"
                role = "مالك" if owner else ("أدمن" if admin else ("مستخدم" if allowed else "غير مصرح"))
                return name, phone, role, ai_allowed
    except Exception as e:
        log_error(f"get_personal_info: {e}")
    return None, None, None, None

def _get_role_icon(uid):
    try:
        uid_str = str(uid)
        for row in users_sheet.get_all_values()[1:]:
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                if (row[5].strip().upper() if len(row) > 5 else "") == "TRUE":
                    return "👑"
                if (row[4].strip().upper() if len(row) > 4 else "") == "TRUE":
                    return "⭐"
                if (row[3].strip().upper() if len(row) > 3 else "") == "TRUE":
                    return "👤"
                return "❌"
    except:
        pass
    return "👤"

def _get_user_name_phone(uid):
    try:
        uid_str = str(uid)
        for row in users_sheet.get_all_values()[1:]:
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                return row[0].strip(), (row[1].strip() if len(row) > 1 else "")
    except:
        pass
    return str(uid), ""

# ─────────────────────────────────────────────────────
# دوال البيانات من الشيت
# ─────────────────────────────────────────────────────
def safe_get(row, idx):
    v = row[idx].strip() if len(row) > idx else ""
    return v.lstrip("'").strip() if v else ""

def get_text(cell):
    return cell.split("|")[0].strip() if "|" in cell else cell.strip()

def get_file_ids(cell):
    if "|" not in cell:
        return []
    part = cell.split("|", 1)[1].strip()
    return [f.strip() for f in part.split(",") if f.strip()] if part else []

def parse_date(d):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(d.strip(), fmt).strftime("%d/%m/%Y")
        except:
            continue
    return d.strip()

def is_valid_date(d):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            datetime.strptime(d.strip(), fmt)
            return True
        except:
            continue
    return False

def get_data():
    try:
        useful = []
        for r in sheet.get_all_values()[1:]:
            if any(len(r) > i and r[i].strip() for i in range(2, 8)):
                useful.append(r)
        return useful
    except:
        return []

def save_lecture(date, subject, time_val, room):
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
        log_error(f"save_lecture: {e}")
        return False

def save_text_to_cell(date, subject, col, text_val):
    try:
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) and parse_date(safe_get(row, 0)) == date and safe_get(row, 1) == subject:
                existing_fids = get_file_ids(safe_get(row, col))
                new_val = text_val if not existing_fids else f"{text_val}|{','.join(existing_fids)}"
                sheet.update_cell(i, col + 1, new_val)
                return True
        new_row = [""] * 8
        new_row[0] = date
        new_row[1] = subject
        new_row[col] = text_val
        sheet.append_row(new_row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        log_error(f"save_text_to_cell: {e}")
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

def get_data_summary_for_ai(uid, user_role):
    data = get_data()
    lines = []

    name, phone, role, ai_allowed = get_personal_info(uid)
    if name:
        lines.append(f"### معلومات المستخدم ###\nالاسم: {name}\nالهاتف: {phone or 'غير مسجل'}\nالرتبة: {role}\nصلاحية AI: {'مفعلة' if ai_allowed else 'معطلة'}\n")
    else:
        lines.append("### معلومات المستخدم ###\nلم يتم العثور على معلوماتك.\n")

    if user_role == "owner":
        try:
            total_users = 0
            total_allowed = 0
            total_admins = 0
            total_owners = 0
            total_ai_allowed = 0
            for row in users_sheet.get_all_values()[1:]:
                if len(row) < 3:
                    continue
                uid_str = row[2].strip().lstrip("'")
                if not uid_str.isdigit():
                    continue
                total_users += 1
                allowed = (row[3].strip().upper() if len(row) > 3 else "FALSE") == "TRUE"
                admin = (row[4].strip().upper() if len(row) > 4 else "FALSE") == "TRUE"
                owner = (row[5].strip().upper() if len(row) > 5 else "FALSE") == "TRUE"
                ai = (row[AI_ALLOWED_COL].strip().upper() if len(row) > AI_ALLOWED_COL else "FALSE") == "TRUE"
                if allowed:
                    total_allowed += 1
                if admin:
                    total_admins += 1
                if owner:
                    total_owners += 1
                if ai:
                    total_ai_allowed += 1
            lines.append("### إحصائيات المستخدمين ###")
            lines.append(f"إجمالي المسجلين: {total_users}")
            lines.append(f"المصرح لهم: {total_allowed}")
            lines.append(f"الأدمن: {total_admins}")
            lines.append(f"المالكين: {total_owners}")
            lines.append(f"المصرح لهم بـ AI: {total_ai_allowed}\n")
        except Exception as e:
            log_error(f"إحصائيات المستخدمين: {e}")

    if not data:
        lines.append("لا توجد بيانات في قاعدة البيانات.")
        return "\n".join(lines)

    subjects = {}
    for row in data:
        date = safe_get(row, 0)
        subject = safe_get(row, 1)
        if not subject:
            continue
        if subject not in subjects:
            subjects[subject] = {"lectures": [], "tasks": [], "summaries": [], "alerts": [], "price": None}
        lect = safe_get(row, 2)
        if lect:
            subjects[subject]["lectures"].append((date, lect))
        task_cell = safe_get(row, 4)
        task_text = get_text(task_cell) if task_cell else None
        if task_text:
            subjects[subject]["tasks"].append((date, task_text))
        summary_cell = safe_get(row, 6)
        summary_text = get_text(summary_cell) if summary_cell else None
        if summary_text:
            subjects[subject]["summaries"].append((date, summary_text))
        alert_cell = safe_get(row, 7)
        alert_text = get_text(alert_cell) if alert_cell else None
        if alert_text:
            subjects[subject]["alerts"].append((date, alert_text))
        price_cell = safe_get(row, 5)
        if price_cell and not subjects[subject]["price"]:
            subjects[subject]["price"] = get_text(price_cell)

    lines.append("### قاعدة البيانات ###")
    for subj in sorted(subjects.keys()):
        details = subjects[subj]
        lines.append(f"\n**المادة: {subj}**")
        if details["price"]:
            lines.append(f"💰 السعر: {details['price']}")
        if details["lectures"]:
            lines.append("🕐 **المحاضرات** (التاريخ - الوقت):")
            for date, time_str in details["lectures"]:
                lines.append(f"   • {date} : {time_str}")
        if details["tasks"]:
            lines.append("📝 **التكاليف** (التاريخ - النص):")
            for date, txt in details["tasks"]:
                lines.append(f"   • {date} : {txt[:200]}")
        if details["summaries"]:
            lines.append("📖 **الملخصات** (التاريخ - النص):")
            for date, txt in details["summaries"]:
                lines.append(f"   • {date} : {txt[:200]}")
        if details["alerts"]:
            lines.append("⚠️ **التنبيهات** (التاريخ - النص):")
            for date, txt in details["alerts"]:
                lines.append(f"   • {date} : {txt[:200]}")

    lines.append(f"\n📚 المواد المتاحة: {', '.join(sorted(subjects.keys()))}")

    if user_role in ("admin", "owner"):
        lines.append("\n### الأوامر الإدارية المتاحة عبر المحادثة ###")
        lines.append("- `أرسل إشعار [النص]` - إرسال إشعار لجميع المستخدمين")
        lines.append("- `فعّل AI للمستخدم [ID]` - تفعيل الذكاء الاصطناعي لمستخدم")
        lines.append("- `عطّل AI للمستخدم [ID]` - تعطيل الذكاء الاصطناعي لمستخدم")
        lines.append("- `اجعل [ID] مالك/أدمن/مستخدم` - تغيير رتبة مستخدم")
        lines.append("- `أضف مستخدم [الاسم] ID [ID]` - إضافة مستخدم جديد")
        lines.append("- `أضف محاضرة [المادة] تاريخ [DD/MM/YYYY] وقت [HH:MM-HH:MM] قاعة [القاعة]`")
        lines.append("- `أضف تكليف [المادة] تاريخ [DD/MM/YYYY] نص: [النص]`")
        lines.append("- `أضف ملخص [المادة] تاريخ [DD/MM/YYYY] نص: [النص]`")
        lines.append("- `أضف سعر [المادة] [السعر]`")
        lines.append("- `احذف [محاضرة/تكليف/ملخص/تنبيه] [المادة] تاريخ [DD/MM/YYYY]`")

    return "\n".join(lines)

def get_bot_code_summary(uid):
    lines = []
    lines.append("### معلومات عامة عن البوت ###")
    lines.append("- هذا بوت دراسي لإدارة المواد الجامعية والمحاضرات والتكاليف.")
    lines.append("- يدعم Google Sheets كقاعدة بيانات.")
    lines.append("- يدعم اللغة العربية والإنجليزية.")

    lines.append("\n### الرتب والصلاحيات ###")
    lines.append("- **مستخدم عادي**: يمكنه عرض البيانات، طلب رفع ملف، استخدام المساعد الذكي (إذا فعّل المالك).")
    lines.append("- **أدمن**: يمكنه إضافة/تعديل/حذف البيانات، رفع ملفات مباشرة، إرسال إشعارات، رفع تعليمات.")
    lines.append("- **مالك**: كل صلاحيات الأدمن + إدارة المستخدمين (الموافقة على الطلبات، تغيير الرتب، تفعيل AI).")

    lines.append("\n### الأزرار الرئيسية ###")
    button_keys = [
        "زر_المواد", "زر_التاريخ", "زر_التكاليف", "زر_الجدول", "زر_التنبيهات",
        "زر_الاسعار", "زر_الملخصات", "زر_طلب_رفع", "زر_رفع_ملف", "زر_رفع_تعليمات",
        "زر_اشعار", "زر_اضافة", "زر_تعديل", "زر_المستخدمين", "زر_عوده"
    ]
    for key in button_keys:
        lines.append(f"- **{bt(key, uid)}**: {_get_button_description(key)}")

    lines.append("\n### أوامر البوت ###")
    lines.append("- `/start` - بدء البوت وعرض القائمة")
    lines.append("- `/ai` - تشغيل المساعد الذكي (إذا كانت الصلاحية مفعلة)")
    lines.append("- `/ai_reset` - إعادة تعيين نموذج AI (للمالك فقط)")
    lines.append("- `/ai_clear` - مسح سياق محادثة AI")
    lines.append("- `/lang` - تغيير اللغة")
    lines.append("- `/help` - عرض التعليمات")

    lines.append("\n### كيف يعمل المساعد الذكي ###")
    lines.append("- يتم تفعيله عبر زر '🤖 مساعد نايف' في القائمة.")
    lines.append("- عند التفعيل، كل الرسائل النصية والتسجيلات الصوتية تمر للذكاء الاصطناعي.")
    lines.append("- الأزرار لا تمر للذكاء الاصطناعي وتعمل بشكل طبيعي.")
    lines.append("- الأدمن والمالك يمكنهم تنفيذ الأوامر الإدارية عبر النص.")
    lines.append("- الذكاء الاصطناعي يقرأ قاعدة البيانات ويجيب على الأسئلة.")

    return "\n".join(lines)

def _get_button_description(key):
    desc = {
        "زر_المواد": "يعرض قائمة المواد المتاحة. بعد اختيار مادة، يمكنك اختيار عرض جدولها، تكاليفها، ملخصاتها، تنبيهاتها، أو سعرها.",
        "زر_التاريخ": "يسمح بالبحث عن البيانات حسب التاريخ (يوم محدد أو فترة زمنية).",
        "زر_التكاليف": "يعرض آخر التكاليف المضافة لجميع المواد.",
        "زر_الجدول": "يعرض أوقات المحاضرات لآخر يوم دراسي.",
        "زر_التنبيهات": "يعرض التنبيهات الحالية.",
        "زر_الاسعار": "يعرض أسعار الملازم لجميع المواد.",
        "زر_الملخصات": "يعرض آخر الملخصات المضافة.",
        "زر_طلب_رفع": "للمستخدمين العاديين: يتيح طلب رفع ملف (سيتم إرسال طلب للمشرف).",
        "زر_رفع_ملف": "للأدمن: يسمح برفع ملف مباشرة للتكليف أو الملخص.",
        "زر_رفع_تعليمات": "للأدمن: يسمح برفع تعليمات للمستخدمين أو الأدمن.",
        "زر_اشعار": "للأدمن: يسمح بإرسال إشعار لجميع المستخدمين.",
        "زر_اضافة": "للأدمن: يسمح بإضافة محاضرة، تكليف، ملخص، سعر، أو تنبيه.",
        "زر_تعديل": "للأدمن: يسمح بتعديل أو حذف البيانات الموجودة.",
        "زر_المستخدمين": "للمالك فقط: يعرض قائمة المستخدمين ويتيح التحكم بصلاحياتهم.",
        "زر_عوده": "يعود إلى القائمة الرئيسية."
    }
    return desc.get(key, "زر للتحكم في البوت.")

# ─────────────────────────────────────────────────────
# دوال الأزرار والقوائم
# ─────────────────────────────────────────────────────
BUTTON_TEXTS = set()

def load_button_texts():
    global BUTTON_TEXTS
    BUTTON_TEXTS = set()
    button_keys = [
        "زر_المواد", "زر_التاريخ", "زر_التكاليف", "زر_الجدول", "زر_التنبيهات",
        "زر_الاسعار", "زر_الملخصات", "زر_طلب_رفع", "زر_رفع_ملف", "زر_رفع_تعليمات",
        "زر_اشعار", "زر_اضافة", "زر_تعديل", "زر_المستخدمين", "زر_عوده",
        "زر_يوم", "زر_فتره", "زر_تحديد_الكل", "زر_تم_التحديد", "زر_حسب_الماده",
        "زر_حسب_التاريخ", "زر_اضافة_محاضره", "زر_اضافة_تكليف", "زر_اضافة_ملخص",
        "زر_اضافة_سعر", "زر_اضافة_تنبيه", "زر_تعديل_محاضره", "زر_تعديل_تكليف",
        "زر_تعديل_ملخص", "زر_تعديل_سعر", "زر_تعديل_تنبيه", "زر_تعديل_زرار", "زر_حذف_زرار"
    ]
    for key in button_keys:
        BUTTON_TEXTS.add(bt(key))
    BUTTON_TEXTS.update([
        "🤖 مساعد نايف", "🟢 🤖 مساعد نايف", "🔴 🤖 مساعد نايف",
        "📤 إرسال الآن", "✅ إرسال", "➕ إضافة محاضرة أخرى",
        "🚫 لا يوجد", "⏭️ تخطي", "🔄 استبدال", "✏️ بجانبه", "🔄 بدله",
        "✅ نعم، احذف", "❌ إلغاء", "📤 إرسال بدون نص", "👤 للمستخدمين",
        "👑 للأدمن", "👤 تعليمات المستخدم", "👑 تعليمات الأدمن",
        "🔍 بحث بالID", "🔍 بحث بالرقم", "🇾🇪 العربية", "🇬🇧 English",
        "📋 عرض جميع المستخدمين"
    ])

def main_menu(uid, admin=False, owner=False):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    if admin or owner:
        m.row(bt("زر_التاريخ", uid), bt("زر_المواد", uid))
        m.row(bt("زر_التكاليف", uid), bt("زر_الجدول", uid))
        m.row(bt("زر_الاسعار", uid), bt("زر_الملخصات", uid), bt("زر_التنبيهات", uid))
        m.row(bt("زر_اضافة", uid), bt("زر_تعديل", uid))
        m.row(bt("زر_اشعار", uid), bt("زر_رفع_ملف", uid), bt("زر_رفع_تعليمات", uid))
        if owner:
            m.add(bt("زر_المستخدمين", uid))
    else:
        m.row(bt("زر_التاريخ", uid), bt("زر_المواد", uid))
        m.row(bt("زر_التكاليف", uid), bt("زر_الجدول", uid), bt("زر_الملخصات", uid))
        m.row(bt("زر_الاسعار", uid), bt("زر_طلب_رفع", uid), bt("زر_التنبيهات", uid))

    if OPENROUTER_API_KEY:
        status = "🟢" if user_ai_enabled.get(uid, False) else "🔴"
        m.add(f"{status} 🤖 {bt('زر_مساعد_نايف', uid)}")
    return m

def back_only_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add(bt("زر_عوده", uid))
    return m

def back_skip_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row("⏭️ تخطي", bt("زر_عوده", uid))
    return m

def back_with_noexist(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("لا يوجد", bt("زر_عوده", uid))
    return m

def subjects_menu_kb(uid):
    subjects = get_subjects()
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for s in subjects:
        m.add(s)
    m.add(bt("زر_عوده", uid))
    return m, subjects

def subjects_with_noexist_kb(uid):
    subjects = get_subjects()
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for s in subjects:
        m.add(s)
    m.add("🚫 لا يوجد", bt("زر_عوده", uid))
    return m, subjects

def subject_options_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for k in ["خيار_الجدول", "خيار_التكاليف", "خيار_السعر", "خيار_الملخص", "خيار_التنبيهات"]:
        m.add(bt(k, uid))
    m.add(bt("زر_عوده", uid))
    return m

def dates_menu_kb(dates, uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for d in dates:
        m.add(d)
    m.add(bt("زر_عوده", uid))
    return m

def file_type_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(bt("زر_اضافة_تكليف", uid), bt("زر_اضافة_ملخص", uid))
    m.add(bt("زر_عوده", uid))
    return m

def add_data_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row(bt("زر_اضافة_محاضره", uid), bt("زر_اضافة_تكليف", uid))
    m.row(bt("زر_اضافة_ملخص", uid), bt("زر_اضافة_سعر", uid))
    m.add(bt("زر_اضافة_تنبيه", uid))
    m.add(bt("زر_عوده", uid))
    return m

def edit_data_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row(bt("زر_تعديل_محاضره", uid), bt("زر_تعديل_تكليف", uid))
    m.row(bt("زر_تعديل_ملخص", uid), bt("زر_تعديل_سعر", uid))
    m.add(bt("زر_تعديل_تنبيه", uid))
    m.add(bt("زر_عوده", uid))
    return m

def edit_action_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(bt("زر_تعديل_زرار", uid), bt("زر_حذف_زرار", uid))
    m.add(bt("زر_عوده", uid))
    return m

def buildings_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("🏛 القديم", "🏫 الاداب")
    m.add(bt("زر_عوده", uid))
    return m

def rooms_menu_kb(building, uid):
    rooms = get_rooms(building)
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for r in rooms:
        m.add(r)
    m.add(bt("زر_عوده", uid))
    return m, rooms

def lecture_time_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("🕐 08:00 - 10:00", "🕐 10:00 - 12:00")
    m.add("🕐 12:00 - 14:00", "⏰ توقيت آخر")
    m.add("لا يوجد", bt("زر_عوده", uid))
    return m

def manage_users_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row("🔍 بحث بالID", "🔍 بحث بالرقم")
    m.row("📋 عرض جميع المستخدمين")
    m.add(bt("زر_عوده", uid))
    return m

def display_mode_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row(bt("زر_حسب_التاريخ", uid), bt("زر_حسب_الماده", uid))
    m.add(bt("زر_عوده", uid))
    return m

def date_type_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row(bt("زر_يوم", uid), bt("زر_فتره", uid))
    m.add(bt("زر_عوده", uid))
    return m

def help_audience_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("👤 للمستخدمين", "👑 للأدمن")
    m.add(bt("زر_عوده", uid))
    return m

def help_view_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("👤 تعليمات المستخدم", "👑 تعليمات الأدمن")
    m.add(bt("زر_عوده", uid))
    return m

def lang_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("🇾🇪 العربية", "🇬🇧 English")
    return m

def upload_confirm_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row("✅ إرسال", bt("زر_عوده", uid))
    return m

def get_subjects():
    try:
        seen, result = set(), []
        for row in sheet.get_all_values()[1:]:
            s = row[1].strip() if len(row) > 1 else ""
            if s and s not in seen:
                seen.add(s)
                result.append(s)
        return result
    except Exception as e:
        log_error(f"get_subjects: {e}")
        return []

def get_rooms(building):
    try:
        if not rooms_sheet:
            return []
        return [r[1].strip() for r in rooms_sheet.get_all_values()
                if len(r) > 1 and r[0].strip() == building and r[1].strip()]
    except:
        return []

def send_date_suggestions(chat_id, subject=None, for_lecture=False, for_alert=False, uid=None):
    now = datetime.now(YEMEN_TZ)
    today = now.strftime("%d/%m/%Y")
    tmrw = (now + timedelta(days=1)).strftime("%d/%m/%Y")
    if for_lecture or for_alert:
        lines = [f"`{tmrw}`", f"`{today}`"]
    else:
        lines = [f"`{today}`"]
    lines = lines[:4]
    msg = "📅 تواريخ مقترحة (اضغط للنسخ):\n\n" + "\n".join(lines)
    bot.send_message(chat_id, msg, parse_mode="Markdown")

def get_settings():
    return bt("رسالة_الترحيب"), bt("رسالة_الرفض")

# ─────────────────────────────────────────────────────
# دوال الأوامر الإدارية النصية (محدثة)
# ─────────────────────────────────────────────────────
def try_execute_admin_command(text, uid, user_role, chat_id, bot_instance):
    if user_role not in ("admin", "owner"):
        return False, None

    text = text.strip()
    executed = False
    response = None

    # ========== إرسال إشعار لجميع المستخدمين ==========
    pattern_broadcast = r'(?:أرسل|إرسال)\s*إشعار\s*(.+)'
    m = re.search(pattern_broadcast, text, re.IGNORECASE)
    if m:
        broadcast_text = m.group(1).strip()
        if broadcast_text:
            uids, open_all = get_all_user_ids()
            if open_all:
                registered = get_all_registered_uids()
                if registered:
                    uids = registered
            if not uids:
                return True, "⚠️ لا يوجد مستخدمون لإرسال الإشعار لهم."
            success = 0
            fail = 0
            for user_id in uids:
                try:
                    bot_instance.send_message(user_id, f"📢 *إشعار:*\n\n{broadcast_text}", parse_mode="Markdown")
                    success += 1
                except:
                    fail += 1
            return True, f"✅ تم إرسال الإشعار!\n✅ {success} | ❌ {fail}"
        else:
            return False, "❌ يجب إدخال نص الإشعار. مثال: أرسل إشعار سيتم تعطيل البوت غداً"

    # ========== إضافة مستخدم جديد ==========
    pattern_add_user = r'(?:أضف|إضافة)\s*مستخدم\s*(.+?)(?:\s+ID\s*(\d+)|(?:\s+بالرقم\s*(\d+)))?$'
    m = re.search(pattern_add_user, text, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        uid_str = m.group(2) or m.group(3)
        if uid_str and uid_str.isdigit():
            new_uid = int(uid_str)
            _, row = find_user_row_by_id(new_uid)
            if row:
                return True, f"⚠️ المستخدم {new_uid} موجود بالفعل."
            if add_user_to_sheet(name, new_uid, auto=False, allowed=True):
                return True, f"✅ تم إضافة المستخدم {name} (ID: {new_uid}) بنجاح."
            else:
                return True, "❌ حدث خطأ أثناء إضافة المستخدم."
        else:
            return False, "❌ يجب إدخال ID صحيح. مثال: أضف مستخدم أحمد 123456789"

    # ========== تغيير صلاحية مستخدم (تفعيل/تعطيل AI) ==========
    pattern_toggle_ai = r'(?:فعّل|عطّل|تفعيل|تعطيل)\s*AI\s*(?:للمستخدم)?\s*(\d+)'
    m = re.search(pattern_toggle_ai, text, re.IGNORECASE)
    if m:
        target_uid = int(m.group(1))
        is_enable = "فعّل" in text or "تفعيل" in text
        if set_ai_allowed(target_uid, is_enable):
            name, _ = _get_user_name_phone(target_uid)
            status = "مفعل" if is_enable else "معطل"
            try:
                msg = bt("رسالة_ai_تفعيل", target_uid) if is_enable else bt("رسالة_ai_تعطيل", target_uid)
                bot_instance.send_message(target_uid, msg)
            except:
                pass
            return True, f"✅ تم {status} AI للمستخدم {name} (ID: {target_uid})"
        else:
            return True, f"❌ فشل تغيير صلاحية AI للمستخدم {target_uid}"

    # ========== تغيير رتبة مستخدم ==========
    pattern_change_role = r'(?:اجعل|حول|غير)\s*(?:المستخدم)?\s*(\d+|.+?)\s*(مالك|أدمن|مستخدم)'
    m = re.search(pattern_change_role, text, re.IGNORECASE)
    if m:
        identifier = m.group(1).strip()
        target_role = m.group(2).strip()
        if identifier.isdigit():
            target_uid = int(identifier)
        else:
            _, row = find_user_row_by_phone(identifier)
            if not row:
                _, row = find_user_row_by_id(identifier)
            if row:
                target_uid = int(row[2].strip().lstrip("'"))
            else:
                return False, f"❌ لم أجد مستخدم باسم '{identifier}'"

        try:
            rows = users_sheet.get_all_values()
            for i, row in enumerate(rows[1:], start=2):
                if len(row) > 2 and row[2].strip().lstrip("'") == str(target_uid):
                    if target_role == "مالك":
                        users_sheet.update(f"D{i}:F{i}", [[True, True, True]])
                        role_name = "مالك"
                    elif target_role == "أدمن":
                        users_sheet.update(f"D{i}:F{i}", [[True, True, False]])
                        role_name = "أدمن"
                    else:
                        users_sheet.update(f"D{i}:F{i}", [[True, False, False]])
                        role_name = "مستخدم"
                    name, phone = _get_user_name_phone(target_uid)
                    notify_owners_action(target_uid, name, phone, f"أمر من {uid}", f"set_{role_name}")
                    try:
                        bot_instance.send_message(target_uid, f"✅ تم تغيير رتبتك إلى {role_name}")
                    except:
                        pass
                    return True, f"✅ تم تغيير رتبة المستخدم {name} إلى {role_name}"
            return True, f"❌ لم أجد المستخدم {target_uid}"
        except Exception as e:
            log_error(f"change_role: {e}")
            return True, "❌ حدث خطأ أثناء تغيير الرتبة"

    # ========== إضافة محاضرة ==========
    pattern_add_lecture = r'(?:أضف|إضافة)\s*محاضرة\s*(?:مادة\s*)?([^\s]+)\s*(?:تاريخ\s*)?(\d{1,2}/\d{1,2}/\d{4})\s*(?:وقت\s*)?(\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})\s*(?:قاعة\s*)?(.+)'
    m = re.search(pattern_add_lecture, text, re.IGNORECASE)
    if m:
        subject = m.group(1).strip()
        date = m.group(2).strip()
        time_val = m.group(3).strip()
        room = m.group(4).strip()
        if not is_valid_date(date):
            return False, "❌ التاريخ غير صحيح. استخدم صيغة DD/MM/YYYY."
        if save_lecture(date, subject, time_val, room):
            return True, f"✅ تم إضافة المحاضرة:\n📌 {subject}\n📅 {date}\n🕐 {time_val}\n📍 {room}"
        else:
            return False, "❌ حدث خطأ أثناء الإضافة."

    # ========== إضافة تكليف ==========
    pattern_add_task = r'(?:أضف|إضافة)\s*(?:تكليف|واجب)\s*(?:مادة\s*)?([^\s]+)\s*(?:تاريخ\s*)?(\d{1,2}/\d{1,2}/\d{4})\s*(?:نص\s*)?(.+)'
    m = re.search(pattern_add_task, text, re.IGNORECASE)
    if m:
        subject = m.group(1).strip()
        date = m.group(2).strip()
        task_text = m.group(3).strip()
        if not is_valid_date(date):
            return False, "❌ التاريخ غير صحيح."
        if save_text_to_cell(date, subject, 4, task_text):
            return True, f"✅ تم إضافة التكليف:\n📌 {subject}\n📅 {date}\n📝 {task_text}"
        else:
            return False, "❌ خطأ في الحفظ."

    # ========== إضافة ملخص ==========
    pattern_add_summary = r'(?:أضف|إضافة)\s*ملخص\s*(?:مادة\s*)?([^\s]+)\s*(?:تاريخ\s*)?(\d{1,2}/\d{1,2}/\d{4})\s*(?:نص\s*)?(.+)'
    m = re.search(pattern_add_summary, text, re.IGNORECASE)
    if m:
        subject = m.group(1).strip()
        date = m.group(2).strip()
        summary_text = m.group(3).strip()
        if not is_valid_date(date):
            return False, "❌ التاريخ غير صحيح."
        if save_text_to_cell(date, subject, 6, summary_text):
            return True, f"✅ تم إضافة الملخص:\n📌 {subject}\n📅 {date}\n📖 {summary_text}"
        else:
            return False, "❌ خطأ في الحفظ."

    # ========== إضافة سعر ==========
    pattern_add_price = r'(?:أضف|إضافة)\s*سعر\s*(?:مادة\s*)?([^\s]+)\s*(?:سعر\s*)?(.+)'
    m = re.search(pattern_add_price, text, re.IGNORECASE)
    if m:
        subject = m.group(1).strip()
        price = m.group(2).strip()
        rows = sheet.get_all_values()
        updated = False
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 1) == subject:
                sheet.update_cell(i, 6, price)
                updated = True
                break
        if not updated:
            sheet.append_row(["", subject, "", "", "", price, "", ""], value_input_option="USER_ENTERED")
        return True, f"✅ تم تحديث سعر مادة {subject} إلى {price}"

    # ========== حذف عنصر ==========
    pattern_delete = r'(?:احذف|حذف)\s*(محاضرة|تكليف|ملخص|تنبيه)\s*(?:مادة\s*)?([^\s]+)\s*(?:تاريخ\s*)?(\d{1,2}/\d{1,2}/\d{4})'
    m = re.search(pattern_delete, text, re.IGNORECASE)
    if m:
        type_word = m.group(1)
        subject = m.group(2).strip()
        date = m.group(3).strip()
        col_map = {"محاضرة": 2, "تكليف": 4, "ملخص": 6, "تنبيه": 7}
        col = col_map.get(type_word)
        if col:
            if delete_cell(date, subject, col):
                return True, f"✅ تم حذف {type_word} للمادة {subject} بتاريخ {date}"
            else:
                return False, f"❌ لم يتم العثور على {type_word} للمادة {subject} بتاريخ {date}"
        else:
            return False, "النوع غير معروف."

    # ========== إضافة تنبيه ==========
    pattern_add_alert = r'(?:أضف|إضافة)\s*تنبيه\s*(?:مادة\s*)?([^\s]+)\s*(?:تاريخ\s*)?(\d{1,2}/\d{1,2}/\d{4})\s*(?:نص\s*)?(.+)'
    m = re.search(pattern_add_alert, text, re.IGNORECASE)
    if m:
        subject = m.group(1).strip()
        date = m.group(2).strip()
        alert_text = m.group(3).strip()
        if not is_valid_date(date):
            return False, "❌ التاريخ غير صحيح."
        if save_text_to_cell(date, subject, 7, alert_text):
            return True, f"✅ تم إضافة التنبيه:\n📌 {subject}\n📅 {date}\n⚠️ {alert_text}"
        else:
            return False, "❌ خطأ في الحفظ."

    return False, None

# ─────────────────────────────────────────────────────
# دوال إرسال الملفات
# ─────────────────────────────────────────────────────
def _try_send_file(chat_id, fid, caption=None, parse_mode=None, reply_markup=None):
    for sender in [bot.send_photo, bot.send_video, bot.send_audio,
                   bot.send_voice, bot.send_document]:
        try:
            sender(chat_id, fid, caption=caption, parse_mode=parse_mode,
                   reply_markup=reply_markup)
            return True
        except:
            continue
    return False

def send_files_with_text(chat_id, text, fids, reply_markup=None):
    if not fids:
        if text:
            bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=reply_markup)
        return
    cap = text[:1024] if text else None
    parse = "Markdown" if cap else None
    if len(fids) == 1:
        ok = _try_send_file(chat_id, fids[0], caption=cap, parse_mode=parse, reply_markup=reply_markup)
        if not ok and text:
            bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=reply_markup)
        return
    for fid in fids:
        _try_send_file(chat_id, fid)
    if text:
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=reply_markup)

# ─────────────────────────────────────────────────────
# دوال التسجيلات الصوتية
# ─────────────────────────────────────────────────────
def transcribe_voice(file_id, lang="ar"):
    if not OPENROUTER_API_KEY:
        return None
    try:
        file_info = bot.get_file(file_id)
        file_path = file_info.file_path
        file_url = f"https://api.telegram.org/file/bot{STUDY_BOT_TOKEN}/{file_path}"
        response = _requests.get(file_url)
        if response.status_code != 200:
            log_error(f"فشل تحميل الملف الصوتي: {response.status_code}")
            return None
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
        files = {
            "file": (file_path, response.content),
            "model": (None, "whisper-1"),
            "language": (None, lang),
        }
        resp = _requests.post(
            "https://openrouter.ai/api/v1/audio/transcriptions",
            headers=headers,
            files=files,
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("text", "").strip()
        else:
            log_error(f"Whisper error: {resp.status_code} {resp.text}")
            return None
    except Exception as e:
        log_error(f"transcribe_voice: {e}")
        return None

# ─────────────────────────────────────────────────────
# دوال إشعارات المالكين
# ─────────────────────────────────────────────────────
def notify_owners_new_request(requester_id, requester_name, phone=""):
    owners = get_owner_ids()
    _approval_counter[0] += 1
    short_key = str(_approval_counter[0])
    _approval_store[short_key] = {
        "requester_id": requester_id,
        "requester_name": requester_name,
        "phone": phone,
    }
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("✅ قبول", callback_data=f"approve_{short_key}"),
        telebot.types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_{short_key}")
    )
    ph = f"📞 الرقم: `{phone}`\n" if phone else ""
    msg = (f"📩 طلب انضمام جديد!\n\n"
           f"👤 الاسم: `{requester_name}`\n"
           f"🆔 المعرف: `{requester_id}`\n{ph}")
    if requester_id not in request_msg_ids:
        request_msg_ids[requester_id] = {}
    for oid in owners:
        try:
            sent = bot.send_message(oid, msg, parse_mode="Markdown", reply_markup=markup)
            request_msg_ids[requester_id][oid] = sent.message_id
        except:
            pass

def notify_owners_action(target_id, target_name, phone, actor, action):
    EVENT = {
        "approve": ("✅", "تمت الموافقة على طلب الانضمام"),
        "reject": ("❌", "تم رفض طلب الانضمام"),
        "remove": ("🚫", "تم إلغاء صلاحية المستخدم"),
        "set_user": ("🔄", "تم تعيين دور مستخدم عادي"),
        "set_admin": ("⭐", "تم الترقية إلى أدمن"),
        "set_owner": ("👑", "تم الترقية إلى مالك"),
        "downgrade_owner": ("⬇️", "تم تخفيض رتبة المالك → مستخدم"),
        "downgrade_owner_to_user": ("⬇️", "تم تخفيض رتبة المالك → مستخدم"),
        "downgrade_admin": ("⬇️", "تم تخفيض رتبة الأدمن → مستخدم"),
        "ai_enabled": ("🤖", "تم تفعيل المساعد الذكي"),
        "ai_disabled": ("🚫", "تم تعطيل المساعد الذكي"),
    }
    icon, title = EVENT.get(action, ("🔔", action))
    if actor == "الشيت":
        actor_line = "📊 تعديل مباشر في الشيت"
    elif actor == "الكود السري":
        actor_line = "🔑 استخدام الكود السري"
    else:
        actor_line = f"👤 {actor}"
    ph = f"\n📞 `{phone}`" if phone else ""
    msg = (f"{icon} *{title}*\n━━━━━━━━━━━━━━━━━━━━\n"
           f"👤 {target_name}\n🆔 `{target_id}`{ph}\n━━━━━━━━━━━━━━━━━━━━\n🔧 {actor_line}")
    owners = get_owner_ids()
    if action in ("approve", "reject"):
        msg_ids = request_msg_ids.pop(target_id, {})
        for oid in owners:
            mid = msg_ids.get(oid)
            if mid:
                try:
                    bot.delete_message(oid, mid)
                except:
                    pass
    for oid in owners:
        try:
            bot.send_message(oid, msg, parse_mode="Markdown")
        except:
            pass

# ─────────────────────────────────────────────────────
# دوال عرض النتائج
# ─────────────────────────────────────────────────────
def send_search_results(chat_id, uid, date_filter, subjects_filter, types_filter, display_mode):
    data = get_data()
    is_range = isinstance(date_filter, tuple)
    if is_range:
        d1, d2 = date_filter
        range_str = f"{format_date_ar(d1)} — {format_date_ar(d2)}"
    else:
        range_str = format_date_ar(date_filter)

    def match_date(r):
        rd = safe_get(r, 0)
        if not rd:
            return False
        try:
            pd = parse_date(rd)
        except:
            return False
        if is_range:
            return dates_in_range(pd, d1, d2)
        return pd == date_filter

    filtered = [r for r in data if match_date(r) and safe_get(r, 1) in subjects_filter]
    if not filtered:
        bot.send_message(chat_id, f"{bt('رسالة_لا_بيانات', uid)}\n📅 {range_str}")
        return

    found = False
    if display_mode == "date":
        all_dates = sorted(
            set(parse_date(safe_get(r, 0)) for r in filtered if safe_get(r, 0)),
            key=lambda x: datetime.strptime(x, "%d/%m/%Y")
        )
        for d in all_dates:
            rows_d = [r for r in filtered if safe_get(r, 0) and parse_date(safe_get(r, 0)) == d]
            if not rows_d:
                continue
            day = get_day_name(d, uid)
            d_ar = format_date_ar(d)
            msg = f"📅 *{d_ar} — {day}*\n{'━' * 20}\n"
            fids_all = []
            has_content = False
            for row in rows_d:
                subj = safe_get(row, 1)
                parts = []
                if "محاضرات" in types_filter:
                    t = safe_get(row, 2)
                    if t:
                        parts.append(f"🕐 {t}")
                if "تكاليف" in types_filter:
                    cell = safe_get(row, 4)
                    tx = get_text(cell)
                    fi = get_file_ids(cell)
                    if tx:
                        parts.append(f"📝 {tx}")
                    fids_all.extend(fi)
                if "ملخصات" in types_filter:
                    cell = safe_get(row, 6)
                    tx = get_text(cell)
                    fi = get_file_ids(cell)
                    if tx:
                        parts.append(f"📖 {tx}")
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
                key=lambda r: datetime.strptime(parse_date(safe_get(r, 0)), "%d/%m/%Y") if safe_get(r, 0) else datetime.min
            )
            if not rows_s:
                continue
            msg = f"📌 *{subj}*\n{'━' * 20}\n"
            fids_all = []
            has_content = False
            for row in rows_s:
                d = parse_date(safe_get(row, 0))
                day = get_day_name(d, uid)
                d_ar = format_date_ar(d)
                parts = [f"📅 {d_ar} — {day}"]
                if "محاضرات" in types_filter:
                    t = safe_get(row, 2)
                    if t:
                        parts.append(f"🕐 {t}")
                if "تكاليف" in types_filter:
                    cell = safe_get(row, 4)
                    tx = get_text(cell)
                    fi = get_file_ids(cell)
                    if tx:
                        parts.append(f"📝 {tx}")
                    fids_all.extend(fi)
                if "ملخصات" in types_filter:
                    cell = safe_get(row, 6)
                    tx = get_text(cell)
                    fi = get_file_ids(cell)
                    if tx:
                        parts.append(f"📖 {tx}")
                    fids_all.extend(fi)
                if len(parts) > 1:
                    msg += "\n".join(parts) + "\n─\n"
                    has_content = True
            if has_content or fids_all:
                found = True
                send_files_with_text(chat_id, msg, fids_all)

    if not found:
        bot.send_message(chat_id, f"{bt('رسالة_لا_بيانات', uid)}\n📅 {range_str}")

def get_day_name(date_str, uid=None):
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return DAYS_EN[dt.weekday()] if uid and user_lang.get(uid, "ar") == "en" else DAYS_AR[dt.weekday()]
    except:
        return ""

def format_date_ar(date_str):
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return f"{dt.day} {MONTHS_AR[dt.month]}"
    except:
        return date_str

def dates_in_range(date_str, d1, d2):
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        dt1 = datetime.strptime(d1, "%d/%m/%Y")
        dt2 = datetime.strptime(d2, "%d/%m/%Y")
        if dt1 > dt2:
            dt1, dt2 = dt2, dt1
        return dt1 <= dt <= dt2
    except:
        return False

def get_last_date(data, col):
    dates = []
    for r in data:
        d = safe_get(r, 0)
        if d and (get_text(safe_get(r, col)) or get_file_ids(safe_get(r, col))):
            try:
                dates.append(parse_date(d))
            except:
                pass
    return sorted(dates, key=lambda x: datetime.strptime(x, "%d/%m/%Y"))[-1] if dates else None

DAYS_AR = {0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس", 4: "الجمعة", 5: "السبت", 6: "الأحد"}
DAYS_EN = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
MONTHS_AR = {1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
             7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"}

# ─────────────────────────────────────────────────────
# دوال مراقبة التغييرات
# ─────────────────────────────────────────────────────
def _snapshot_users():
    snap = {}
    try:
        for row in users_sheet.get_all_values()[1:]:
            uid_str = row[2].strip().lstrip("'") if len(row) > 2 else ""
            if not uid_str.isdigit():
                continue
            snap[uid_str] = {
                "allowed": (row[3].strip().upper() if len(row) > 3 else "FALSE") == "TRUE",
                "admin": (row[4].strip().upper() if len(row) > 4 else "FALSE") == "TRUE",
                "owner": (row[5].strip().upper() if len(row) > 5 else "FALSE") == "TRUE",
                "ai": (row[AI_ALLOWED_COL].strip().upper() if len(row) > AI_ALLOWED_COL else "FALSE") == "TRUE",
                "name": row[0].strip(),
                "phone": row[1].strip() if len(row) > 1 else "",
            }
    except:
        pass
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
                if not old:
                    continue
                uid = int(uid_str)
                name = new["name"]
                phone = new["phone"]
                if new["owner"] and not old["owner"]:
                    try:
                        bot.send_message(uid, "👑 تمت ترقيتك إلى مالك!")
                    except:
                        pass
                    notify_owners_action(uid, name, phone, "الشيت", "set_owner")
                elif new["admin"] and not old["admin"]:
                    try:
                        bot.send_message(uid, "⭐ تمت ترقيتك إلى أدمن!")
                    except:
                        pass
                    notify_owners_action(uid, name, phone, "الشيت", "set_admin")
                elif new["allowed"] and not old["allowed"]:
                    try:
                        bot.send_message(uid, bt("رسالة_موافقة", uid))
                    except:
                        pass
                    notify_owners_action(uid, name, phone, "الشيت", "approve")
                    log_info(f"موافقة من الشيت على {name}", uid)
                elif new["ai"] and not old["ai"]:
                    try:
                        bot.send_message(uid, bt("رسالة_ai_تفعيل", uid))
                    except:
                        pass
                    notify_owners_action(uid, name, phone, "الشيت", "ai_enabled")
                elif not new["ai"] and old["ai"]:
                    try:
                        bot.send_message(uid, bt("رسالة_ai_تعطيل", uid))
                    except:
                        pass
                    notify_owners_action(uid, name, phone, "الشيت", "ai_disabled")
                elif old["owner"] and not new["owner"] and new["admin"]:
                    try:
                        bot.send_message(uid, "⬇️ تم تخفيض رتبتك من مالك إلى أدمن.")
                    except:
                        pass
                    notify_owners_action(uid, name, phone, "الشيت", "downgrade_owner")
                elif old["owner"] and not new["owner"] and new["allowed"] and not new["admin"]:
                    try:
                        bot.send_message(uid, "⬇️ تم تخفيض رتبتك من مالك إلى مستخدم عادي.")
                    except:
                        pass
                    notify_owners_action(uid, name, phone, "الشيت", "downgrade_owner_to_user")
                elif old["admin"] and not new["admin"] and new["allowed"] and not old["owner"]:
                    try:
                        bot.send_message(uid, "⬇️ تم تخفيض رتبتك من أدمن إلى مستخدم عادي.")
                    except:
                        pass
                    notify_owners_action(uid, name, phone, "الشيت", "downgrade_admin")
                elif not new["allowed"] and old["allowed"]:
                    try:
                        bot.send_message(uid, "⛔ تم إلغاء صلاحيتك.")
                    except:
                        pass
                    notify_owners_action(uid, name, phone, "الشيت", "remove")
            _users_snapshot = new_snap
        except:
            pass

# ─────────────────────────────────────────────────────
# دوال بطاقة المستخدم وعرض جميع المستخدمين
# ─────────────────────────────────────────────────────
def send_user_card(chat_id, row):
    name = row[0].strip() if row else ""
    uid_str = row[2].strip().lstrip("'") if len(row) > 2 else ""
    phone = row[1].strip() if len(row) > 1 else ""
    own = row[5].strip().upper() if len(row) > 5 else "FALSE"
    adm = row[4].strip().upper() if len(row) > 4 else "FALSE"
    allow_val = row[3].strip().upper() if len(row) > 3 else "FALSE"
    ai_val = row[AI_ALLOWED_COL].strip().upper() if len(row) > AI_ALLOWED_COL else "FALSE"
    if own == "TRUE":
        role_icon = "👑"
        role = "مالك"
    elif adm == "TRUE":
        role_icon = "⭐"
        role = "أدمن"
    elif allow_val == "TRUE":
        role_icon = "👤"
        role = "مستخدم"
    else:
        role_icon = "❌"
        role = "غير مصرح"
    ai_icon = "🤖" if ai_val == "TRUE" else "🚫"
    ph_line = f"\n📞 `{phone}`" if phone else ""
    text = f"{role_icon} *{name}*\n🆔 `{uid_str}`{ph_line}\n{ai_icon} AI: {'مفعل' if ai_val == 'TRUE' else 'معطل'}\n{'─' * 23}"
    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
    markup.row(
        telebot.types.InlineKeyboardButton("👑 مالك", callback_data=f"role_owner_{uid_str}"),
        telebot.types.InlineKeyboardButton("⭐ أدمن", callback_data=f"role_admin_{uid_str}"),
        telebot.types.InlineKeyboardButton("👤 مستخدم", callback_data=f"role_user_{uid_str}"),
    )
    markup.row(
        telebot.types.InlineKeyboardButton("🤖 تفعيل AI", callback_data=f"ai_on_{uid_str}"),
        telebot.types.InlineKeyboardButton("🚫 تعطيل AI", callback_data=f"ai_off_{uid_str}"),
    )
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

def format_all_users_message():
    try:
        rows = users_sheet.get_all_values()
        lines = ["👥 *قائمة جميع المستخدمين*\n" + "━" * 30 + "\n"]
        for row in rows[1:]:
            if len(row) < 3:
                continue
            uid_str = row[2].strip().lstrip("'")
            if not uid_str.isdigit():
                continue
            name = row[0].strip() or "مجهول"
            phone = row[1].strip() if len(row) > 1 else ""
            allowed = (row[3].strip().upper() if len(row) > 3 else "FALSE") == "TRUE"
            admin = (row[4].strip().upper() if len(row) > 4 else "FALSE") == "TRUE"
            owner = (row[5].strip().upper() if len(row) > 5 else "FALSE") == "TRUE"
            ai = (row[AI_ALLOWED_COL].strip().upper() if len(row) > AI_ALLOWED_COL else "FALSE") == "TRUE"
            if owner:
                role_icon = "👑"
                role = "مالك"
            elif admin:
                role_icon = "⭐"
                role = "أدمن"
            elif allowed:
                role_icon = "👤"
                role = "مستخدم"
            else:
                role_icon = "❌"
                role = "غير مصرح"
            ai_icon = "🤖" if ai else "🚫"
            phone_display = f"📞 {phone}" if phone else "📞 غير مسجل"
            lines.append(f"`{uid_str}` | {role_icon} {name} | {phone_display} | {role} | {ai_icon}")
        if len(lines) == 1:
            return "❌ لا يوجد مستخدمين مسجلين.", []
        return "\n".join(lines), rows[1:]
    except Exception as e:
        log_error(f"format_all_users_message: {e}")
        return "❌ حدث خطأ في قراءة بيانات المستخدمين.", []

def _execute_search(chat_id, uid):
    state = user_state.get(uid, {})
    df = state.get("date_filter")
    subjs = [v for v in state.get("sel_subjects", []) if v != "__all__"]
    types_f = [v for v in state.get("sel_types", []) if v != "__all__"]
    display_mode = state.get("display_mode", "subject")
    user_state.pop(uid, None)
    welcome, _ = get_settings()
    allowed, admins, owners, open_all, admin_all, _, _ = get_users()
    adm = admin_all or uid in admins
    own = uid in owners
    send_search_results(chat_id, uid, df, subjs, types_f, display_mode)
    bot.send_message(chat_id, welcome, reply_markup=main_menu(uid, admin=adm, owner=own))

# ─────────────────────────────────────────────────────
# دوال المعالجة الأخرى
# ─────────────────────────────────────────────────────
def auto_register_user(message, open_all=None):
    try:
        if open_all is None:
            _, _, _, open_all, _, _, _ = get_users()
        if not open_all:
            return
        uid_str = str(message.from_user.id)
        for row in users_sheet.get_all_values()[1:]:
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                return
        add_user_to_sheet(message.from_user.full_name or "مجهول", message.from_user.id, auto=True, allowed=False)
    except:
        pass

def calc_secret_code(uid):
    day = datetime.now(YEMEN_TZ).day
    total = sum(int(d) for d in str(uid)) + day
    return str(total)

def _do_broadcast(chat_id, uid, admin, owner, text_msg, files_data):
    uids, open_all = get_all_user_ids()
    if open_all:
        registered = get_all_registered_uids()
        if registered:
            uids = registered
    if not uids:
        bot.send_message(chat_id, "⚠️ لا يوجد مستخدمون.")
        return
    success = 0
    fail = 0
    for user_id in uids:
        try:
            if text_msg:
                bot.send_message(user_id, f"📢 *إشعار:*\n\n{text_msg}", parse_mode="Markdown")
            for fd in (files_data or []):
                _try_send_file(user_id, fd["file_id"])
            success += 1
        except:
            fail += 1
    bot.send_message(chat_id, f"✅ تم الإرسال!\n✅ {success} | ❌ {fail}", reply_markup=main_menu(uid, admin=admin, owner=owner))

def send_help_materials(chat_id, uid, audience_filter):
    mats = get_help_materials()
    mats = [m for m in mats if m["audience"] == audience_filter]
    if not mats:
        bot.send_message(chat_id, "📭 لا توجد تعليمات حالياً.")
        return
    title = ("📖 تعليمات المستخدم" if audience_filter == "user" else "📖 تعليمات الأدمن")
    bot.send_message(chat_id, f"*{title}*", parse_mode="Markdown")
    for m in mats:
        send_files_with_text(chat_id, m["note"] or None, [m["file_id"]] if m["file_id"] else [])

def get_help_materials():
    try:
        mats = []
        for row in help_sheet.get_all_values():
            if not row or not any(r.strip() for r in row):
                continue
            fid = row[1].strip() if len(row) > 1 else ""
            ftype = row[2].strip() if len(row) > 2 else ""
            aud = row[3].strip() if len(row) > 3 else "user"
            note = row[4].strip() if len(row) > 4 else ""
            if fid or note:
                mats.append({"file_id": fid, "file_type": ftype, "audience": aud, "note": note})
        return mats
    except:
        return []

def save_help_material(files_data, audience, note=""):
    try:
        rows = help_sheet.get_all_values()
        nrow = len(rows) + 1
        if note:
            help_sheet.update([[f"note_{nrow}", "", "", audience, note]], f"A{nrow}:E{nrow}")
            nrow += 1
        for fd in files_data:
            help_sheet.update([[f"file_{nrow}", fd["file_id"], fd["file_type"], audience, ""]], f"A{nrow}:E{nrow}")
            nrow += 1
        return True
    except Exception as e:
        log_error(f"save_help_material: {e}")
        return False

def _process_lecture_time(chat_id, uid, state, time_val, admin, owner):
    subj = state.get("subject", "")
    date = state.get("date", "")
    room = state.get("room", "")
    if time_val == "لا يوجد":
        if save_lecture(date, subj, time_val, room):
            mk = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            mk.add("➕ إضافة محاضرة أخرى", bt("زر_عوده", uid))
            user_state[uid]["step"] = "lecture_done"
            bot.send_message(chat_id, f"✅ تم الحفظ!\n📌 {subj}\n📅 {date}\n📍 {room}", reply_markup=mk)
        else:
            bot.send_message(chat_id, bt("رسالة_خطأ", uid))
            user_state.pop(uid, None)
        return
    conflict = check_lecture_conflict(date, time_val)
    if conflict:
        user_state[uid]["step"] = "confirm_lecture_overwrite"
        user_state[uid]["time_val"] = time_val
        mk2 = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        mk2.row("🔄 استبدال", bt("زر_عوده", uid))
        bot.send_message(chat_id,
                         f"⚠️ تداخل في الوقت!\n\n📌 {conflict['subject']}\n"
                         f"🕐 {conflict['time']}\n📍 {conflict['room']}\n\n"
                         f"الوقت `{time_val}` يتداخل معها.\nماذا تريد؟",
                         parse_mode="Markdown", reply_markup=mk2)
    else:
        if save_lecture(date, subj, time_val, room):
            mk3 = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            mk3.add("➕ إضافة محاضرة أخرى", bt("زر_عوده", uid))
            user_state[uid]["step"] = "lecture_done"
            user_state[uid]["time_val"] = time_val
            bot.send_message(chat_id,
                             f"✅ تم حفظ المحاضرة!\n📌 {subj}\n📅 {date}\n🕐 {time_val}\n📍 {room}",
                             reply_markup=mk3)
        else:
            bot.send_message(chat_id, bt("رسالة_خطأ", uid))
            user_state.pop(uid, None)

def check_lecture_conflict(date, time_val):
    try:
        ns, ne = parse_time_range(time_val)
        if ns is None:
            return None
        for row in get_data():
            rd = parse_date(safe_get(row, 0))
            rt = safe_get(row, 2)
            if rd != date or not rt:
                continue
            es2, ee2 = parse_time_range(rt)
            if es2 is None:
                continue
            if ns < ee2 and es2 < ne:
                return {"subject": safe_get(row, 1),
                        "room": safe_get(row, 3),
                        "time": normalize_time(rt)}
    except:
        pass
    return None

def normalize_time(t):
    t = t.strip().replace("–", "-").replace("—", "-")
    t = re.sub(r'\s*-\s*', ' - ', t)

    def pad(m):
        return f"{int(m.group(1)):02d}:{m.group(2)}"

    return re.sub(r'(\d{1,2}):(\d{2})', pad, t)

def parse_time_range(t):
    t = normalize_time(t)
    parts = re.split(r'\s*-\s*', t)
    if len(parts) != 2:
        return None, None

    def mins(s):
        s = s.strip()
        h, mm = s.split(":") if ":" in s else (s, "0")
        return int(h) * 60 + int(mm)

    try:
        return mins(parts[0]), mins(parts[1])
    except:
        return None, None

def build_multiselect_kb(items, selected, prefix):
    keyboard = []
    row = []
    for label, value in items:
        lbl = f"✅ {label}" if value in selected else label
        row.append(telebot.types.InlineKeyboardButton(lbl, callback_data=f"{prefix}:{value}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    all_lbl = f"✅ {bt('زر_تحديد_الكل')}" if "__all__" in selected else bt("زر_تحديد_الكل")
    done_lbl = bt("زر_تم_التحديد")
    if row:
        row.append(telebot.types.InlineKeyboardButton(all_lbl, callback_data=f"{prefix}:__all__"))
        keyboard.append(row)
        keyboard.append([telebot.types.InlineKeyboardButton(done_lbl, callback_data=f"{prefix}:__done__")])
    else:
        keyboard.append([
            telebot.types.InlineKeyboardButton(all_lbl, callback_data=f"{prefix}:__all__"),
            telebot.types.InlineKeyboardButton(done_lbl, callback_data=f"{prefix}:__done__"),
        ])
    return telebot.types.InlineKeyboardMarkup(keyboard)

def parse_smart_date(raw):
    text = normalize_digits(raw.strip())
    if is_valid_date(text):
        return parse_date(text)
    if text.isdigit():
        d = int(text)
        if 1 <= d <= 31:
            return smart_date_from_day(d)
    return None

def smart_date_from_day(day):
    now = datetime.now(YEMEN_TZ)
    if day <= now.day:
        try:
            return now.replace(day=day).strftime("%d/%m/%Y")
        except:
            return now.strftime("%d/%m/%Y")
    else:
        first = now.replace(day=1)
        last_m = first - timedelta(days=1)
        try:
            return last_m.replace(day=day).strftime("%d/%m/%Y")
        except:
            return now.strftime("%d/%m/%Y")

def parse_date_range(raw):
    text = normalize_digits(raw.strip())
    m = re.match(r'(\d{1,2}/\d{1,2}/\d{4})\s*[-–]\s*(\d{1,2}/\d{1,2}/\d{4})', text)
    if m and is_valid_date(m.group(1)) and is_valid_date(m.group(2)):
        return parse_date(m.group(1)), parse_date(m.group(2))
    m2 = re.match(r'^(\d{1,2})[-–](\d{1,2})$', text)
    if m2:
        return smart_date_from_day(int(m2.group(1))), smart_date_from_day(int(m2.group(2)))
    return None, None

def save_file_to_cell(date, subject, col, fids, merge=False):
    try:
        fids = fids if isinstance(fids, list) else [fids]
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) and parse_date(safe_get(row, 0)) == date and safe_get(row, 1) == subject:
                current = safe_get(row, col)
                all_fids = (get_file_ids(current) + fids) if merge else fids
                sheet.update_cell(i, col + 1, merge_cell(get_text(current), all_fids))
                return True
        new_row = [""] * 8
        new_row[0] = date
        new_row[1] = subject
        new_row[col] = f"|{','.join(fids)}"
        sheet.append_row(new_row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        log_error(f"save_file_to_cell: {e}")
        return False

def merge_cell(text, fids):
    if not fids:
        return text
    fids_str = ",".join(fids) if isinstance(fids, list) else fids
    return f"{text}|{fids_str}" if fids_str else text

def normalize_digits(text):
    return text.translate(ARABIC_DIGITS)

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def is_pending(uid):
    if uid in pending_requests:
        return True
    try:
        uid_str = str(uid)
        es = 0
        for row in users_sheet.get_all_values()[1:]:
            if not row or not any(c.strip() for c in row):
                es += 1
                if es >= 5:
                    break
                continue
            es = 0
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                return True
    except:
        pass
    return False

# ─────────────────────────────────────────────────────
# دوال اللوج
# ─────────────────────────────────────────────────────
def tg_log(level, msg, uid=None):
    icons = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🚨"}
    now = datetime.now(YEMEN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    if uid:
        name, phone = _get_user_name_phone(uid)
        role_icon = _get_role_icon(uid)
        ph_line = f"\n📞 {phone}" if phone else ""
        user_block = f"{role_icon} {name}\n🆔 `{uid}`{ph_line}\n\n"
    else:
        user_block = ""
    text = f"{icons.get(level, '📋')} *{level}*\n`{now}`\n\n{user_block}{msg}"
    if LOG_BOT_TOKEN and users_sheet:
        try:
            es = 0
            for row in users_sheet.get_all_values()[1:]:
                if not row or not any(c.strip() for c in row):
                    es += 1
                    if es >= 5:
                        break
                    continue
                es = 0
                uid_str = row[2].strip().lstrip("'") if len(row) > 2 else ""
                if uid_str.isdigit() and (row[7].strip().upper() if len(row) > 7 else "") == "TRUE":
                    try:
                        _requests.post(
                            f"https://api.telegram.org/bot{LOG_BOT_TOKEN}/sendMessage",
                            json={"chat_id": int(uid_str), "text": text, "parse_mode": "Markdown"},
                            timeout=5)
                    except:
                        pass
        except:
            pass
    getattr(logger, level.lower(), logger.info)(msg)

def log_info(m, uid=None):
    tg_log("INFO", m, uid)

def log_warning(m, uid=None):
    tg_log("WARNING", m, uid)

def log_error(m, uid=None):
    tg_log("ERROR", m, uid)

def log_critical(m, uid=None):
    tg_log("CRITICAL", m, uid)

# ─────────────────────────────────────────────────────
# معالجات الأوامر والرسائل
# ─────────────────────────────────────────────────────
@bot.message_handler(commands=['start'])
def start_message(message):
    uid = message.from_user.id
    load_user_lang(uid)
    welcome, rejection = get_settings()
    allowed, admins, owners, open_all, admin_all, _, _ = get_users()
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
    log_info("START", uid)
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin, owner=owner))

@bot.message_handler(commands=['ai'])
def ai_command(message):
    uid = message.from_user.id
    if not OPENROUTER_API_KEY:
        bot.send_message(message.chat.id, bt("رسالة_ai_غير_مفعل", uid))
        return
    if not is_ai_allowed(uid):
        bot.send_message(message.chat.id, bt("رسالة_ai_غير_مسموح", uid))
        return
    user_ai_enabled[uid] = True
    m = _ai_model()
    bot.send_message(
        message.chat.id,
        bt("رسالة_ai_ترحيب", uid).format(model=f"{m['icon']} {m['name']}"),
        parse_mode="Markdown",
        reply_markup=main_menu(uid)
    )

@bot.message_handler(commands=['ai_reset'])
def ai_reset_command(message):
    uid = message.from_user.id
    if not is_owner_id(uid):
        bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط", uid))
        return
    ai_reset_model()
    m = _ai_model()
    bot.send_message(message.chat.id, f"✅ تمت إعادة تعيين النموذج إلى {m['icon']} *{m['name']}*", parse_mode="Markdown")

@bot.message_handler(commands=['ai_clear'])
def ai_clear_command(message):
    uid = message.from_user.id
    _ai_histories.pop(uid, None)
    bot.send_message(message.chat.id, "✅ تم مسح سياق المحادثة.")

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
    allowed, _, _, open_all, _, _, _ = get_users()
    if not (open_all or uid in allowed):
        bot.send_message(message.chat.id, rejection)
        return
    user_state[uid] = {"choosing_lang": True}
    bot.send_message(message.chat.id, bt("رسالة_تغيير_اللغة", uid), reply_markup=lang_menu(uid))

@bot.message_handler(commands=['help'])
def help_message(message):
    uid = message.from_user.id
    load_user_lang(uid)
    _, admins, owners, _, admin_all, _, _ = get_users()
    admin = admin_all or uid in admins
    owner = uid in owners
    if admin or owner:
        user_state[uid] = {"viewing_help": True}
        bot.send_message(message.chat.id, "اختر:", reply_markup=help_view_menu(uid))
    else:
        send_help_materials(message.chat.id, uid, "user")

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    uid = message.from_user.id
    phone = message.contact.phone_number if message.contact else ""
    name = message.from_user.full_name or "مجهول"
    try:
        rows = users_sheet.get_all_values()
        uid_str = str(uid)
        found = False
        es = 0
        for i, row in enumerate(rows[1:], start=2):
            if not row or not any(c.strip() for c in row):
                es += 1
                if es >= 5:
                    break
                continue
            es = 0
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                users_sheet.update(f"A{i}:B{i}", [[name, phone]])
                found = True
                break
        if not found:
            users_sheet.append_row([name, phone, uid, False, False, False, False, False, False],
                                    value_input_option="USER_ENTERED")
    except Exception as e:
        log_error(f"handle_contact: {e}")
    notify_owners_new_request(uid, name, phone)
    bot.send_message(message.chat.id, bt("رسالة_شكر_اتصال", uid), reply_markup=telebot.types.ReplyKeyboardRemove())

@bot.message_handler(content_types=['document', 'photo', 'video', 'audio', 'voice'])
def handle_file(message):
    uid = message.from_user.id
    load_user_lang(uid)
    _, rejection = get_settings()
    allowed, admins, owners, open_all, admin_all, _, _ = get_users()
    if not (open_all or uid in allowed):
        bot.send_message(message.chat.id, rejection)
        return
    auto_register_user(message, open_all=open_all)
    f_admin = admin_all or uid in admins
    f_owner = uid in owners
    state = user_state.get(uid, {})

    if message.document:
        file_id, ftype = message.document.file_id, "document"
    elif message.photo:
        file_id, ftype = message.photo[-1].file_id, "photo"
    elif message.video:
        file_id, ftype = message.video.file_id, "video"
    elif message.audio:
        file_id, ftype = message.audio.file_id, "audio"
    elif message.voice:
        file_id, ftype = message.voice.file_id, "voice"
    else:
        return

    def _reset_timer(key, fn):
        t_old = user_state.get(uid, {}).get("_timer")
        if t_old:
            try:
                t_old.cancel()
            except:
                pass
        t = threading.Timer(3.0, fn)
        user_state[uid]["_timer"] = t
        t.start()

    if state.get("uploading") and state.get("step") in ("waiting_files", "confirm_files"):
        if not (f_admin or f_owner):
            bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط", uid))
            return
        user_state[uid]["step"] = "waiting_files"
        user_state[uid].setdefault("pending_files", []).append({"file_id": file_id, "file_type": ftype})

        def _finish_upload():
            st = user_state.get(uid, {})
            if st.get("step") == "waiting_files":
                user_state[uid]["step"] = "confirm_files"
                n = len(st.get("pending_files", []))
                bot.send_message(message.chat.id, f"📎 تم استلام {n} ملف.\nأرسل المزيد أو اضغط *إرسال*:",
                                 parse_mode="Markdown", reply_markup=upload_confirm_menu(uid))

        _reset_timer("uploading", _finish_upload)
        return

    if state.get("requesting_upload") and state.get("step") in ("waiting_files_req", "confirm_req"):
        user_state[uid]["step"] = "waiting_files_req"
        user_state[uid].setdefault("pending_files", []).append({"file_id": file_id, "file_type": ftype})

        def _finish_req():
            st = user_state.get(uid, {})
            if st.get("step") == "waiting_files_req":
                user_state[uid]["step"] = "confirm_req"
                n = len(st.get("pending_files", []))
                bot.send_message(message.chat.id, f"📎 تم استلام {n} ملف.\nاضغط *إرسال* لإرسال الطلب:",
                                 parse_mode="Markdown", reply_markup=upload_confirm_menu(uid))

        _reset_timer("requesting_upload", _finish_req)
        return

    if state.get("uploading_help") and state.get("step") == "waiting_file_help":
        if not (f_admin or f_owner):
            bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط", uid))
            return
        user_state[uid].setdefault("pending_files", []).append({"file_id": file_id, "file_type": ftype})

        def _finish_help():
            st = user_state.get(uid, {})
            if st.get("step") == "waiting_file_help":
                files = st.get("pending_files", [])
                audience = st.get("audience", "user")
                note = st.get("note", "")
                if save_help_material(files, audience, note):
                    bot.send_message(message.chat.id, "✅ تم الحفظ!", reply_markup=main_menu(uid, admin=f_admin, owner=f_owner))
                else:
                    bot.send_message(message.chat.id, bt("رسالة_خطأ", uid))
                user_state.pop(uid, None)

        _reset_timer("uploading_help", _finish_help)
        return

    if state.get("broadcasting") and state.get("step") == "waiting_file_or_send":
        if not (f_admin or f_owner):
            bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط", uid))
            return
        user_state[uid].setdefault("broadcast_files", []).append({"file_id": file_id, "file_type": ftype})
        return

    if not (f_admin or f_owner):
        bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط", uid))
        return
    bot.send_message(message.chat.id, "📤 لرفع ملف اضغط *رفع ملف* أولاً.", parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    uid = message.from_user.id
    load_user_lang(uid)
    welcome, rejection = get_settings()
    allowed, admins, owners, open_all, admin_all, _, _ = get_users()
    is_allowed = open_all or uid in allowed
    admin = admin_all or uid in admins
    owner = uid in owners
    text = (message.text or "").strip()
    state = user_state.get(uid, {})
    back_btn = bt("زر_عوده", uid)

    # معالجة التسجيلات الصوتية
    if message.content_type == 'voice':
        if user_ai_enabled.get(uid, False) and is_ai_allowed(uid):
            bot.send_chat_action(message.chat.id, "typing")
            transcribed = transcribe_voice(message.voice.file_id, lang="ar")
            if transcribed:
                text = transcribed
            else:
                bot.send_message(message.chat.id, "❌ لم أستطع فهم التسجيل الصوتي.")
                return
        else:
            return

    # معالجة الأزرار (تكون أولوية)
    if text in BUTTON_TEXTS:
        # لا نخرج من وضع AI، فقط نتعامل مع الزر بالطريقة العادية
        pass
    # معالجة AI (إذا كان مفعلاً)
    elif user_ai_enabled.get(uid, False) and is_ai_allowed(uid):
        user_role = get_user_role(uid)
        executed, cmd_response = try_execute_admin_command(text, uid, user_role, message.chat.id, bot)
        if executed:
            bot.send_message(message.chat.id, cmd_response, reply_markup=main_menu(uid, admin=admin, owner=owner))
            return

        bot.send_chat_action(message.chat.id, "typing")

        def _notify(msg):
            if admin or owner:
                bot.send_message(message.chat.id, msg, parse_mode="Markdown")

        response, used_model = ask_ai(uid, text, user_role=user_role, notify_fn=_notify, send_notify=(owner or admin))
        if response:
            model_line = f"\n\n_{used_model['icon']} {used_model['name']}_"
            bot.send_message(message.chat.id, response + model_line, parse_mode="Markdown",
                             reply_markup=main_menu(uid, admin=admin, owner=owner))
        else:
            bot.send_message(message.chat.id, bt("رسالة_ai_فشل", uid),
                             reply_markup=main_menu(uid, admin=admin, owner=owner))
        return

    # ========== باقي معالجة البوت العادي ==========
    if state.get("choosing_lang") or text in ["🇾🇪 العربية", "🇬🇧 English"]:
        if text == "🇾🇪 العربية":
            user_lang[uid] = "ar"
        elif text == "🇬🇧 English":
            user_lang[uid] = "en"
        else:
            bot.send_message(message.chat.id, bt("رسالة_تغيير_اللغة", uid), reply_markup=lang_menu(uid))
            return
        user_state.pop(uid, None)
        save_user_lang_to_sheet(uid, user_lang[uid])
        bot.send_message(message.chat.id, bt("رسالة_تم_تغيير_اللغة", uid), reply_markup=telebot.types.ReplyKeyboardRemove())
        return

    if not is_allowed:
        code = calc_secret_code(uid)
        _code_input = normalize_digits(text).strip()
        if _code_input == code and _code_input.isdigit():
            try:
                uid_str = str(uid)
                rows = users_sheet.get_all_values()
                found = False
                es = 0
                for i, row in enumerate(rows[1:], start=2):
                    if not row or not any(c.strip() for c in row):
                        es += 1
                        if es >= 5:
                            break
                        continue
                    es = 0
                    if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                        users_sheet.update_cell(i, 4, True)
                        found = True
                        break
                if not found:
                    add_user_to_sheet(message.from_user.full_name or "مجهول", uid)
                pending_requests.discard(uid)
                uid_str_snap = str(uid)
                if uid_str_snap in _users_snapshot:
                    _users_snapshot[uid_str_snap]["allowed"] = True
                bot.send_message(message.chat.id, bt("رسالة_موافقة", uid), reply_markup=telebot.types.ReplyKeyboardRemove())
                notify_owners_action(uid, message.from_user.full_name or "مجهول", "", "الكود السري", "approve")
                log_info(f"كود سري صحيح", uid)
            except Exception as e:
                log_error(f"secret_code activate: {e}")
                bot.send_message(message.chat.id, bt("رسالة_خطأ", uid))
            return
        if not is_pending(uid):
            pending_requests.add(uid)
        bot.send_message(message.chat.id, rejection)
        cm = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        cm.add(telebot.types.KeyboardButton("📱 مشاركة جهة الاتصال", request_contact=True))
        bot.send_message(message.chat.id, "📲 شارك جهة اتصالك:", reply_markup=cm)
        return

    if sheet is None:
        bot.send_message(message.chat.id, "❌ لا يوجد اتصال بقاعدة البيانات.")
        return

    auto_register_user(message, open_all=open_all)

    try:
        subjects_kb, subjects_list = subjects_menu_kb(uid)
        data = get_data()

        # زر المساعد الذكي (سويتش)
        ai_button_text = f"🤖 {bt('زر_مساعد_نايف', uid)}"
        if text in [f"🟢 {ai_button_text}", f"🔴 {ai_button_text}", ai_button_text]:
            if not OPENROUTER_API_KEY:
                bot.send_message(message.chat.id, bt("رسالة_ai_غير_مفعل", uid))
                return
            if not is_ai_allowed(uid):
                bot.send_message(message.chat.id, bt("رسالة_ai_غير_مسموح", uid))
                return
            current = user_ai_enabled.get(uid, False)
            user_ai_enabled[uid] = not current
            if user_ai_enabled[uid]:
                bot.send_message(
                    message.chat.id,
                    f"✅ تم تفعيل {ai_button_text}!\n\n"
                    "الآن كل رسائلك النصية والتسجيلات الصوتية سترسل للذكاء الاصطناعي.\n"
                    "الأزرار لا تزال تعمل بشكل طبيعي.\n\n"
                    "لإيقاف المساعد، اضغط على الزر مرة أخرى.",
                    reply_markup=main_menu(uid, admin=admin, owner=owner)
                )
            else:
                bot.send_message(
                    message.chat.id,
                    f"❌ تم إيقاف {ai_button_text}.",
                    reply_markup=main_menu(uid, admin=admin, owner=owner)
                )
            return

        # زر العودة
        if text == back_btn:
            if state.get("date_search"):
                step = state.get("step", "")
                if step == "choose_date_input":
                    user_state.pop(uid, None)
                    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin, owner=owner))
                elif step == "choose_subjects":
                    user_state[uid]["step"] = "choose_date_input"
                    bot.send_message(message.chat.id, "📅 أدخل التاريخ أو الفترة:", reply_markup=back_only_menu(uid))
                elif step == "choose_type":
                    user_state[uid]["step"] = "choose_subjects"
                    subjects = get_subjects()
                    sel = set(state.get("sel_subjects", []))
                    kb = build_multiselect_kb([(s, s) for s in subjects], sel, "ms_subj")
                    bot.send_message(message.chat.id, "📚 اختر المواد:", reply_markup=kb)
                elif step == "choose_display":
                    user_state[uid]["step"] = "choose_type"
                    items2 = [("محاضرات", "محاضرات"), ("تكاليف", "تكاليف"), ("ملخصات", "ملخصات")]
                    sel2 = set(state.get("sel_types", []))
                    kb2 = build_multiselect_kb(items2, sel2, "ms_type")
                    bot.send_message(message.chat.id, "📋 اختر المطلوب:", reply_markup=kb2)
                else:
                    user_state.pop(uid, None)
                    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin, owner=owner))
                return
            if state.get("uploading") or state.get("uploading_help") or state.get("requesting_upload") or state.get("broadcasting") or state.get("adding_data") or state.get("editing_data") or state.get("managing_users") or state.get("viewing_help"):
                user_state.pop(uid, None)
                bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin, owner=owner))
                return
            user_state.pop(uid, None)
            bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin, owner=owner))
            return

        # تعليمات
        if state.get("viewing_help"):
            if text == "👤 تعليمات المستخدم":
                send_help_materials(message.chat.id, uid, "user")
            elif text == "👑 تعليمات الأدمن":
                send_help_materials(message.chat.id, uid, "admin")
            else:
                bot.send_message(message.chat.id, "اختر:", reply_markup=help_view_menu(uid))
                return
            user_state.pop(uid, None)
            bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin, owner=owner))
            return

        # البحث بالتاريخ
        if text == bt("زر_التاريخ", uid):
            user_state[uid] = {"date_search": True, "step": "choose_date_type"}
            bot.send_message(message.chat.id, "📅 اختر نوع البحث:", reply_markup=date_type_menu(uid))
            return

        if state.get("date_search"):
            step = state.get("step", "")
            if step == "choose_date_type":
                if text == bt("زر_يوم", uid):
                    user_state[uid]["search_mode"] = "day"
                    user_state[uid]["step"] = "choose_date_input"
                    bot.send_message(message.chat.id, "📅 أدخل اليوم (مثال: 27) أو التاريخ كاملاً (27/02/2026):", reply_markup=back_only_menu(uid))
                elif text == bt("زر_فتره", uid):
                    user_state[uid]["search_mode"] = "range"
                    user_state[uid]["step"] = "choose_date_input"
                    bot.send_message(message.chat.id, "📅 أدخل الفترة:\nمثال: 15-27\nأو تاريخين: 01/02/2026-28/02/2026", reply_markup=back_only_menu(uid))
                return
            if step == "choose_date_input":
                mode = state.get("search_mode", "day")
                if mode == "day":
                    d = parse_smart_date(text)
                    if not d:
                        bot.send_message(message.chat.id, "❌ صيغة غير صحيحة.\nمثال: 27 أو 27/02/2026")
                        return
                    user_state[uid]["date_filter"] = d
                else:
                    d1, d2 = parse_date_range(text)
                    if not d1:
                        bot.send_message(message.chat.id, "❌ صيغة غير صحيحة.\nمثال: 15-27")
                        return
                    user_state[uid]["date_filter"] = (d1, d2)
                user_state[uid]["step"] = "choose_subjects"
                subjects = get_subjects()
                kb = build_multiselect_kb([(s, s) for s in subjects], set(), "ms_subj")
                bot.send_message(message.chat.id, "📚 اختر المواد:", reply_markup=kb)
                return
            if step == "choose_display":
                if text == bt("زر_حسب_الماده", uid):
                    user_state[uid]["display_mode"] = "subject"
                elif text == bt("زر_حسب_التاريخ", uid):
                    user_state[uid]["display_mode"] = "date"
                else:
                    bot.send_message(message.chat.id, "📊 اختر طريقة العرض:", reply_markup=display_mode_menu(uid))
                    return
                _execute_search(message.chat.id, uid)
            return

        # المواد
        if text == bt("زر_المواد", uid):
            user_state.pop(uid, None)
            bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=subjects_kb)
            return

        _free = not state or set(state.keys()) <= {"subject"}
        if _free and text in subjects_list:
            user_state[uid] = {"subject": text}
            bot.send_message(message.chat.id, f"📌 *{text}*\nماذا تحتاج؟", parse_mode="Markdown", reply_markup=subject_options_menu(uid))
            return

        SUBJ_OPTS = [bt(k, uid) for k in ["خيار_الجدول", "خيار_التكاليف", "خيار_السعر", "خيار_الملخص", "خيار_التنبيهات"]]
        if _free and state.get("subject") and text in SUBJ_OPTS:
            subj = state["subject"]
            rows_s = [r for r in data if safe_get(r, 1) == subj]
            if text == bt("خيار_السعر", uid):
                price = next((get_text(safe_get(r, 5)) for r in rows_s if safe_get(r, 5)), None)
                msg2 = (f"💰 *{subj}*: {price}" if price else f"لا يوجد سعر لـ *{subj}*")
                bot.send_message(message.chat.id, msg2, parse_mode="Markdown", reply_markup=subject_options_menu(uid))
                return
            col_map3 = {bt("خيار_الجدول", uid): 2, bt("خيار_التكاليف", uid): 4, bt("خيار_الملخص", uid): 6, bt("خيار_التنبيهات", uid): 7}
            col = col_map3.get(text, 2)
            dates = list(dict.fromkeys(
                parse_date(safe_get(r, 0)) for r in rows_s
                if (get_text(safe_get(r, col)) or get_file_ids(safe_get(r, col))) and safe_get(r, 0)))
            if not dates:
                no_map = {bt("خيار_الجدول", uid): "لا توجد محاضرات", bt("خيار_التكاليف", uid): "لا توجد تكاليف",
                          bt("خيار_الملخص", uid): "لا توجد ملخصات", bt("خيار_التنبيهات", uid): "لا توجد تنبيهات"}
                bot.send_message(message.chat.id, f"{no_map.get(text, 'لا توجد بيانات')} لـ *{subj}*",
                                 parse_mode="Markdown", reply_markup=subject_options_menu(uid))
                return
            user_state[uid] = {"subject": subj, "action": text, "awaiting_date": True, "col": col, "dates": dates}
            bot.send_message(message.chat.id, "📅 اختر التاريخ:", reply_markup=dates_menu_kb(dates, uid))
            return

        if state.get("awaiting_date"):
            subj = state["subject"]
            col = state["col"]
            dates = state.get("dates", [])
            matched = [r for r in data if safe_get(r, 1) == subj and parse_date(safe_get(r, 0)) == text]
            if not matched:
                bot.send_message(message.chat.id, bt("رسالة_لا_بيانات", uid), reply_markup=dates_menu_kb(dates, uid))
                return
            day = get_day_name(text, uid)
            d_ar = format_date_ar(text)
            day_str = f" ({day})" if day else ""
            header = f"*{subj}* — {d_ar}{day_str}\n{'─' * 25}\n"
            all_text = header
            all_fids = []
            for row in matched:
                cell = safe_get(row, col)
                val = get_text(cell)
                fids = get_file_ids(cell)
                col_icon = {2: "🕐", 4: "📝", 6: "📖", 7: "⚠️"}.get(col, "")
                if val:
                    all_text += f"{col_icon} {val}\n"
                all_fids.extend(fids)
            send_files_with_text(message.chat.id, all_text, all_fids, reply_markup=dates_menu_kb(dates, uid))
            return

        # أزرار القائمة الرئيسية
        if text == bt("زر_التكاليف", uid):
            ld = get_last_date(data, 4)
            if not ld:
                bot.send_message(message.chat.id, "📭 لا توجد تكاليف.", reply_markup=main_menu(uid, admin=admin, owner=owner))
                return
            rows_s = [r for r in data if parse_date(safe_get(r, 0)) == ld and (get_text(safe_get(r, 4)) or get_file_ids(safe_get(r, 4)))]
            day = get_day_name(ld, uid)
            d_ar = format_date_ar(ld)
            header = f"📝 *{d_ar} — {day}*\n{'─' * 25}\n"
            all_fids = []
            for row in rows_s:
                cell = safe_get(row, 4)
                tx = get_text(cell)
                fids = get_file_ids(cell)
                subj_n = safe_get(row, 1)
                if tx:
                    header += f"📌 {subj_n}: {tx}\n"
                elif fids:
                    header += f"📌 {subj_n}: 📎 ملف\n"
                all_fids.extend(fids)
            send_files_with_text(message.chat.id, header, all_fids, reply_markup=main_menu(uid, admin=admin, owner=owner))
            return

        if text == bt("زر_الجدول", uid):
            ld = get_last_date(data, 2)
            if not ld:
                bot.send_message(message.chat.id, "📭 لا توجد محاضرات.", reply_markup=main_menu(uid, admin=admin, owner=owner))
                return
            rows_s = [r for r in data if parse_date(safe_get(r, 0)) == ld and get_text(safe_get(r, 2))]
            day = get_day_name(ld, uid)
            d_ar = format_date_ar(ld)
            resp = f"🕐 *{d_ar} — {day}:*\n{'─' * 25}\n"
            for r in rows_s:
                resp += f"📌 {safe_get(r, 1)}: {get_text(safe_get(r, 2))}\n"
            bot.send_message(message.chat.id, resp, parse_mode="Markdown", reply_markup=main_menu(uid, admin=admin, owner=owner))
            return

        if text == bt("زر_الملخصات", uid):
            ld = get_last_date(data, 6)
            if not ld:
                bot.send_message(message.chat.id, "📭 لا توجد ملخصات.", reply_markup=main_menu(uid, admin=admin, owner=owner))
                return
            rows_s = [r for r in data if parse_date(safe_get(r, 0)) == ld and (get_text(safe_get(r, 6)) or get_file_ids(safe_get(r, 6)))]
            day = get_day_name(ld, uid)
            d_ar = format_date_ar(ld)
            header = f"📖 *{d_ar} — {day}*\n{'─' * 25}\n"
            all_fids = []
            for row in rows_s:
                cell = safe_get(row, 6)
                tx = get_text(cell)
                fids = get_file_ids(cell)
                subj_n = safe_get(row, 1)
                if tx:
                    header += f"📌 {subj_n}: {tx}\n"
                elif fids:
                    header += f"📌 {subj_n}: 📎 ملف\n"
                all_fids.extend(fids)
            send_files_with_text(message.chat.id, header, all_fids, reply_markup=main_menu(uid, admin=admin, owner=owner))
            return

        if text == bt("زر_الاسعار", uid):
            seen = {}
            for r in data:
                s = safe_get(r, 1)
                p = get_text(safe_get(r, 5))
                if s and p and s not in seen:
                    seen[s] = p
            if not seen:
                bot.send_message(message.chat.id, "📭 لا توجد أسعار.", reply_markup=main_menu(uid, admin=admin, owner=owner))
                return
            mx = max(len(s) for s in seen.keys())
            lines = "".join(f"📖 {s:<{mx}} : {p}\n" for s, p in seen.items())
            bot.send_message(message.chat.id, f"💰 *أسعار الملازم:*\n```\n{lines}```",
                             parse_mode="Markdown", reply_markup=main_menu(uid, admin=admin, owner=owner))
            return

        if text == bt("زر_التنبيهات", uid):
            alerts = [(safe_get(r, 1), parse_date(safe_get(r, 0)), get_text(safe_get(r, 7))) for r in data if get_text(safe_get(r, 7))]
            if not alerts:
                bot.send_message(message.chat.id, "✅ لا توجد تنبيهات.", reply_markup=main_menu(uid, admin=admin, owner=owner))
                return
            resp = "*⚠️ التنبيهات:*\n" + "─" * 25 + "\n"
            for s, d, a in alerts:
                d_ar = format_date_ar(d)
                resp += f"🔔 {s} ({d_ar}):\n{a}\n\n"
            bot.send_message(message.chat.id, resp, parse_mode="Markdown", reply_markup=main_menu(uid, admin=admin, owner=owner))
            return

        # طلب رفع ملف (مستخدم)
        if text == bt("زر_طلب_رفع", uid):
            user_state[uid] = {"requesting_upload": True, "step": "choose_subject"}
            bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=subjects_kb)
            return

        if state.get("requesting_upload"):
            step = state.get("step", "")
            if step == "choose_subject" and text in subjects_list:
                user_state[uid]["subject"] = text
                user_state[uid]["step"] = "choose_type"
                bot.send_message(message.chat.id, f"📌 *{text}*\nاختر النوع:", parse_mode="Markdown", reply_markup=file_type_menu(uid))
                return
            if step == "choose_type":
                if text == bt("زر_اضافة_تكليف", uid):
                    user_state[uid]["col"] = 4
                elif text == bt("زر_اضافة_ملخص", uid):
                    user_state[uid]["col"] = 6
                else:
                    return
                user_state[uid]["step"] = "choose_date"
                subj = state.get("subject", "")
                bot.send_message(message.chat.id, "📅 أدخل التاريخ:", reply_markup=back_only_menu(uid))
                send_date_suggestions(message.chat.id, subject=subj, uid=uid)
                return
            if step == "choose_date":
                d = parse_smart_date(text)
                if not d:
                    bot.send_message(message.chat.id, "❌ صيغة غير صحيحة.\nمثال: `27/02/2026`", parse_mode="Markdown")
                    return
                user_state[uid]["date"] = d
                user_state[uid]["step"] = "waiting_files_req"
                bot.send_message(message.chat.id, "📎 أرسل الملف أو الملفات:", reply_markup=back_only_menu(uid))
                return
            if step == "confirm_req":
                if text == "✅ إرسال":
                    files = state.get("pending_files", [])
                    col = state.get("col", 4)
                    subj = state.get("subject", "")
                    date = state.get("date", "")
                    req_uid = uid
                    if not files:
                        bot.send_message(message.chat.id, "⚠️ لم يتم استلام أي ملف.")
                        return
                    _, admins2, owners2, _, admin_all2, _, _ = get_users()
                    targets = list(set(admins2 + owners2))
                    col_label = "تكليف" if col == 4 else "ملخص"
                    for fdata in files:
                        fid = fdata["file_id"]
                        _file_req_counter[0] += 1
                        short_key = str(_file_req_counter[0])
                        _file_req_store[short_key] = {"req_uid": req_uid, "date": date, "subj": subj, "col": col, "fid": fid}
                        mk_req = telebot.types.InlineKeyboardMarkup()
                        mk_req.row(
                            telebot.types.InlineKeyboardButton("✅ قبول", callback_data=f"file_req:approve:{short_key}"),
                            telebot.types.InlineKeyboardButton("❌ رفض", callback_data=f"file_req:reject:{short_key}")
                        )
                        caption = (f"📨 طلب رفع {col_label}\n👤 من: {message.from_user.full_name}\n📌 {subj} | 📅 {date}")
                        for tid in targets:
                            try:
                                _try_send_file(tid, fid, caption=caption)
                                bot.send_message(tid, "👆 اختر:", reply_markup=mk_req)
                            except:
                                pass
                    bot.send_message(message.chat.id, "✅ تم إرسال الطلب! سيتم إخبارك بالنتيجة.", reply_markup=main_menu(uid, admin=admin, owner=owner))
                    user_state.pop(uid, None)
                return
            return

        # إدارة المستخدمين
        if text == bt("زر_المستخدمين", uid):
            if not owner:
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط", uid))
                return
            user_state[uid] = {"managing_users": True, "step": "menu"}
            rows_all = users_sheet.get_all_values()
            entries = []
            es = 0
            for row in rows_all[1:]:
                if not row or not any(c.strip() for c in row):
                    es += 1
                    if es >= 5:
                        break
                    continue
                es = 0
                name = row[0].strip()
                uid_str = row[2].strip().lstrip("'") if len(row) > 2 else ""
                own_v = row[5].strip().upper() if len(row) > 5 else "FALSE"
                adm_v = row[4].strip().upper() if len(row) > 4 else "FALSE"
                if not name or name == "الكل" or not uid_str:
                    continue
                entries.append((name, uid_str, own_v, adm_v, row))
            entries.sort(key=lambda x: (0 if x[2] == "TRUE" else 1 if x[3] == "TRUE" else 2))
            bot.send_message(message.chat.id, "👥 *قائمة المستخدمين:*\n" + "─" * 25, parse_mode="Markdown", reply_markup=manage_users_menu(uid))
            for _, _, _, _, row in entries:
                send_user_card(message.chat.id, row)
            return

        if state.get("managing_users"):
            step = state.get("step", "menu")
            if step == "menu":
                if text == "🔍 بحث بالID":
                    user_state[uid]["step"] = "search_id"
                    bot.send_message(message.chat.id, "🔍 أدخل الـ ID:", reply_markup=back_only_menu(uid))
                elif text == "🔍 بحث بالرقم":
                    user_state[uid]["step"] = "search_phone"
                    bot.send_message(message.chat.id, "🔍 أدخل رقم الهاتف:", reply_markup=back_only_menu(uid))
                elif text == "📋 عرض جميع المستخدمين":
                    all_msg, rows = format_all_users_message()
                    if rows:
                        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
                        for row in rows:
                            if len(row) < 3:
                                continue
                            uid_str = row[2].strip().lstrip("'")
                            if not uid_str.isdigit():
                                continue
                            name = row[0].strip() or "مجهول"
                            markup.add(telebot.types.InlineKeyboardButton(f"👤 {name}", callback_data=f"show_user_{uid_str}"))
                        bot.send_message(message.chat.id, all_msg, parse_mode="Markdown", reply_markup=markup)
                    else:
                        bot.send_message(message.chat.id, all_msg)
                return
            if step == "search_id":
                _, row = find_user_row_by_id(text.strip())
                if row:
                    send_user_card(message.chat.id, row)
                else:
                    bot.send_message(message.chat.id, "❌ لم يُعثر على مستخدم")
                user_state[uid]["step"] = "menu"
                bot.send_message(message.chat.id, "↩️", reply_markup=manage_users_menu(uid))
                return
            if step == "search_phone":
                _, row = find_user_row_by_phone(text.strip())
                if row:
                    send_user_card(message.chat.id, row)
                else:
                    bot.send_message(message.chat.id, "❌ لم يُعثر على مستخدم")
                user_state[uid]["step"] = "menu"
                bot.send_message(message.chat.id, "↩️", reply_markup=manage_users_menu(uid))
                return
            return

        # بث الإشعارات
        if text == bt("زر_اشعار", uid):
            if not (admin or owner):
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط", uid))
                return
            user_state[uid] = {"broadcasting": True, "step": "waiting_text"}
            m_bcast = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            m_bcast.add("📤 إرسال بدون نص", back_btn)
            bot.send_message(message.chat.id, "اكتب نص الإشعار أو اضغط إرسال بدون نص:", reply_markup=m_bcast)
            return

        if state.get("broadcasting"):
            step = state.get("step", "")
            if step == "waiting_text":
                if text == "📤 إرسال بدون نص":
                    user_state[uid]["broadcast_text"] = ""
                else:
                    user_state[uid]["broadcast_text"] = text
                user_state[uid]["step"] = "waiting_file_or_send"
                m_bcast2 = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                m_bcast2.add("📤 إرسال الآن", back_btn)
                bot.send_message(message.chat.id, "أرسل ملفاً (اختياري) أو اضغط إرسال الآن:", reply_markup=m_bcast2)
                return
            if step == "waiting_file_or_send":
                if text == "📤 إرسال الآن":
                    _do_broadcast(message.chat.id, uid, admin, owner, state.get("broadcast_text", ""), state.get("broadcast_files", []))
                    user_state.pop(uid, None)
                return

        # رفع التعليمات
        if text == bt("زر_رفع_تعليمات", uid):
            if not (admin or owner):
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط", uid))
                return
            user_state[uid] = {"uploading_help": True, "step": "choose_audience"}
            bot.send_message(message.chat.id, "👥 هذه التعليمات لمن؟", reply_markup=help_audience_menu(uid))
            return

        if state.get("uploading_help"):
            step = state.get("step", "")
            if step == "choose_audience":
                if text == "👤 للمستخدمين":
                    user_state[uid]["audience"] = "user"
                elif text == "👑 للأدمن":
                    user_state[uid]["audience"] = "admin"
                else:
                    return
                user_state[uid]["step"] = "enter_note"
                bot.send_message(message.chat.id, "📝 أدخل نصاً توضيحياً (اختياري) أو اضغط تخطي:", reply_markup=back_skip_menu(uid))
                return
            if step == "enter_note":
                user_state[uid]["note"] = "" if text == "⏭️ تخطي" else text
                user_state[uid]["step"] = "waiting_file_help"
                bot.send_message(message.chat.id, "📎 أرسل الملف أو الملفات:", reply_markup=back_skip_menu(uid))
                return
            if step == "waiting_file_help":
                if text == "⏭️ تخطي":
                    note = state.get("note", "")
                    if not note:
                        bot.send_message(message.chat.id, "⚠️ لازم ترسل نص أو ملف على الأقل.")
                        return
                    if save_help_material([], state.get("audience", "user"), note):
                        bot.send_message(message.chat.id, "✅ تم الحفظ!", reply_markup=main_menu(uid, admin=admin, owner=owner))
                    else:
                        bot.send_message(message.chat.id, bt("رسالة_خطأ", uid))
                    user_state.pop(uid, None)
                return

        # رفع ملف (أدمن)
        if text == bt("زر_رفع_ملف", uid):
            if not (admin or owner):
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط", uid))
                return
            user_state[uid] = {"uploading": True, "step": "choose_subject"}
            bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=subjects_kb)
            return

        if state.get("uploading"):
            step = state.get("step", "")
            if step == "choose_subject" and text in subjects_list:
                user_state[uid]["subject"] = text
                user_state[uid]["step"] = "choose_type"
                bot.send_message(message.chat.id, f"📌 *{text}*\nاختر النوع:", parse_mode="Markdown", reply_markup=file_type_menu(uid))
                return
            if step == "choose_type":
                if text == bt("زر_اضافة_تكليف", uid):
                    user_state[uid]["col"] = 4
                elif text == bt("زر_اضافة_ملخص", uid):
                    user_state[uid]["col"] = 6
                else:
                    return
                user_state[uid]["step"] = "choose_date"
                subj = state.get("subject", "")
                bot.send_message(message.chat.id, "📅 أدخل التاريخ:", reply_markup=back_only_menu(uid))
                send_date_suggestions(message.chat.id, subject=subj, uid=uid)
                return
            if step == "choose_date":
                d = parse_smart_date(text)
                if not d:
                    bot.send_message(message.chat.id, "❌ صيغة غير صحيحة. مثال: `27/02/2026`", parse_mode="Markdown")
                    send_date_suggestions(message.chat.id, subject=state.get("subject", ""), uid=uid)
                    return
                user_state[uid]["date"] = d
                user_state[uid]["step"] = "waiting_files"
                bot.send_message(message.chat.id, "📎 أرسل الملف أو الملفات:", reply_markup=back_only_menu(uid))
                return
            if step == "confirm_files":
                if text == "✅ إرسال":
                    files = state.get("pending_files", [])
                    col = state.get("col", 4)
                    subj = state.get("subject", "")
                    date = state.get("date", "")
                    fids = [f["file_id"] for f in files]
                    if save_file_to_cell(date, subj, col, fids, merge=False):
                        bot.send_message(message.chat.id, bt("رسالة_تم_الحفظ", uid), reply_markup=main_menu(uid, admin=admin, owner=owner))
                    else:
                        bot.send_message(message.chat.id, bt("رسالة_خطأ", uid))
                    user_state.pop(uid, None)
                return
            return

        # إضافة بيانات
        if text == bt("زر_اضافة", uid):
            if not (admin or owner):
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط", uid))
                return
            user_state[uid] = {"adding_data": True, "step": "choose_type"}
            bot.send_message(message.chat.id, "اختر نوع البيانات:", reply_markup=add_data_menu(uid))
            return

        if state.get("adding_data"):
            step = state.get("step", "")
            ADD_MAP = {bt("زر_اضافة_محاضره", uid): "lecture", bt("زر_اضافة_تكليف", uid): "task",
                       bt("زر_اضافة_ملخص", uid): "summary", bt("زر_اضافة_سعر", uid): "price",
                       bt("زر_اضافة_تنبيه", uid): "alert"}
            if step == "choose_type" and text in ADD_MAP:
                dtype = ADD_MAP[text]
                user_state[uid]["data_type"] = dtype
                if dtype == "lecture":
                    user_state[uid]["step"] = "enter_date"
                    bot.send_message(message.chat.id, "📅 أدخل تاريخ المحاضرة:", reply_markup=back_only_menu(uid))
                    send_date_suggestions(message.chat.id, for_lecture=True, uid=uid)
                elif dtype in ("task", "summary", "alert", "price"):
                    user_state[uid]["step"] = "choose_subject"
                    _kb_no, _ = subjects_with_noexist_kb(uid)
                    bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=_kb_no)
                return
            if step == "choose_subject" and text == "🚫 لا يوجد":
                dtype = state.get("data_type", "")
                label_map = {"task": "لا يوجد تكليف", "summary": "لا يوجد ملخص", "alert": "لا يوجد تنبيه", "price": "لا يوجد سعر"}
                msg_no = label_map.get(dtype, "لا يوجد")
                bot.send_message(message.chat.id, f"✅ تم التسجيل: {msg_no}", reply_markup=main_menu(uid, admin=admin, owner=owner))
                user_state.pop(uid, None)
                return
            if step == "choose_subject" and text in subjects_list:
                user_state[uid]["subject"] = text
                dtype = state.get("data_type", "")
                if dtype == "lecture":
                    if state.get("room") and state.get("date"):
                        user_state[uid]["step"] = "enter_time"
                        bot.send_message(message.chat.id, "🕐 اختر وقت المحاضرة:", reply_markup=lecture_time_menu(uid))
                    else:
                        user_state[uid]["step"] = "choose_building"
                        bot.send_message(message.chat.id, "🏛 اختر المبنى:", reply_markup=buildings_menu(uid))
                elif dtype == "price":
                    user_state[uid]["step"] = "enter_value"
                    bot.send_message(message.chat.id, "💰 أدخل سعر الملزمة:", reply_markup=back_only_menu(uid))
                else:
                    user_state[uid]["step"] = "enter_date"
                    bot.send_message(message.chat.id, "📅 أدخل التاريخ:", reply_markup=back_only_menu(uid))
                    send_date_suggestions(message.chat.id, subject=text, for_alert=(dtype == "alert"), uid=uid)
                return
            if step == "enter_date":
                d = parse_smart_date(text)
                if not d:
                    bot.send_message(message.chat.id, "❌ صيغة غير صحيحة. مثال: `27/02/2026`", parse_mode="Markdown")
                    send_date_suggestions(message.chat.id, for_lecture=(state.get("data_type") == "lecture"),
                                          for_alert=(state.get("data_type") == "alert"), uid=uid)
                    return
                user_state[uid]["date"] = d
                dtype = state.get("data_type", "")
                if dtype == "lecture":
                    user_state[uid]["step"] = "choose_building"
                    bot.send_message(message.chat.id, "🏛 اختر المبنى:", reply_markup=buildings_menu(uid))
                elif dtype in ("task", "summary"):
                    user_state[uid]["step"] = "enter_value"
                    col_lbl = "التكليف" if dtype == "task" else "الملخص"
                    bot.send_message(message.chat.id, f"📝 أدخل نص {col_lbl}:", reply_markup=back_only_menu(uid))
                elif dtype == "alert":
                    user_state[uid]["step"] = "enter_value"
                    bot.send_message(message.chat.id, "⚠️ أدخل نص التنبيه:", reply_markup=back_only_menu(uid))
                return
            if step == "choose_building":
                bmap = {"🏛 القديم": "القديم", "🏫 الاداب": "الاداب"}
                if text in bmap:
                    user_state[uid]["building"] = bmap[text]
                    user_state[uid]["building_label"] = text
                    mk_rooms, rooms = rooms_menu_kb(bmap[text], uid)
                    if not rooms:
                        bot.send_message(message.chat.id, "⚠️ لا توجد قاعات لهذا المبنى. اختر مبنى آخر أو أضف القاعات في شيت القاعات:", reply_markup=buildings_menu(uid))
                        return
                    user_state[uid]["step"] = "choose_room"
                    user_state[uid]["rooms"] = rooms
                    bot.send_message(message.chat.id, "🚪 اختر القاعة:", reply_markup=mk_rooms)
                return
            if step == "choose_room":
                rooms = state.get("rooms", [])
                if rooms and text not in rooms:
                    mk_rooms, _ = rooms_menu_kb(state.get("building", ""), uid)
                    bot.send_message(message.chat.id, "⚠️ اختر قاعة من القائمة:", reply_markup=mk_rooms)
                    return
                user_state[uid]["room"] = f"{state.get('building_label', '')}: {text}"
                dtype = state.get("data_type", "")
                if dtype == "lecture":
                    if state.get("subject"):
                        user_state[uid]["step"] = "enter_time"
                        bot.send_message(message.chat.id, "🕐 اختر وقت المحاضرة:", reply_markup=lecture_time_menu(uid))
                    else:
                        user_state[uid]["step"] = "choose_subject"
                        _kb_no2, _ = subjects_with_noexist_kb(uid)
                        bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=_kb_no2)
                return
            if step == "enter_time":
                TIME_MAP = {"🕐 08:00 - 10:00": "08:00 - 10:00", "🕐 10:00 - 12:00": "10:00 - 12:00", "🕐 12:00 - 14:00": "12:00 - 14:00"}
                if text in TIME_MAP:
                    time_val = TIME_MAP[text]
                elif text == "⏰ توقيت آخر":
                    user_state[uid]["step"] = "enter_time_custom"
                    bot.send_message(message.chat.id, "أدخل الوقت:\n`08:00 - 09:30`", parse_mode="Markdown", reply_markup=back_with_noexist(uid))
                    return
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
                subj = state.get("subject", "")
                date = state.get("date", "")
                room = state.get("room", "")
                time_val = state.get("time_val", "")
                if text == "🔄 استبدال":
                    if save_lecture(date, subj, time_val, room):
                        mk_done = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
                        mk_done.add("➕ إضافة محاضرة أخرى", back_btn)
                        user_state[uid]["step"] = "lecture_done"
                        bot.send_message(message.chat.id, f"✅ تم الاستبدال!\n📌 {subj}\n📅 {date}\n🕐 {time_val}\n📍 {room}", reply_markup=mk_done)
                    else:
                        bot.send_message(message.chat.id, bt("رسالة_خطأ", uid))
                        user_state.pop(uid, None)
                return
            if step == "lecture_done":
                if text == "➕ إضافة محاضرة أخرى":
                    user_state[uid] = {"adding_data": True, "step": "choose_subject", "data_type": "lecture",
                                        "date": state.get("date", ""), "room": state.get("room", ""),
                                        "building": state.get("building", ""), "building_label": state.get("building_label", "")}
                    bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=subjects_kb)
                return
            if step == "enter_value":
                dtype = state.get("data_type", "")
                subj = state.get("subject", "")
                date = state.get("date", "")
                val = text
                if dtype == "price":
                    rows_s = sheet.get_all_values()
                    updated = False
                    for i, row in enumerate(rows_s[1:], start=2):
                        if safe_get(row, 1) == subj:
                            sheet.update_cell(i, 6, val)
                            updated = True
                            break
                    if not updated:
                        sheet.append_row(["", subj, "", "", "", val, "", ""], value_input_option="USER_ENTERED")
                    bot.send_message(message.chat.id, bt("رسالة_تم_الحفظ", uid), reply_markup=main_menu(uid, admin=admin, owner=owner))
                    user_state.pop(uid, None)
                else:
                    col_map2 = {"task": 4, "summary": 6, "alert": 7}
                    col = col_map2.get(dtype, 4)
                    matched = [r for r in data if safe_get(r, 1) == subj and parse_date(safe_get(r, 0)) == date]
                    existing = get_text(safe_get(matched[0], col)) if matched else ""
                    if existing:
                        user_state[uid]["step"] = "confirm_overwrite"
                        user_state[uid]["existing_val"] = existing
                        user_state[uid]["pending_val"] = val
                        mk_ow = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                        mk_ow.add("✏️ بجانبه", "🔄 بدله")
                        mk_ow.add(back_btn)
                        bot.send_message(message.chat.id, f"⚠️ يوجد مدخل سابق:\n`{existing}`\n\nماذا تريد؟", parse_mode="Markdown", reply_markup=mk_ow)
                    else:
                        ok = save_text_to_cell(date, subj, col, val)
                        bot.send_message(message.chat.id, bt("رسالة_تم_الحفظ", uid) if ok else bt("رسالة_خطأ", uid), reply_markup=main_menu(uid, admin=admin, owner=owner))
                        user_state.pop(uid, None)
                return
            if step == "confirm_overwrite":
                dtype = state.get("data_type", "")
                subj = state.get("subject", "")
                date = state.get("date", "")
                col = {"task": 4, "summary": 6, "alert": 7}.get(dtype, 4)
                existing = state.get("existing_val", "")
                pending = state.get("pending_val", "")
                if text == "✏️ بجانبه":
                    final = existing + " | " + pending
                elif text == "🔄 بدله":
                    final = pending
                else:
                    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin, owner=owner))
                    user_state.pop(uid, None)
                    return
                ok = save_text_to_cell(date, subj, col, final)
                bot.send_message(message.chat.id, bt("رسالة_تم_الحفظ", uid) if ok else bt("رسالة_خطأ", uid), reply_markup=main_menu(uid, admin=admin, owner=owner))
                user_state.pop(uid, None)
                return
            return

        # تعديل بيانات
        if text == bt("زر_تعديل", uid):
            if not (admin or owner):
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط", uid))
                return
            user_state[uid] = {"editing_data": True, "step": "choose_type"}
            bot.send_message(message.chat.id, "اختر نوع البيانات:", reply_markup=edit_data_menu(uid))
            return

        if state.get("editing_data"):
            step = state.get("step", "")
            EDIT_MAP = {bt("زر_تعديل_محاضره", uid): "lecture", bt("زر_تعديل_تكليف", uid): "task",
                        bt("زر_تعديل_ملخص", uid): "summary", bt("زر_تعديل_سعر", uid): "price",
                        bt("زر_تعديل_تنبيه", uid): "alert"}
            COL_MAP = {"lecture": 2, "task": 4, "summary": 6, "price": 5, "alert": 7}
            if step == "choose_type" and text in EDIT_MAP:
                user_state[uid]["data_type"] = EDIT_MAP[text]
                user_state[uid]["step"] = "choose_subject"
                bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=subjects_kb)
                return
            if step == "choose_subject" and text in subjects_list:
                user_state[uid]["subject"] = text
                dtype = state.get("data_type", "")
                col = COL_MAP.get(dtype, 2)
                if dtype == "price":
                    matched = [r for r in data if safe_get(r, 1) == text]
                    current = next((get_text(safe_get(r, 5)) for r in matched if safe_get(r, 5)), "")
                    user_state[uid]["step"] = "choose_action"
                    user_state[uid]["current_val"] = current
                    user_state[uid]["date"] = ""
                    bot.send_message(message.chat.id, f"القيمة الحالية: *{current or 'فارغ'}*", parse_mode="Markdown", reply_markup=edit_action_menu(uid))
                else:
                    matched = [r for r in data if safe_get(r, 1) == text]
                    dates = list(dict.fromkeys(parse_date(safe_get(r, 0)) for r in matched if (get_text(safe_get(r, col)) or get_file_ids(safe_get(r, col))) and safe_get(r, 0)))
                    if not dates:
                        bot.send_message(message.chat.id, bt("رسالة_لا_بيانات", uid), reply_markup=edit_data_menu(uid))
                        user_state[uid] = {"editing_data": True, "step": "choose_type"}
                    else:
                        user_state[uid]["step"] = "choose_date_edit"
                        user_state[uid]["col"] = col
                        bot.send_message(message.chat.id, "📅 اختر التاريخ:", reply_markup=dates_menu_kb(dates, uid))
                return
            if step == "choose_date_edit":
                subj = state.get("subject", "")
                col = state.get("col", 2)
                matched = [r for r in data if safe_get(r, 1) == subj and parse_date(safe_get(r, 0)) == text]
                if not matched:
                    bot.send_message(message.chat.id, bt("رسالة_لا_بيانات", uid))
                    return
                current = get_text(safe_get(matched[0], col))
                user_state[uid]["date"] = text
                user_state[uid]["current_val"] = current
                user_state[uid]["step"] = "choose_action"
                bot.send_message(message.chat.id, f"القيمة الحالية: *{current or 'فارغ'}*", parse_mode="Markdown", reply_markup=edit_action_menu(uid))
                return
            if step == "choose_action":
                if text == bt("زر_تعديل_زرار", uid):
                    user_state[uid]["step"] = "enter_new_val"
                    bot.send_message(message.chat.id, "أدخل القيمة الجديدة:", reply_markup=back_only_menu(uid))
                elif text == bt("زر_حذف_زرار", uid):
                    user_state[uid]["step"] = "confirm_delete"
                    cur = state.get("current_val", "")
                    mk_del = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                    mk_del.add("✅ نعم، احذف", "❌ إلغاء")
                    bot.send_message(message.chat.id, f"⚠️ هل أنت متأكد من حذف:\n*{cur}*？", parse_mode="Markdown", reply_markup=mk_del)
                return
            if step == "confirm_delete":
                if text == "✅ نعم، احذف":
                    dtype = state.get("data_type", "")
                    subj = state.get("subject", "")
                    date = state.get("date", "")
                    col = COL_MAP.get(dtype, 2)
                    if dtype == "price":
                        rows_s = sheet.get_all_values()
                        for i, row in enumerate(rows_s[1:], start=2):
                            if safe_get(row, 1) == subj:
                                sheet.update_cell(i, 6, "")
                                break
                        bot.send_message(message.chat.id, bt("رسالة_تم_الحذف", uid), reply_markup=main_menu(uid, admin=admin, owner=owner))
                    else:
                        ok = delete_cell(date, subj, col)
                        bot.send_message(message.chat.id, bt("رسالة_تم_الحذف", uid) if ok else bt("رسالة_خطأ", uid), reply_markup=main_menu(uid, admin=admin, owner=owner))
                    user_state.pop(uid, None)
                elif text == "❌ إلغاء":
                    user_state[uid]["step"] = "choose_action"
                    bot.send_message(message.chat.id, "تم الإلغاء.", reply_markup=edit_action_menu(uid))
                return
            if step == "enter_new_val":
                dtype = state.get("data_type", "")
                subj = state.get("subject", "")
                date = state.get("date", "")
                col = COL_MAP.get(dtype, 2)
                if dtype == "price":
                    rows_s = sheet.get_all_values()
                    for i, row in enumerate(rows_s[1:], start=2):
                        if safe_get(row, 1) == subj:
                            sheet.update_cell(i, 6, text)
                            break
                    bot.send_message(message.chat.id, bt("رسالة_تم_التعديل", uid), reply_markup=main_menu(uid, admin=admin, owner=owner))
                else:
                    ok = save_text_to_cell(date, subj, col, text)
                    bot.send_message(message.chat.id, bt("رسالة_تم_التعديل", uid) if ok else bt("رسالة_خطأ", uid), reply_markup=main_menu(uid, admin=admin, owner=owner))
                user_state.pop(uid, None)
                return
            return

        bot.send_message(message.chat.id, "❓ اختر من القائمة.", reply_markup=main_menu(uid, admin=admin, owner=owner))

    except Exception as e:
        bot.send_message(message.chat.id, bt("رسالة_خطأ", uid))
        log_error(f"handle_message uid={uid}: {e}", uid)

# ─────────────────────────────────────────────────────
# معالجات الـ Callback
# ─────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda call: call.data.startswith("role_"))
def handle_role(call):
    caller_id = call.from_user.id
    if not is_owner_id(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح")
        return
    parts = call.data.split("_", 2)
    new_role = parts[1]
    target_uid = parts[2]
    decided_by = (f"@{call.from_user.username}" if call.from_user.username else call.from_user.full_name)
    try:
        rows = users_sheet.get_all_values()
        es = 0
        for i, row in enumerate(rows[1:], start=2):
            if not row or not any(c.strip() for c in row):
                es += 1
                if es >= 5:
                    break
                continue
            es = 0
            cell_id = row[2].strip().lstrip("'") if len(row) > 2 else ""
            if cell_id != target_uid:
                continue
            cur_own = row[5].strip().upper() if len(row) > 5 else "FALSE"
            cur_adm = row[4].strip().upper() if len(row) > 4 else "FALSE"
            cur_allow = row[3].strip().upper() if len(row) > 3 else "FALSE"
            t_name = row[0].strip()
            t_phone = row[1].strip() if len(row) > 1 else ""
            if new_role == "owner" and cur_own == "TRUE":
                users_sheet.update(f"D{i}:F{i}", [[True, False, False]])
                label = "تم إلغاء صلاحية المالك"
                try:
                    bot.send_message(int(target_uid), "⬇️ تم تخفيض رتبتك من مالك إلى مستخدم عادي.")
                except:
                    pass
                notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "downgrade_owner")
            elif new_role == "admin" and cur_adm == "TRUE" and cur_own != "TRUE":
                users_sheet.update(f"D{i}:F{i}", [[True, False, False]])
                label = "تم إلغاء صلاحية الأدمن"
                try:
                    bot.send_message(int(target_uid), "⬇️ تم تخفيض رتبتك من أدمن إلى مستخدم عادي.")
                except:
                    pass
                notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "downgrade_admin")
            elif new_role == "user" and cur_allow == "TRUE" and cur_adm != "TRUE" and cur_own != "TRUE":
                users_sheet.update(f"D{i}:F{i}", [[False, False, False]])
                label = "⛔ تم إلغاء الصلاحية"
                try:
                    bot.send_message(int(target_uid), "⛔ تم إلغاء صلاحيتك.")
                except:
                    pass
                notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "remove")
            elif new_role == "owner":
                users_sheet.update(f"D{i}:F{i}", [[True, True, True]])
                label = "👑 تم تعيين مالك"
                try:
                    bot.send_message(int(target_uid), "👑 تهانينا! تمت ترقيتك إلى مالك.")
                except:
                    pass
                notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "set_owner")
            elif new_role == "admin":
                users_sheet.update(f"D{i}:F{i}", [[True, True, False]])
                label = "⭐ تم تعيين أدمن"
                try:
                    bot.send_message(int(target_uid), "⭐ تهانينا! تمت ترقيتك إلى أدمن.")
                except:
                    pass
                notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "set_admin")
            else:
                users_sheet.update(f"D{i}:F{i}", [[True, False, False]])
                label = "👤 تم تعيين مستخدم"
                if cur_own == "TRUE":
                    try:
                        bot.send_message(int(target_uid), "⬇️ تم تخفيض رتبتك من مالك إلى مستخدم عادي.")
                    except:
                        pass
                    notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "downgrade_owner_to_user")
                elif cur_adm == "TRUE":
                    try:
                        bot.send_message(int(target_uid), "⬇️ تم تخفيض رتبتك من أدمن إلى مستخدم عادي.")
                    except:
                        pass
                    notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "downgrade_admin")
                else:
                    try:
                        bot.send_message(int(target_uid), bt("رسالة_موافقة", int(target_uid)))
                    except:
                        pass
                    notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "set_user")
            try:
                rows2 = users_sheet.get_all_values()
                for row2 in rows2[1:]:
                    if len(row2) > 2 and row2[2].strip().lstrip("'") == target_uid:
                        send_user_card(call.message.chat.id, row2)
                        break
            except Exception as e2:
                if "message is not modified" not in str(e2):
                    log_error(f"role edit: {e2}")
            bot.answer_callback_query(call.id, label)
            return
        bot.answer_callback_query(call.id, "❌ المستخدم غير موجود")
    except Exception as e:
        log_error(f"handle_role: {e}")
        bot.answer_callback_query(call.id, "❌ خطأ")

@bot.callback_query_handler(func=lambda call: call.data.startswith("ai_on_") or call.data.startswith("ai_off_"))
def handle_ai_permission(call):
    caller_id = call.from_user.id
    if not is_owner_id(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح")
        return
    parts = call.data.split("_", 2)
    action = parts[1]
    target_uid = parts[2]
    decided_by = (f"@{call.from_user.username}" if call.from_user.username else call.from_user.full_name)
    allowed = (action == "on")
    if set_ai_allowed(int(target_uid), allowed):
        label = "✅ تم تفعيل AI" if allowed else "❌ تم تعطيل AI"
        try:
            rows = users_sheet.get_all_values()
            for row in rows[1:]:
                if len(row) > 2 and row[2].strip().lstrip("'") == target_uid:
                    send_user_card(call.message.chat.id, row)
                    break
        except:
            pass
        bot.answer_callback_query(call.id, label)
        name, phone = _get_user_name_phone(int(target_uid))
        notify_owners_action(int(target_uid), name, phone, decided_by, "ai_enabled" if allowed else "ai_disabled")
        try:
            if allowed:
                bot.send_message(int(target_uid), bt("رسالة_ai_تفعيل", int(target_uid)))
            else:
                bot.send_message(int(target_uid), bt("رسالة_ai_تعطيل", int(target_uid)))
        except:
            pass
    else:
        bot.answer_callback_query(call.id, "❌ فشل التحديث")

@bot.callback_query_handler(func=lambda call: call.data.startswith("show_user_"))
def handle_show_user(call):
    uid_str = call.data.split("_")[2]
    _, row = find_user_row_by_id(uid_str)
    if row:
        send_user_card(call.message.chat.id, row)
        bot.answer_callback_query(call.id)
    else:
        bot.answer_callback_query(call.id, "❌ المستخدم غير موجود")

@bot.callback_query_handler(func=lambda call: (call.data.startswith("approve_") or call.data.startswith("reject_")))
def handle_approval(call):
    caller_id = call.from_user.id
    if not is_owner_id(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح")
        return
    decided_by = (f"@{call.from_user.username}" if call.from_user.username else call.from_user.full_name)
    short_key = call.data.split("_", 1)[1]
    req_data = _approval_store.get(short_key)
    if not req_data:
        bot.answer_callback_query(call.id, "⚠️ انتهت صلاحية الطلب")
        return
    requester_id = req_data["requester_id"]
    requester_name = req_data["requester_name"]
    phone = req_data["phone"]
    if call.data.startswith("approve_"):
        try:
            uid_str = str(requester_id)
            rows = users_sheet.get_all_values()
            found = False
            es = 0
            for i, row in enumerate(rows[1:], start=2):
                if not row or not any(c.strip() for c in row):
                    es += 1
                    if es >= 5:
                        break
                    continue
                es = 0
                if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                    users_sheet.update_cell(i, 4, True)
                    found = True
                    break
            if not found:
                add_user_to_sheet(requester_name, requester_id)
            pending_requests.discard(requester_id)
            _approval_store.pop(short_key, None)
            try:
                bot.send_message(requester_id, bt("رسالة_موافقة", requester_id))
            except:
                pass
            notify_owners_action(requester_id, requester_name, phone, decided_by, "approve")
        except Exception as e:
            log_error(f"approve: {e}")
            bot.answer_callback_query(call.id, "❌ خطأ في الحفظ")
            return
    else:
        pending_requests.discard(requester_id)
        _approval_store.pop(short_key, None)
        try:
            bot.send_message(requester_id, bt("رسالة_رفض_طلب", requester_id))
        except:
            pass
        notify_owners_action(requester_id, requester_name, phone, decided_by, "reject")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: (call.data.startswith("ms_subj:") or call.data.startswith("ms_type:")))
def handle_multiselect(call):
    uid = call.from_user.id
    state = user_state.get(uid, {})
    parts = call.data.split(":", 1)
    prefix = parts[0]
    value = parts[1]
    if prefix == "ms_subj":
        subjects = get_subjects()
        sel_key = "sel_subjects"
        items = [(s, s) for s in subjects]
        all_vals = subjects
    elif prefix == "ms_type":
        sel_key = "sel_types"
        items = [("محاضرات", "محاضرات"), ("تكاليف", "تكاليف"), ("ملخصات", "ملخصات")]
        all_vals = ["محاضرات", "تكاليف", "ملخصات"]
    else:
        bot.answer_callback_query(call.id)
        return
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
            items2 = [("محاضرات", "محاضرات"), ("تكاليف", "تكاليف"), ("ملخصات", "ملخصات")]
            kb = build_multiselect_kb(items2, set(), "ms_type")
            try:
                bot.edit_message_text("📋 اختر المطلوب:", call.message.chat.id, call.message.message_id, reply_markup=kb)
            except:
                bot.send_message(call.message.chat.id, "📋 اختر المطلوب:", reply_markup=kb)
        else:
            search_mode = state.get("search_mode", "day")
            sel_subjs = [v for v in state.get("sel_subjects", []) if v != "__all__"]
            if search_mode == "range" and len(sel_subjs) > 1:
                user_state[uid]["step"] = "choose_display"
                try:
                    bot.edit_message_text("📊 اختر طريقة العرض:", call.message.chat.id, call.message.message_id, reply_markup=telebot.types.InlineKeyboardMarkup())
                except:
                    pass
                bot.send_message(call.message.chat.id, "📊 اختر طريقة العرض:", reply_markup=display_mode_menu(uid))
            else:
                user_state[uid]["display_mode"] = "date" if len(sel_subjs) == 1 else "subject"
                _execute_search(call.message.chat.id, uid)
        return
    else:
        if value in selected:
            selected.discard(value)
            selected.discard("__all__")
        else:
            selected.add(value)
        if set(all_vals) <= selected:
            selected.add("__all__")
        else:
            selected.discard("__all__")
    user_state[uid][sel_key] = list(selected)
    kb = build_multiselect_kb(items, selected, prefix)
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb)
    except:
        pass
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("file_req:"))
def handle_file_request_decision(call):
    caller_id = call.from_user.id
    if not _is_admin_or_owner(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح")
        return
    parts = call.data.split(":")
    action = parts[1]
    short_key = parts[2]
    req_data = _file_req_store.get(short_key)
    if not req_data:
        bot.answer_callback_query(call.id, "⚠️ انتهت صلاحية الطلب")
        return
    req_uid = req_data["req_uid"]
    date_val = req_data["date"]
    subject = req_data["subj"]
    col = req_data["col"]
    file_id = req_data["fid"]
    decided_by = (f"@{call.from_user.username}" if call.from_user.username else call.from_user.full_name)
    if action == "approve":
        save_file_to_cell(date_val, subject, col, [file_id])
        _file_req_store.pop(short_key, None)
        try:
            bot.send_message(req_uid, f"✅ تمت الموافقة على ملفك!\n📌 {subject}\n📅 {date_val}")
        except:
            pass
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=telebot.types.InlineKeyboardMarkup())
            bot.send_message(call.message.chat.id, f"✅ موافقة بواسطة {decided_by} | {subject} {date_val}")
        except:
            pass
    else:
        _file_req_store.pop(short_key, None)
        try:
            bot.send_message(req_uid, f"❌ تم رفض طلب رفع ملف\n📌 {subject}\n📅 {date_val}")
        except:
            pass
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=telebot.types.InlineKeyboardMarkup())
            bot.send_message(call.message.chat.id, f"❌ رفض بواسطة {decided_by} | {subject} {date_val}")
        except:
            pass
    bot.answer_callback_query(call.id)

# ─────────────────────────────────────────────────────
# تشغيل البوت
# ─────────────────────────────────────────────────────
def run():
    load_bot_texts()
    load_button_texts()
    if not OPENROUTER_API_KEY:
        log_warning("⚠️ OPENROUTER_API_KEY غير موجود. لن يعمل المساعد الذكي.")
    threading.Thread(target=_watch_sheet_loop, daemon=True).start()
    log_info("بوت الدراسة يعمل ✅")
    bot.infinity_polling()

if __name__ == "__main__":
    run()