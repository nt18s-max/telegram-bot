# ====================================================
# study_test_bot.py — نسخة التطوير والاختبار
# جميع الميزات:
# - دعم متعدد لمزودي AI (OpenRouter, Gemini, NVIDIA, Anthropic, Cohere, DeepSeek, Mistral, Groq)
# - إدارة عبر شيت ai_providers (ترتيب أولوية، نماذج auto)
# - زر AI سويتش + زر النشر التلقائي (عمود K)
# - AI فقط من القائمة الرئيسية
# - رسالة "نايف يكتب..." فورية ومتحركة حتى الرد ثم تُحذف
# - معالجة غير متزامنة (threading) لا تعلق الأزرار
# - دعم التسجيلات الصوتية (Whisper)
# - أوامر إدارية نصية باللغة الطبيعية
# - إدارة مستخدمين متكاملة (بحث ذكي، عرض الكل، آخر 3)
# - بطاقة مستخدم (أزرار: أدمن، مستخدم، AI، تغيير الاسم)
# - طلب انضمام بـ 6 أزرار (رتب + تغيير اسم + تفعيل AI + رفض)
# - تقارير لوج متطورة (تحديث بدلاً من تكرار)
# - إشعارات النشر التلقائي للمشتركين
# - مراقبة تغييرات الشيت وإشعارات
# - ميزة نايف: إرسال file_id إلى اللوج مع كلمة "نايف"
# - استدعاء الملفات عبر الذكاء الاصطناعي (للمالك فقط)
# ====================================================

import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import os, json, re, threading, time, unicodedata
from dotenv import load_dotenv
import pytz, logging
import requests as _requests

load_dotenv()

YEMEN_TZ = pytz.timezone('Asia/Aden')
LOG_BOT_TOKEN = os.environ.get("STUDY_BOT_LOG_TOKEN", "")
STUDY_BOT_TOKEN = os.environ.get("STUDY_TEST_TOKEN", "")
BOT_NAME = "study_test_bot"  # للتمييز في اللوج
SHEET_KEY = os.environ.get("SHEET_KEY", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")

# logging.basicConfig — shared with study_bot, skipped
logger = logging.getLogger("StudyTestBot")

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
        # يحاول الاسم الجديد أولاً ثم القديم للتوافق
        try:
            rooms_sheet = spreadsheet.worksheet("القاعات والمواد")
        except:
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
    "رسالة_الترحيب_ar": "",
    "رسالة_الترحيب_en": "",
    "رسالة_الرفض_ar": "",
    "رسالة_الرفض_en": "",
    "رسالة_انتظار_ar": "",
    "رسالة_انتظار_en": "",
    "رسالة_موافقة_ar": "",
    "رسالة_موافقة_en": "",
    "رسالة_رفض_طلب_ar": "",
    "رسالة_رفض_طلب_en": "",
    "زر_المواد_ar": "",
    "زر_المواد_en": "",
    "زر_التاريخ_ar": "",
    "زر_التاريخ_en": "",
    "زر_التكاليف_ar": "",
    "زر_التكاليف_en": "",
    "زر_الجدول_ar": "",
    "زر_الجدول_en": "",
    "زر_التنبيهات_ar": "",
    "زر_التنبيهات_en": "",
    "زر_الاسعار_ar": "",
    "زر_الاسعار_en": "",
    "زر_الملازم_ar": "",
    "زر_الملازم_en": "",
    "خيار_الملزمه_ar": "",
    "خيار_الملزمه_en": "",
    "زر_اضافة_ملزمه_ar": "",
    "زر_اضافة_ملزمه_en": "",
    "زر_تعديل_ملزمه_ar": "",
    "زر_تعديل_ملزمه_en": "",
    "زر_الملخصات_ar": "",
    "زر_الملخصات_en": "",
    "زر_طلب_رفع_ar": "",
    "زر_طلب_رفع_en": "",
    "زر_رفع_ملف_ar": "",
    "زر_رفع_ملف_en": "",
    "زر_رفع_تعليمات_ar": "",
    "زر_رفع_تعليمات_en": "",
    "زر_اشعار_ar": "",
    "زر_اشعار_en": "",
    "زر_اضافة_ar": "",
    "زر_اضافة_en": "",
    "زر_تعديل_ar": "",
    "زر_تعديل_en": "",
    "زر_المستخدمين_ar": "",
    "زر_المستخدمين_en": "",
    "زر_عوده_ar": "",
    "زر_عوده_en": "",
    "زر_يوم_ar": "",
    "زر_يوم_en": "",
    "زر_فتره_ar": "",
    "زر_فتره_en": "",
    "زر_تحديد_الكل_ar": "",
    "زر_تحديد_الكل_en": "",
    "زر_تم_التحديد_ar": "",
    "زر_تم_التحديد_en": "",
    "زر_حسب_الماده_ar": "",
    "زر_حسب_الماده_en": "",
    "زر_حسب_التاريخ_ar": "",
    "زر_حسب_التاريخ_en": "",
    "زر_اضافة_محاضره_ar": "",
    "زر_اضافة_محاضره_en": "",
    "زر_اضافة_تكليف_ar": "",
    "زر_اضافة_تكليف_en": "",
    "زر_اضافة_ملخص_ar": "",
    "زر_اضافة_ملخص_en": "",
    "زر_اضافة_سعر_ar": "",
    "زر_اضافة_سعر_en": "",
    "زر_اضافة_تنبيه_ar": "",
    "زر_اضافة_تنبيه_en": "",
    "زر_تعديل_محاضره_ar": "",
    "زر_تعديل_محاضره_en": "",
    "زر_تعديل_تكليف_ar": "",
    "زر_تعديل_تكليف_en": "",
    "زر_تعديل_ملخص_ar": "",
    "زر_تعديل_ملخص_en": "",
    "زر_تعديل_سعر_ar": "",
    "زر_تعديل_سعر_en": "",
    "زر_تعديل_تنبيه_ar": "",
    "زر_تعديل_تنبيه_en": "",
    "زر_تعديل_زرار_ar": "",
    "زر_تعديل_زرار_en": "",
    "زر_حذف_زرار_ar": "",
    "زر_حذف_زرار_en": "",
    "خيار_الجدول_ar": "",
    "خيار_الجدول_en": "",
    "خيار_التكاليف_ar": "",
    "خيار_التكاليف_en": "",
    "خيار_السعر_ar": "",
    "خيار_السعر_en": "",
    "خيار_الملخص_ar": "",
    "خيار_الملخص_en": "",
    "خيار_التنبيهات_ar": "",
    "خيار_التنبيهات_en": "",
    "رسالة_لا_بيانات_ar": "",
    "رسالة_لا_بيانات_en": "",
    "رسالة_خطأ_ar": "",
    "رسالة_خطأ_en": "",
    "رسالة_تم_الحفظ_ar": "",
    "رسالة_تم_الحفظ_en": "",
    "رسالة_تم_الحذف_ar": "",
    "رسالة_تم_الحذف_en": "",
    "رسالة_تم_التعديل_ar": "",
    "رسالة_تم_التعديل_en": "",
    "رسالة_ادمن_فقط_ar": "",
    "رسالة_ادمن_فقط_en": "",
    "زر_مساعد_نايف_ar": "",
    "زر_مساعد_نايف_en": "",
    "زر_نشر_تلقائي_ar": "",
    "زر_نشر_تلقائي_en": "",
    "رسالة_نايف_يكتب_ar": "",
    "رسالة_نايف_يكتب_en": "",
    "رسالة_ai_غير_مفعل_ar": "",
    "رسالة_ai_غير_مفعل_en": "",
    "رسالة_ai_غير_مسموح_ar": "",
    "رسالة_ai_غير_مسموح_en": "",
    "رسالة_ai_اشتراك_ar": "",
    "رسالة_ai_اشتراك_en": "",
    "رسالة_ai_فشل_ar": "",
    "رسالة_ai_فشل_en": "",
    "رسالة_ai_تم_الغاء_ar": "",
    "رسالة_ai_تم_الغاء_en": "",
    "رسالة_ai_تفعيل_ar": "",
    "رسالة_ai_تفعيل_en": "",
    "رسالة_ai_تعطيل_ar": "",
    "رسالة_ai_تعطيل_en": "",
    "رسالة_ai_ترحيب_ar": "",
    "رسالة_ai_ترحيب_en": "",
    "رسالة_تغيير_اللغة_ar": "",
    "رسالة_تغيير_اللغة_en": "",
    "رسالة_تم_تغيير_اللغة_ar": "",
    "رسالة_تم_تغيير_اللغة_en": "",
    "رسالة_طلب_جهة_اتصال_ar": "",
    "رسالة_طلب_جهة_اتصال_en": "",
    "رسالة_شكر_اتصال_ar": "",
    "رسالة_شكر_اتصال_en": "",
    "رسالة_غير_مسموح_ar": "",
    "رسالة_غير_مسموح_en": "",
    "زر_مشاركة_رقم_ar": "",
    "زر_مشاركة_رقم_en": "",
    "زر_لا_اريد_ar": "",
    "زر_لا_اريد_en": "",
    "رسالة_مشاركة_ar": "",
    "رسالة_مشاركة_en": "",
    "زر_مشاركة_كيبورد_ar": "",
    "زر_مشاركة_كيبورد_en": "",
    "زر_عوده_مشاركه_ar": "",
    "رسالة_كيبورد_مشاركة_ar": "",
    "رسالة_كيبورد_مشاركة_en": "",
    "زر_عوده_مشاركه_en": "",
    "رسالة_لا_اريد_ar": "",
    "رسالة_لا_اريد_en": "",
    "زر_بوت_تواصل_ar": "",
    "زر_بوت_تواصل_en": "",
    "رابط_بوت_تواصل_ar": "",
    "رابط_بوت_تواصل_en": "",
    "رسالة_جاري_الحذف_ar": "",
    "رسالة_جاري_الحذف_en": "",
}
BOT_TEXTS = dict(DEFAULT_BOT_TEXTS)

# ── ألوان الأزرار من عمود D في الشيت ──────────────────
# القيم المقبولة: danger (أحمر)، success (أخضر)، primary (أزرق)، فارغ (افتراضي)
BUTTON_STYLES: dict[str, str] = {}
_VALID_STYLES = {"danger", "success", "primary"}

def load_bot_texts():
    global BOT_TEXTS, BUTTON_STYLES
    try:
        rows = bot_texts_sheet.get_all_values()
        styles = {}
        for row in rows:
            if len(row) >= 2 and row[0].strip():
                key = row[0].strip()
                ar_text = row[1].strip() if len(row) > 1 else ""
                en_text = row[2].strip() if len(row) > 2 else ""
                # عمود D — لون الزر (اختياري)
                style = row[3].strip().lower() if len(row) > 3 else ""
                BOT_TEXTS[f"{key}_ar"] = ar_text if ar_text else DEFAULT_BOT_TEXTS.get(f"{key}_ar", key)
                BOT_TEXTS[f"{key}_en"] = en_text if en_text else DEFAULT_BOT_TEXTS.get(f"{key}_en", key)
                if style in _VALID_STYLES:
                    styles[key] = style
        BUTTON_STYLES = styles
        logger.info(f"✅ bot_texts loaded with bilingual support ({len(styles)} أزرار ملوّنة)")
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

def _make_btn(key, uid=None):
    """ينشئ KeyboardButton مع لون من الشيت إذا وُجد — يسقط بأمان إذا المكتبة لم تدعمه."""
    label = bt(key, uid)
    style = BUTTON_STYLES.get(key, "")
    if style in _VALID_STYLES:
        try:
            return telebot.types.KeyboardButton(label, style=style)
        except Exception:
            pass
    return telebot.types.KeyboardButton(label)

def _make_inline(key, label, callback_data):
    """ينشئ InlineKeyboardButton مع لون من الشيت إذا وُجد — يسقط بأمان إذا المكتبة لم تدعمه."""
    style = BUTTON_STYLES.get(key, "")
    if style in _VALID_STYLES:
        try:
            return telebot.types.InlineKeyboardButton(label, callback_data=callback_data, style=style)
        except Exception:
            pass
    return telebot.types.InlineKeyboardButton(label, callback_data=callback_data)

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
user_auto_publish = {}
AI_PROVIDERS = []
_temp_admin_actions = {}
_log_messages = {}
_user_card_messages = {}
_pending_files = {}
_naif_files = {}
_pending_kb_msgs = {}  # تخزين message_id لرسائل الكيبورد المؤقتة {uid: msg_id}
_schedule_cards = {}   # تخزين بطاقات الجدول المستخرجة مؤقتاً: {short_key: {uid, entries, msg_id, chat_id}}

# ─────────────────────────────────────────────────────
# دوال AI المتعددة
# ─────────────────────────────────────────────────────
_ai_histories = {}
_AI_MAX_HISTORY = 20

AI_SYSTEM_PROMPT_BASE = (
    "أنت مساعد ذكي لطلاب الجامعة اسمك 'مساعد نايف'. أجب دائماً باللغة العربية ما لم يطلب المستخدم غير ذلك. "
    "إجاباتك مختصرة وواضحة ومناسبة للطلاب. لا تستخدم markdown بشكل مبالغ فيه.\n\n"
    "**تعليمات مهمة جداً عند الإجابة عن كيفية استخدام البوت:**\n"
    "- إذا سأل المستخدم 'كيف' يفعل شيئاً في البوت، اشرح له المسار بالأسهم مثل:\n"
    "  📚 المواد ← رياضيات ← 📝 التكاليف ← اختر التاريخ\n"
    "- اذكر اسم الزر كما يظهر في البوت بالضبط.\n"
    "- إذا كان هناك أكثر من طريقة، اذكرهم جميعاً.\n"
    "- كن محدداً ومختصراً."
)

def load_ai_providers():
    """قراءة قائمة مزودي الذكاء الاصطناعي من الشيت ai_providers"""
    global AI_PROVIDERS
    AI_PROVIDERS = []
    try:
        sheet_providers = spreadsheet.worksheet("ai_providers")
        rows = sheet_providers.get_all_values()
        if not rows:
            logger.info("⚠️ لا توجد صفحة ai_providers أو فارغة.")
            return
        for row in rows[1:]:
            if len(row) < 5:
                continue
            order = row[0].strip()
            provider = row[1].strip().lower()
            api_key = row[2].strip()
            model = row[3].strip().lower()
            enabled = row[4].strip().upper() == "TRUE"
            if not enabled or not api_key:
                continue

            # معالجة النموذج "auto"
            if model == "auto":
                if provider == "gemini":
                    model = "gemini-1.5-flash"
                elif provider == "openrouter":
                    model = "openrouter/free"
                elif provider == "nvidia":
                    model = "nvidia/nemotron-3-super:free"
                elif provider == "anthropic":
                    model = "claude-3-haiku-20240307"
                elif provider == "cohere":
                    model = "command-r"
                elif provider == "deepseek":
                    model = "deepseek-chat"
                elif provider == "mistral":
                    model = "mistral-small-latest"
                elif provider == "groq":
                    model = "llama3-70b-8192"
                else:
                    continue

            if provider == "gemini":
                AI_PROVIDERS.append({
                    "order": int(order) if order.isdigit() else 999,
                    "provider": "gemini",
                    "api_key": api_key,
                    "model": model,
                    "name": f"Gemini {model}",
                    "icon": "✨"
                })
            elif provider == "openrouter":
                AI_PROVIDERS.append({
                    "order": int(order) if order.isdigit() else 999,
                    "provider": "openrouter",
                    "api_key": api_key,
                    "model": model,
                    "name": "OpenRouter Auto" if model == "openrouter/free" else model.split('/')[-1].replace(':free', ''),
                    "icon": "🎯"
                })
            elif provider == "nvidia":
                AI_PROVIDERS.append({
                    "order": int(order) if order.isdigit() else 999,
                    "provider": "nvidia",
                    "api_key": api_key,
                    "model": model,
                    "name": f"NVIDIA {model.split('/')[-1]}",
                    "icon": "🟢"
                })
            elif provider == "anthropic":
                AI_PROVIDERS.append({
                    "order": int(order) if order.isdigit() else 999,
                    "provider": "anthropic",
                    "api_key": api_key,
                    "model": model,
                    "name": f"Claude {model}",
                    "icon": "🔮"
                })
            elif provider == "cohere":
                AI_PROVIDERS.append({
                    "order": int(order) if order.isdigit() else 999,
                    "provider": "cohere",
                    "api_key": api_key,
                    "model": model,
                    "name": f"Cohere {model}",
                    "icon": "🌀"
                })
            elif provider == "deepseek":
                AI_PROVIDERS.append({
                    "order": int(order) if order.isdigit() else 999,
                    "provider": "deepseek",
                    "api_key": api_key,
                    "model": model,
                    "name": f"DeepSeek {model}",
                    "icon": "🔍"
                })
            elif provider == "mistral":
                AI_PROVIDERS.append({
                    "order": int(order) if order.isdigit() else 999,
                    "provider": "mistral",
                    "api_key": api_key,
                    "model": model,
                    "name": f"Mistral {model}",
                    "icon": "💨"
                })
            elif provider == "groq":
                AI_PROVIDERS.append({
                    "order": int(order) if order.isdigit() else 999,
                    "provider": "groq",
                    "api_key": api_key,
                    "model": model,
                    "name": f"Groq {model}",
                    "icon": "⚡"
                })
        AI_PROVIDERS.sort(key=lambda x: x["order"])
        logger.info(f"✅ تم تحميل {len(AI_PROVIDERS)} مزود AI")
        for p in AI_PROVIDERS:
            logger.info(f"   {p['order']}: {p['provider']} - {p['model']}")
    except Exception as e:
        logger.warning(f"لم يتم العثور على صفحة ai_providers أو خطأ: {e}")
        AI_PROVIDERS = []

def call_gemini(provider, uid, user_text, system_prompt):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{provider['model']}:generateContent?key={provider['api_key']}"
        payload = {
            "contents": [{
                "parts": [{"text": system_prompt + "\n\n" + user_text}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024,
            }
        }
        resp = _requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return text, {"id": provider["model"], "name": provider["name"], "icon": provider["icon"]}
        else:
            log_error(f"Gemini error {resp.status_code}: {resp.text[:200]}", uid)
            return None, None
    except Exception as e:
        log_error(f"Gemini exception: {e}", uid)
        return None, None

def call_openrouter(provider, uid, user_text, system_prompt, notify_fn=None, send_notify=True):
    headers = {
        "Authorization": f"Bearer {provider['api_key']}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/study_bot",
        "X-Title": "Study Bot",
    }
    payload = {
        "model": provider["model"],
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
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            return content, {"id": provider["model"], "name": provider["name"], "icon": provider["icon"]}
        else:
            log_error(f"OpenRouter {resp.status_code} {resp.text[:200]} on {provider['model']}", uid)
            return None, None
    except Exception as e:
        log_error(f"OpenRouter exception: {e}", uid)
        return None, None

def call_nvidia(provider, uid, user_text, system_prompt):
    try:
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": provider["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            "temperature": 0.7,
            "max_tokens": 1024
        }
        resp = _requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return text, {"id": provider["model"], "name": provider["name"], "icon": provider["icon"]}
        else:
            log_error(f"NVIDIA error {resp.status_code}: {resp.text[:200]}", uid)
            return None, None
    except Exception as e:
        log_error(f"NVIDIA exception: {e}", uid)
        return None, None

def call_anthropic(provider, uid, user_text, system_prompt):
    try:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": provider["api_key"],
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload = {
            "model": provider["model"],
            "max_tokens": 1024,
            "temperature": 0.7,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_text}]
        }
        resp = _requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            text = data["content"][0]["text"]
            return text, {"id": provider["model"], "name": provider["name"], "icon": provider["icon"]}
        else:
            log_error(f"Anthropic error {resp.status_code}: {resp.text[:200]}", uid)
            return None, None
    except Exception as e:
        log_error(f"Anthropic exception: {e}", uid)
        return None, None

def call_cohere(provider, uid, user_text, system_prompt):
    try:
        url = "https://api.cohere.ai/v1/chat"
        headers = {
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": provider["model"],
            "message": user_text,
            "preamble": system_prompt,
            "temperature": 0.7,
            "max_tokens": 1024
        }
        resp = _requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            text = data["text"]
            return text, {"id": provider["model"], "name": provider["name"], "icon": provider["icon"]}
        else:
            log_error(f"Cohere error {resp.status_code}: {resp.text[:200]}", uid)
            return None, None
    except Exception as e:
        log_error(f"Cohere exception: {e}", uid)
        return None, None

def call_deepseek(provider, uid, user_text, system_prompt):
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": provider["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            "temperature": 0.7,
            "max_tokens": 1024
        }
        resp = _requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return text, {"id": provider["model"], "name": provider["name"], "icon": provider["icon"]}
        else:
            log_error(f"DeepSeek error {resp.status_code}: {resp.text[:200]}", uid)
            return None, None
    except Exception as e:
        log_error(f"DeepSeek exception: {e}", uid)
        return None, None

def call_mistral(provider, uid, user_text, system_prompt):
    try:
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": provider["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            "temperature": 0.7,
            "max_tokens": 1024
        }
        resp = _requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return text, {"id": provider["model"], "name": provider["name"], "icon": provider["icon"]}
        else:
            log_error(f"Mistral error {resp.status_code}: {resp.text[:200]}", uid)
            return None, None
    except Exception as e:
        log_error(f"Mistral exception: {e}", uid)
        return None, None

def call_groq(provider, uid, user_text, system_prompt):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": provider["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            "temperature": 0.7,
            "max_tokens": 1024
        }
        resp = _requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return text, {"id": provider["model"], "name": provider["name"], "icon": provider["icon"]}
        else:
            log_error(f"Groq error {resp.status_code}: {resp.text[:200]}", uid)
            return None, None
    except Exception as e:
        log_error(f"Groq exception: {e}", uid)
        return None, None

def ai_reset_model():
    """إعادة تحميل مزودي AI من الشيت"""
    global AI_PROVIDERS
    load_ai_providers()

# ─────────────────────────────────────────────────────
# نظام استخراج الجدول من النص
# ─────────────────────────────────────────────────────

def _time12_to_24(t):
    """
    يحوّل الوقت بأي تنسيق:
    - ساعتان (10-12) → HH:MM - HH:MM
    - ساعة واحدة (من 11) → HH:MM فقط بدون نهاية
    يقبل: عربي/إنجليزي، أرقام عربية، أي فاصل
    """
    if not t:
        return t
    t = str(t).strip()
    # تحويل الأرقام العربية
    t = t.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    # إزالة كلمات زائدة
    t = re.sub(r'من\s*الساعة|من\s+|الساعة\s*|إلى\s*|الى\s*|حتى\s*|\b(am|pm|ص|م)\b',
               ' ', t, flags=re.IGNORECASE)
    t = re.sub(r'[–—]', '-', t)
    t = t.strip()

    nums = re.findall(r'\d{1,2}(?:[.:]\d{2})?', t)

    def _h24(s):
        s = str(s).replace(':', '.').replace(',', '.')
        if '.' in s:
            h, m = int(s.split('.')[0]), int(s.split('.')[1])
        else:
            h, m = int(s), 0
        if 1 <= h <= 7:
            h += 12
        return h, m

    try:
        if len(nums) >= 2:
            h1, m1 = _h24(nums[0])
            h2, m2 = _h24(nums[1])
            return f"{h1:02d}:{m1:02d} - {h2:02d}:{m2:02d}"
        elif len(nums) == 1:
            # ساعة واحدة فقط → بدون نهاية
            h1, m1 = _h24(nums[0])
            return f"{h1:02d}:{m1:02d}"
        else:
            return t
    except:
        return t

def _format_schedule_card(entries, note=""):
    """بناء نص البطاقة بالتنسيق المطلوب"""
    nums = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    lines = ["📥 *بطاقة بيانات جاهزة للاعتماد*",
             "📚 *الجدول الدراسي المكتشف:*\n"]
    for i, e in enumerate(entries):
        num = nums[i] if i < len(nums) else f"{i+1}."
        teacher = e.get("teacher", "")
        subject = e.get("subject", "")
        subj_display = f"{subject} ({teacher})" if teacher else subject
        entry_type = e.get("type", "محاضرة")
        lines.append(f"{num} *المادة:* {subj_display}")
        lines.append(f"📅 *التاريخ:* {e.get('date','')}")
        lines.append(f"🕒 *الوقت:* {e.get('time','')}")
        lines.append(f"🏛️ *المكان:* {e.get('place','')}")
        lines.append(f"📂 *النوع:* {entry_type}\n")
    if note:
        lines.append(f"⚠️ *ملاحظة إضافية:* {note}\n")
    lines.append("*القرار المطلوب:*")
    return "\n".join(lines)

def _schedule_card_markup(short_key):
    """أزرار البطاقة"""
    mk = telebot.types.InlineKeyboardMarkup(row_width=3)
    mk.row(
        _make_inline("زر_sched_accept", "✅ قبول وإضافة", f"sched_accept_{short_key}"),
        _make_inline("زر_sched_edit",   "✏️ تعديل",       f"sched_edit_{short_key}"),
        _make_inline("زر_sched_cancel", "❌ إلغاء",        f"sched_cancel_{short_key}"),
    )
    return mk

_EXTRACT_PROMPT = """\
أنت محلل بيانات أكاديمية متخصص وذكي. مهمتك فهم النص وتحديد إذا يحتوي جدولاً دراسياً أم لا.

إذا النص سؤال أو محادثة عادية → أرجع: {"entries": [], "note": ""}

إذا النص يحتوي محاضرات أو مواعيد دراسية → استخرجها بذكاء بغض النظر عن التنسيق.

قواعد الوقت (افهمها بذكاء كما يفهمها الطالب اليمني):
- الأوقات من 8 إلى 12 = صباح (8→08:00, 10→10:00, 12→12:00)
- الأوقات من 1 إلى 7 = مساء (1→13:00, 2→14:00, 3→15:00)
- "8-10" → "08:00 - 10:00"
- "11-1" → "11:00 - 13:00"  
- "12-2" → "12:00 - 14:00"
- "من الساعة 11" (بدون نهاية) → "11:00 - 13:00"
- تجاهل كلمات مثل "من الساعة" و"الساعة" واستخرج الأرقام فقط

قواعد التاريخ:
- حوّل أي تاريخ لصيغة DD/MM/YYYY ميلادي
- "الأحد 5 أبريل 2026" → "05/04/2026"
- "2026/4/5" → "05/04/2026"

قواعد التعديل:
- إذا في رسالة تعديل (تغيير أستاذ/وقت/مكان) → اذكر النسخة النهائية فقط، واشرح التعديل في note
- إذا في إجازة → note فقط، لا entry

أرجع JSON فقط بهذا الشكل الحرفي (بدون أي نص إضافي أو backticks):
{"entries":[{"subject":"اسم المادة","teacher":"اسم الأستاذ كاملاً","date":"DD/MM/YYYY","time":"HH:MM - HH:MM","place":"المكان","type":"محاضرة"}],"note":"ملاحظة أو فارغ"}
"""

def extract_schedule_from_text(raw_text):
    """
    يستخرج الجدول من النص - يُفضّل Gemini لدقته، ثم يجرب بقية المزودين.
    يرجع (entries_list, note_str) أو ([], "") للنصوص غير الجدولية أو (None, None) عند الفشل.
    """
    if not AI_PROVIDERS:
        return None, None
    import json as _json

    # ترتيب المزودين: Gemini أولاً لأنه الأدق في الاستخراج
    sorted_providers = (
        [p for p in AI_PROVIDERS if p["provider"] == "gemini"] +
        [p for p in AI_PROVIDERS if p["provider"] != "gemini"]
    )

    for provider in sorted_providers:
        try:
            # أضف قاموس المواد والأساتذة إذا كان موجوداً
            subjects_ctx = ""
            try:
                s_map = get_subjects_with_doctors()
                if s_map:
                    lines_map = [f"- {s}: {', '.join(docs) if docs else 'غير محدد'}"
                                 for s, docs in s_map.items()]
                    subjects_ctx = "\n\nمواد البوت وأساتذتها (للمرجعية):\n" + "\n".join(lines_map)
            except:
                pass
            full_prompt = _EXTRACT_PROMPT + subjects_ctx + "\n\nالنص:\n" + raw_text
            if provider["provider"] == "gemini":
                url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                       f"{provider['model']}:generateContent?key={provider['api_key']}")
                payload = {
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {"temperature": 0, "maxOutputTokens": 1024}
                }
                resp = _requests.post(url, json=payload, timeout=30)
                if resp.status_code != 200:
                    log_error(f"Gemini extract error {resp.status_code}: {resp.text[:100]}")
                    continue
                raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                headers = {
                    "Authorization": f"Bearer {provider['api_key']}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": provider["model"],
                    "messages": [{"role": "user", "content": full_prompt}],
                    "temperature": 0,
                    "max_tokens": 1024
                }
                url_map = {
                    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
                    "nvidia":     "https://integrate.api.nvidia.com/v1/chat/completions",
                    "deepseek":   "https://api.deepseek.com/v1/chat/completions",
                    "mistral":    "https://api.mistral.ai/v1/chat/completions",
                    "groq":       "https://api.groq.com/openai/v1/chat/completions",
                    "anthropic":  None,  # لا يدعم هذا الاستخدام هنا
                }
                ep = url_map.get(provider["provider"])
                if not ep:
                    continue
                resp = _requests.post(ep, headers=headers, json=payload, timeout=30)
                if resp.status_code != 200:
                    continue
                raw = resp.json()["choices"][0]["message"]["content"]

            # تنظيف JSON
            raw = raw.strip()
            raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.IGNORECASE)
            raw = re.sub(r'\s*```\s*$', '', raw)
            raw = raw.strip()

            data = _json.loads(raw)
            entries = data.get("entries", [])
            note = data.get("note", "") or ""

            # الـ AI يتولى تحويل الوقت — لا نحتاج معالجة يدوية
            return entries, note  # [] = نص عادي، [...] = جدول

        except Exception as ex:
            log_error(f"extract_schedule ({provider['provider']}): {ex}")
            continue

    return None, None  # فشل كل المزودين

def ask_ai(uid, user_text, user_role="user", notify_fn=None, send_notify=True):
    if not AI_PROVIDERS:
        log_error(f"لا يوجد مزود AI نشط", uid)
        return None, None

    if uid not in _ai_histories:
        _ai_histories[uid] = []
    _ai_histories[uid].append({"role": "user", "content": user_text})
    if len(_ai_histories[uid]) > _AI_MAX_HISTORY:
        _ai_histories[uid] = _ai_histories[uid][-_AI_MAX_HISTORY:]

    # بناء system prompt
    data_summary = get_data_summary_for_ai(uid, user_role)
    bot_summary = get_bot_code_summary(uid)

    if user_role == "owner":
        role_desc = (
            "أنت مالك البوت. لديك صلاحيات كاملة: إدارة المستخدمين، تغيير الرتب، "
            "تفعيل/تعطيل صلاحية AI، بالإضافة إلى كل صلاحيات الأدمن.\n\n"
            "**ملاحظة مهمة**: يمكنك تنفيذ أي أمر إداري يطلبه منك المالك. "
            "إذا قال لك 'خذ هذا الملف وأضفه كتعليمات'، يجب عليك تنفيذ ذلك مباشرة."
        )
    elif user_role == "admin":
        role_desc = "أنت أدمن في البوت. لديك صلاحيات الإضافة والتعديل والحذف على جميع البيانات، ويمكنك إرسال إشعارات ورفع ملفات مباشرة. لا يمكنك رؤية بيانات المستخدمين الآخرين عبر هذه المحادثة."
    else:
        role_desc = "أنت مستخدم عادي. يمكنك فقط عرض البيانات (محاضرات، تكاليف، ملخصات، تنبيهات، أسعار). لا يمكنك رفع ملفات مباشرة، ولكن يمكنك طلب رفع ملف عبر الزر المخصص."

    admin_note = ""
    if user_role in ("admin", "owner"):
        admin_note = (
            "\n\n**ملاحظة للمستخدم (أدمن/مالك):**\n"
            "يمكنك إصدار أوامر لإضافة وتعديل وحذف البيانات مباشرة باستخدام اللغة الطبيعية. مثال:\n"
            "- أضف محاضرة رياضيات يوم 27/03/2026 الساعة 10:00-12:00 قاعة 101\n"
            "- أضف تكليف برمجة تاريخ 28/03/2026: حل المسائل 1-5\n"
            "- احذف محاضرة فيزياء يوم 26/03/2026\n"
            "- أضف سعر رياضيات 5000\n"
            "- أرسل إشعار للجميع: مرحباً\n"
            "- بلغ المستخدم 123456789 يقول له: أهلاً\n"
            "- فعّل AI للمستخدم 123456789\n"
            "- أعد تعيين AI - إعادة تعيين نموذج الذكاء الاصطناعي (للمالك فقط)\n"
            "- أعطني الملف [file_id] - استدعاء ملف عبر معرفه\n"
            "- أعطني آخر ملف - استدعاء آخر ملف تم رفعه\n"
        )

    system_prompt = (
        AI_SYSTEM_PROMPT_BASE + "\n\n" + role_desc + "\n\n" +
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

    # تجربة المزودين بالترتيب
    for provider in AI_PROVIDERS:
        if provider["provider"] == "gemini":
            response, model_info = call_gemini(provider, uid, user_text, system_prompt)
        elif provider["provider"] == "openrouter":
            response, model_info = call_openrouter(provider, uid, user_text, system_prompt, notify_fn, send_notify)
        elif provider["provider"] == "nvidia":
            response, model_info = call_nvidia(provider, uid, user_text, system_prompt)
        elif provider["provider"] == "anthropic":
            response, model_info = call_anthropic(provider, uid, user_text, system_prompt)
        elif provider["provider"] == "cohere":
            response, model_info = call_cohere(provider, uid, user_text, system_prompt)
        elif provider["provider"] == "deepseek":
            response, model_info = call_deepseek(provider, uid, user_text, system_prompt)
        elif provider["provider"] == "mistral":
            response, model_info = call_mistral(provider, uid, user_text, system_prompt)
        elif provider["provider"] == "groq":
            response, model_info = call_groq(provider, uid, user_text, system_prompt)
        else:
            continue

        if response:
            _ai_histories[uid].append({"role": "assistant", "content": response})
            if len(_ai_histories[uid]) > _AI_MAX_HISTORY:
                _ai_histories[uid] = _ai_histories[uid][-_AI_MAX_HISTORY:]
            return response, model_info

    return None, None

# ─────────────────────────────────────────────────────
# دوال مساعدة للشيت (الأساسية)
# ─────────────────────────────────────────────────────
AI_ALLOWED_COL = 9
AUTO_PUBLISH_COL = 10
AI_SWITCH_COL = 11   # عمود L — حالة سويتش الذكاء الاصطناعي (يحفظها المستخدم)

# ─── Cache للمستخدمين (يمنع Bug الصلاحية الزائفة) ───
_users_cache = {"data": None, "ts": 0}
_USERS_CACHE_TTL = 30  # ثانية

# ─── Cache للبيانات الرئيسية (sheet data) ───
_sheet_data_cache = {"data": None, "ts": 0}
_bot_texts_cache  = {"data": None, "ts": 0}
_SHEET_CACHE_TTL  = 60  # ثانية — يُحدَّث تلقائياً كل دقيقة

def invalidate_users_cache():
    """إبطال الـ cache فوراً عند أي تغيير في الصلاحيات"""
    _users_cache["data"] = None
    _users_cache["ts"] = 0

def get_users():
    global _users_cache
    now = time.time()
    # إذا الـ cache صالح → أعد البيانات مباشرة بدون قراءة الشيت
    if _users_cache["data"] is not None and now - _users_cache["ts"] < _USERS_CACHE_TTL:
        return _users_cache["data"]
    try:
        allowed, admins, owners, log_ids, ai_allowed, auto_publish_uids = [], [], [], [], [], []
        open_all = admin_all = False
        es = 0
        for row in users_sheet.get_all_values()[1:]:
            if not row or not any(c.strip() for c in row):
                es += 1
                if es >= 5:
                    break
                continue
            es = 0
            name = row[0].strip()
            uid_str = row[2].strip().lstrip("'") if len(row) > 2 else ""
            allowed_val = row[3].strip().upper() if len(row) > 3 else "FALSE"
            admin_val = row[4].strip().upper() if len(row) > 4 else "FALSE"
            owner_val = row[5].strip().upper() if len(row) > 5 else "FALSE"
            log_val = row[7].strip().upper() if len(row) > 7 else "FALSE"
            ai_val = row[AI_ALLOWED_COL].strip().upper() if len(row) > AI_ALLOWED_COL else "FALSE"
            auto_val = row[AUTO_PUBLISH_COL].strip().upper() if len(row) > AUTO_PUBLISH_COL else "FALSE"
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
            if owner_val == "TRUE":
                owners.append(uid)
            if log_val == "TRUE":
                log_ids.append(uid)
            if ai_val == "TRUE":
                ai_allowed.append(uid)
            if auto_val == "TRUE":
                auto_publish_uids.append(uid)
        result = (allowed, admins, owners, open_all, admin_all, log_ids, ai_allowed, auto_publish_uids)
        _users_cache["data"] = result
        _users_cache["ts"] = time.time()
        return result
    except Exception as e:
        log_error(f"get_users: {e}")
        # fallback → آخر بيانات معروفة بدلاً من قائمة فارغة تسبب رفض زائف
        if _users_cache["data"] is not None:
            return _users_cache["data"]
        return [], [], [], False, False, [], [], []

def get_owner_ids():
    _, _, owners, _, _, _, _, _ = get_users()
    return owners

def is_owner_id(uid):
    return uid in get_owner_ids()

def is_owner(msg):
    return is_owner_id(msg.from_user.id)

def _is_admin_or_owner(uid):
    _, admins, owners, _, admin_all, _, _, _ = get_users()
    return admin_all or uid in admins or uid in owners

def get_ai_allowed_users():
    _, _, _, _, _, _, ai, _ = get_users()
    return ai

def is_ai_allowed(uid):
    return uid in get_ai_allowed_users()

def get_user_role(uid):
    _, admins, owners, _, admin_all, _, _, _ = get_users()
    if uid in owners:
        return "owner"
    if admin_all or uid in admins:
        return "admin"
    return "user"

def get_all_user_ids():
    allowed, _, _, open_all, _, _, _, _ = get_users()
    if open_all:
        registered = get_all_registered_uids()
        return registered if registered else [], open_all
    return allowed, open_all

def get_all_registered_uids():
    try:
        uids = []
        es = 0
        for row in users_sheet.get_all_values()[1:]:
            if not row or not any(c.strip() for c in row):
                es += 1
                if es >= 5:
                    break
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
        # الأعمدة: الاسم، الهاتف، ID، allowed، admin، owner، lang، log، ai_allowed، auto_publish، ai_switch
        users_sheet.append_row([display, "", uid, allowed, False, False, False, False, False, False, False, False],
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

def get_user_auto_publish(uid):
    try:
        uid_str = str(uid)
        for row in users_sheet.get_all_values()[1:]:
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                auto_val = row[AUTO_PUBLISH_COL].strip().upper() if len(row) > AUTO_PUBLISH_COL else "FALSE"
                return auto_val == "TRUE"
        return False
    except:
        return False

def set_user_auto_publish(uid, enabled):
    try:
        uid_str = str(uid)
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                users_sheet.update_cell(i, AUTO_PUBLISH_COL + 1, enabled)
                return True
        return False
    except Exception as e:
        log_error(f"set_user_auto_publish: {e}")
        return False

def load_user_auto_publish(uid):
    if uid not in user_auto_publish:
        user_auto_publish[uid] = get_user_auto_publish(uid)

def get_user_ai_switch(uid):
    """يقرأ حالة سويتش الذكاء الاصطناعي من الشيت"""
    try:
        uid_str = str(uid)
        for row in users_sheet.get_all_values()[1:]:
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                val = row[AI_SWITCH_COL].strip().upper() if len(row) > AI_SWITCH_COL else "FALSE"
                return val == "TRUE"
        return False
    except:
        return False

def set_user_ai_switch(uid, enabled):
    """يحفظ حالة سويتش الذكاء الاصطناعي في الشيت"""
    try:
        uid_str = str(uid)
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                users_sheet.update_cell(i, AI_SWITCH_COL + 1, enabled)
                return True
        return False
    except Exception as e:
        log_error(f"set_user_ai_switch: {e}")
        return False

def load_user_ai_switch(uid):
    """
    يُحمِّل حالة السويتش من الشيت.
    - إذا AI_PROVIDERS فارغة → السويتش دائماً False في الذاكرة (الزر مخفي)
    - إذا AI_PROVIDERS موجودة → يقرأ الحالة المحفوظة في الشيت (تعلّمها حتى بعد إعادة التشغيل)
    """
    if not AI_PROVIDERS:
        user_ai_enabled[uid] = False
        return
    if uid not in user_ai_enabled:
        user_ai_enabled[uid] = get_user_ai_switch(uid)

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
            if not rp:
                continue
            # مطابقة كاملة
            if rp == pc:
                return i, row
            # مطابقة جزئية: يتطابق إذا أحدهما ينتهي بالآخر (كود الدولة اختياري)
            if rp.endswith(pc) or pc.endswith(rp):
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
# دوال البيانات من الشيت (محاضرات، تكاليف، إلخ)
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

def invalidate_sheet_cache():
    """إبطال cache البيانات فوراً (عند الكتابة أو طلب تحديث يدوي)"""
    _sheet_data_cache["data"] = None
    _sheet_data_cache["ts"]   = 0
    _bot_texts_cache["data"]  = None
    _bot_texts_cache["ts"]    = 0

def get_data():
    global _sheet_data_cache
    now = time.time()
    if _sheet_data_cache["data"] is not None and now - _sheet_data_cache["ts"] < _SHEET_CACHE_TTL:
        return _sheet_data_cache["data"]
    try:
        useful = []
        for r in sheet.get_all_values()[1:]:
            if any(len(r) > i and r[i].strip() for i in range(2, 8)):
                useful.append(r)
        _sheet_data_cache["data"] = useful
        _sheet_data_cache["ts"]   = now
        return useful
    except:
        if _sheet_data_cache["data"] is not None:
            return _sheet_data_cache["data"]
        return []

def get_notes():
    """يقرأ الملازم من عمود I (index 8) في الشيت الرئيسي.
    كل صف فيه بيانات في عمود I يُعرض كملزمة.
    التنسيق: العمود B = اسم المادة، العمود I = رابط أو نص الملزمة.
    """
    try:
        notes = {}  # {subject: [note1, note2, ...]}
        for r in sheet.get_all_values()[1:]:
            subj = r[1].strip() if len(r) > 1 else ""
            note = r[8].strip() if len(r) > 8 else ""
            if subj and note:
                if subj not in notes:
                    notes[subj] = []
                if note not in notes[subj]:
                    notes[subj].append(note)
        return notes
    except Exception as e:
        log_error(f"get_notes: {e}")
        return {}

def save_lecture(date, subject, time_val, room):
    try:
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            row_date = parse_date(safe_get(row, 0)) if safe_get(row, 0) else ""
            row_subj = safe_get(row, 1)
            if row_date == date and row_subj == subject:
                sheet.update_cell(i, 3, time_val)
                sheet.update_cell(i, 4, room)
                log_info(f"save_lecture: تحديث صف {i} | {subject} | {date}")
                return True
        new_row = [""] * 8
        new_row[0] = date
        new_row[1] = subject
        new_row[2] = time_val
        new_row[3] = room
        sheet.append_row(new_row, value_input_option="USER_ENTERED")
        invalidate_sheet_cache()
        log_info(f"save_lecture: إضافة جديدة | {subject} | {date} | {time_val} | {room}")
        # إشعار تلقائي
        all_users, _ = get_all_user_ids()
        title = f"🕐 *محاضرة جديدة*"
        message = f"📌 *{subject}*\n📅 {date}\n🕐 {time_val}\n📍 {room}"
        notify_auto_publish(title, message)
        return True
    except Exception as e:
        log_error(f"save_lecture: {e} | المادة={subject} | التاريخ={date}")
        return False

def save_text_to_cell(date, subject, col, text_val):
    try:
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) and parse_date(safe_get(row, 0)) == date and safe_get(row, 1) == subject:
                existing_fids = get_file_ids(safe_get(row, col))
                new_val = text_val if not existing_fids else f"{text_val}|{','.join(existing_fids)}"
                sheet.update_cell(i, col + 1, new_val)
                invalidate_sheet_cache()
                return True
        new_row = [""] * 8
        new_row[0] = date
        new_row[1] = subject
        new_row[col] = text_val
        sheet.append_row(new_row, value_input_option="USER_ENTERED")
        invalidate_sheet_cache()
        # إشعار تلقائي
        type_name = {4: "تكليف", 6: "ملخص", 7: "تنبيه"}.get(col, "بيانات")
        icon = {4: "📝", 6: "📖", 7: "⚠️"}.get(col, "📌")
        title = f"{icon} *{type_name} جديد*"
        message = f"📌 *{subject}*\n📅 {date}\n📄 {text_val[:200]}"
        notify_auto_publish(title, message)
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

def save_file_to_cell(date, subject, col, fids, merge=False):
    try:
        fids = fids if isinstance(fids, list) else [fids]
        rows = sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) and parse_date(safe_get(row, 0)) == date and safe_get(row, 1) == subject:
                current = safe_get(row, col)
                all_fids = (get_file_ids(current) + fids) if merge else fids
                sheet.update_cell(i, col + 1, merge_cell(get_text(current), all_fids))
                invalidate_sheet_cache()
                return True
        new_row = [""] * 8
        new_row[0] = date
        new_row[1] = subject
        new_row[col] = f"|{','.join(fids)}"
        sheet.append_row(new_row, value_input_option="USER_ENTERED")
        # إشعار تلقائي (للملفات)
        type_name = {4: "تكليف", 6: "ملخص"}.get(col, "ملف")
        icon = {4: "📝", 6: "📖"}.get(col, "📎")
        title = f"{icon} *{type_name} جديد (ملف)*"
        message = f"📌 *{subject}*\n📅 {date}"
        notify_auto_publish(title, message)
        return True
    except Exception as e:
        log_error(f"save_file_to_cell: {e}")
        return False

def merge_cell(text, fids):
    if not fids:
        return text
    fids_str = ",".join(fids) if isinstance(fids, list) else fids
    return f"{text}|{fids_str}" if fids_str else text

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
        lines.append("- `أرسل إشعار للجميع: [النص]` - إرسال إشعار لجميع المستخدمين")
        lines.append("- `بلغ المستخدم [ID] يقول له: [النص]` - إرسال إشعار لمستخدم محدد")
        lines.append("- `فعّل AI للمستخدم [ID]` - تفعيل الذكاء الاصطناعي لمستخدم (للمالك فقط)")
        lines.append("- `عطّل AI للمستخدم [ID]` - تعطيل الذكاء الاصطناعي لمستخدم (للمالك فقط)")
        lines.append("- `اجعل [ID] أدمن/مستخدم` - تغيير رتبة مستخدم (للمالك فقط)")
        lines.append("- `أضف مستخدم [الاسم] ID [ID]` - إضافة مستخدم جديد (للمالك فقط)")
        lines.append("- `أضف محاضرة [المادة] تاريخ [DD/MM/YYYY] وقت [HH:MM-HH:MM] قاعة [القاعة]`")
        lines.append("- `أضف تكليف [المادة] تاريخ [DD/MM/YYYY] نص: [النص]`")
        lines.append("- `أضف ملخص [المادة] تاريخ [DD/MM/YYYY] نص: [النص]`")
        lines.append("- `أضف سعر [المادة] [السعر]`")
        lines.append("- `أضف تنبيه [المادة] تاريخ [DD/MM/YYYY] نص: [النص]`")
        lines.append("- `احذف [محاضرة/تكليف/ملخص/تنبيه] [المادة] تاريخ [DD/MM/YYYY]`")
        lines.append("- `أعد تعيين AI` - إعادة تعيين نموذج الذكاء الاصطناعي (للمالك فقط)")
        lines.append("- `أعطني الملف [file_id]` - استدعاء ملف عبر معرفه (للمالك فقط)")
        lines.append("- `أعطني آخر ملف` - استدعاء آخر ملف تم رفعه (للمالك فقط)")

    return "\n".join(lines)

def get_bot_code_summary(uid):
    """
    دليل البوت الديناميكي — يُبنى تلقائياً من:
    - BOT_TEXTS: أسماء الأزرار الحية (تتغير مع الشيت أو اللغة)
    - get_subjects(): المواد الفعلية من الشيت
    لإضافة ميزة جديدة: أضف bt() key جديد في BOT_TEXTS وأضف السطر هنا.
    """
    lines = []

    # ─── معلومات عامة ───
    lines.append("### معلومات عامة عن البوت ###")
    lines.append("- بوت دراسي لطلاب الجامعة: محاضرات، تكاليف، ملخصات، تنبيهات، أسعار ملازم.")
    lines.append("- قاعدة البيانات: Google Sheets. يدعم العربية والإنجليزية.")
    lines.append("- الأزرار في لوحة المفاتيح أسفل الشاشة.")

    # ─── الرتب ───
    lines.append("\n### الرتب ###")
    lines.append("- مستخدم: عرض البيانات، طلب رفع ملف، مساعد نايف (بإذن المالك).")
    lines.append("- أدمن: إضافة/تعديل/حذف، رفع ملفات، إرسال إشعارات.")
    lines.append("- مالك: كل الصلاحيات + إدارة المستخدمين.")

    # ─── قراءة أسماء الأزرار الحية ───
    B = {k: bt(v, uid) for k, v in {
        "مواد":          "زر_المواد",
        "تاريخ":         "زر_التاريخ",
        "تكاليف":        "زر_التكاليف",
        "جدول":          "زر_الجدول",
        "تنبيهات":       "زر_التنبيهات",
        "اسعار":         "زر_الاسعار",
        "ملخصات":        "زر_الملخصات",
        "طلب_رفع":       "زر_طلب_رفع",
        "رفع_ملف":       "زر_رفع_ملف",
        "رفع_تعليمات":  "زر_رفع_تعليمات",
        "اشعار":         "زر_اشعار",
        "اضافة":         "زر_اضافة",
        "تعديل":         "زر_تعديل",
        "مستخدمين":     "زر_المستخدمين",
        "عوده":          "زر_عوده",
        "يوم":           "زر_يوم",
        "فتره":          "زر_فتره",
        "حسب_ماده":     "زر_حسب_الماده",
        "حسب_تاريخ":    "زر_حسب_التاريخ",
        "خيار_جدول":    "خيار_الجدول",
        "خيار_تكاليف":  "خيار_التكاليف",
        "خيار_سعر":     "خيار_السعر",
        "خيار_ملخص":    "خيار_الملخص",
        "خيار_تنبيه":   "خيار_التنبيهات",
        "اضافة_محاضره": "زر_اضافة_محاضره",
        "اضافة_تكليف":  "زر_اضافة_تكليف",
        "اضافة_ملخص":   "زر_اضافة_ملخص",
        "اضافة_سعر":    "زر_اضافة_سعر",
        "اضافة_تنبيه":  "زر_اضافة_تنبيه",
        "تعديل_محاضره": "زر_تعديل_محاضره",
        "تعديل_تكليف":  "زر_تعديل_تكليف",
        "تعديل_ملخص":   "زر_تعديل_ملخص",
        "تعديل_سعر":    "زر_تعديل_سعر",
        "تعديل_تنبيه":  "زر_تعديل_تنبيه",
        "نشر_تلقائي":   "زر_نشر_تلقائي",
        "مساعد_نايف":   "زر_مساعد_نايف",
    }.items()}

    # ─── المواد الحية من الشيت ───
    try:
        subjects = get_subjects()
        subjects_with_docs = get_subjects_with_doctors()
        if subjects_with_docs:
            # شيت فيه مواد وأساتذة
            subjects_str = " | ".join(
                f"{s} ({', '.join(docs)})" if docs else s
                for s, docs in subjects_with_docs.items()
            )
        elif subjects:
            # شيت فيه مواد بس بدون أساتذة
            subjects_str = " / ".join(subjects)
        else:
            subjects_str = "لا توجد مواد بعد"
    except:
        subjects = []
        subjects_str = "غير متاح"
    lines.append(f"\nالمواد المتاحة حالياً: {subjects_str}")

    # ─── الدليل الكامل (يُبنى من B تلقائياً) ───
    lines.append("\n### كيفية استخدام كل ميزة ###")

    lines.append(f"\n## التكاليف ##")
    lines.append(f"طريقة 1 (مادة معينة): {B['مواد']} ← اسم المادة ← {B['خيار_تكاليف']} ← اختر التاريخ")
    lines.append(f"طريقة 2 (آخر تكليف): {B['تكاليف']}")
    lines.append(f"طريقة 3 (بالتاريخ): {B['تاريخ']} ← {B['يوم']} ← التاريخ ← المادة ← التكاليف")

    lines.append(f"\n## جدول المحاضرات ##")
    lines.append(f"طريقة 1 (آخر يوم): {B['جدول']}")
    lines.append(f"طريقة 2 (مادة معينة): {B['مواد']} ← اسم المادة ← {B['خيار_جدول']} ← اختر التاريخ")
    lines.append(f"طريقة 3 (بالتاريخ): {B['تاريخ']} ← {B['يوم']} ← التاريخ ← المادة ← المحاضرات")

    lines.append(f"\n## الملخصات ##")
    lines.append(f"طريقة 1 (مادة معينة): {B['مواد']} ← اسم المادة ← {B['خيار_ملخص']} ← اختر التاريخ")
    lines.append(f"طريقة 2 (آخر ملخص): {B['ملخصات']}")

    lines.append(f"\n## أسعار الملازم ##")
    lines.append(f"جميع الأسعار: {B['اسعار']}")
    lines.append(f"سعر مادة: {B['مواد']} ← اسم المادة ← {B['خيار_سعر']}")

    lines.append(f"\n## التنبيهات ##")
    lines.append(f"جميع التنبيهات: {B['تنبيهات']}")
    lines.append(f"تنبيهات مادة: {B['مواد']} ← اسم المادة ← {B['خيار_تنبيه']}")

    lines.append(f"\n## البحث بالتاريخ ##")
    lines.append(f"يوم واحد: {B['تاريخ']} ← {B['يوم']} ← اكتب اليوم (مثال: 27 أو 27/03/2026) ← اختر المواد ← اختر نوع البيانات")
    lines.append(f"فترة زمنية: {B['تاريخ']} ← {B['فتره']} ← اكتب الفترة (مثال: 15-27) ← اختر المواد ← اختر نوع البيانات ← اختر طريقة العرض ({B['حسب_ماده']} أو {B['حسب_تاريخ']})")

    lines.append(f"\n## طلب رفع ملف (مستخدم عادي) ##")
    lines.append(f"{B['طلب_رفع']} ← اسم المادة ← {B['اضافة_تكليف']} أو {B['اضافة_ملخص']} ← التاريخ ← أرسل الملف ← ✅ إرسال")
    lines.append("يصل الطلب للأدمن ليوافق أو يرفضه ويُضاف تلقائياً.")

    lines.append(f"\n## مساعد نايف ##")
    lines.append(f"تفعيل: اضغط '🔴 🤖 {B['مساعد_نايف']}' ← يتحول إلى 🟢")
    lines.append(f"إيقاف: اضغطه مرة ثانية ← يتحول إلى 🔴")
    lines.append("شرط مهم: يقرأ رسائلك فقط وأنت في الصفحة الرئيسية. إذا دخلت أي زر، يبقى مفعلاً لكن لا يقرأ حتى تعود.")

    lines.append(f"\n## النشر التلقائي ##")
    lines.append(f"تفعيل: '🔕 {B['نشر_تلقائي']}' ← يتحول إلى 📢")
    lines.append("عند تفعيله تصلك إشعارات عند إضافة أي محتوى جديد.")

    lines.append("\n## تغيير اللغة ##")
    lines.append("/lang ← اختر العربية أو الإنجليزية")

    # ─── ميزات الأدمن/المالك ───
    lines.append("\n### ميزات الأدمن والمالك ###")

    lines.append(f"\n## إضافة بيانات ##")
    lines.append(f"{B['اضافة']} ← اختر النوع:")
    lines.append(f"• {B['اضافة_محاضره']}: التاريخ ← المبنى ← القاعة ← المادة ← الوقت")
    lines.append(f"• {B['اضافة_تكليف']} / {B['اضافة_ملخص']} / {B['اضافة_تنبيه']}: المادة ← التاريخ ← النص")
    lines.append(f"• {B['اضافة_سعر']}: المادة ← السعر")

    lines.append(f"\n## تعديل أو حذف ##")
    lines.append(f"{B['تعديل']} ← اختر ({B['تعديل_محاضره']} / {B['تعديل_تكليف']} / {B['تعديل_ملخص']} / {B['تعديل_سعر']} / {B['تعديل_تنبيه']}) ← المادة ← التاريخ ← تعديل أو حذف")

    lines.append(f"\n## رفع ملف مباشرة ##")
    lines.append(f"{B['رفع_ملف']} ← المادة ← النوع ← التاريخ ← أرسل الملف ← ✅ إرسال")

    lines.append(f"\n## إرسال إشعار ##")
    lines.append(f"{B['اشعار']} ← اكتب النص ← أرسل ملف (اختياري) ← 📤 إرسال الآن")

    lines.append(f"\n## إدارة المستخدمين (مالك) ##")
    lines.append(f"{B['مستخدمين']} ← بحث بالاسم/الرقم/ID أو عرض الكل")
    lines.append("من البطاقة: تعيين أدمن/مستخدم، تفعيل/تعطيل AI، تغيير الاسم")

    lines.append("\n## الأوامر النصية (أدمن/مالك عبر مساعد نايف) ##")
    # أمثلة ديناميكية تستخدم أول مادة موجودة فعلاً
    ex_subj = subjects[0] if subjects else "رياضيات"
    lines.append(f"• أضف محاضرة {ex_subj} يوم 27/03/2026 الساعة 10:00-12:00 قاعة 101")
    lines.append(f"• أضف تكليف {ex_subj} تاريخ 28/03/2026 نص: حل المسائل 1-5")
    lines.append(f"• احذف تكليف {ex_subj} تاريخ 27/03/2026")
    lines.append("• أرسل إشعار للجميع: تذكير بالاختبار غداً")
    lines.append("• فعّل AI للمستخدم 123456789")

    return "\n".join(lines)


def _get_button_description(key):
    """وصف مختصر لكل زر — يُستخدم في السياق العام فقط."""
    desc = {
        "زر_المواد":       "يعرض قائمة المواد. اختر مادة لعرض جدولها، تكاليفها، ملخصاتها، تنبيهاتها، أو سعرها.",
        "زر_التاريخ":      "بحث بالتاريخ: يوم واحد أو فترة زمنية.",
        "زر_التكاليف":     "آخر التكاليف لجميع المواد.",
        "زر_الجدول":       "محاضرات آخر يوم دراسي.",
        "زر_التنبيهات":    "جميع التنبيهات الحالية.",
        "زر_الاسعار":      "أسعار الملازم لجميع المواد.",
        "زر_الملخصات":     "آخر الملخصات المضافة.",
        "زر_طلب_رفع":      "للمستخدم: طلب رفع ملف للأدمن.",
        "زر_رفع_ملف":      "للأدمن: رفع ملف مباشرة.",
        "زر_رفع_تعليمات": "للأدمن: رفع تعليمات للمستخدمين أو الأدمن.",
        "زر_اشعار":        "للأدمن: إرسال إشعار لجميع المستخدمين.",
        "زر_اضافة":        "للأدمن: إضافة محاضرة، تكليف، ملخص، سعر، أو تنبيه.",
        "زر_تعديل":        "للأدمن: تعديل أو حذف البيانات.",
        "زر_المستخدمين":   "للمالك: إدارة المستخدمين وصلاحياتهم.",
        "زر_عوده":         "العودة للقائمة الرئيسية.",
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
        "زر_الاسعار", "زر_الملخصات", "زر_طلب_رفع", "زر_رفع_ملف", "زر_رفع_تعليمات", "زر_الملازم",
        "زر_اشعار", "زر_اضافة", "زر_تعديل", "زر_المستخدمين", "زر_عوده",
        "زر_يوم", "زر_فتره", "زر_تحديد_الكل", "زر_تم_التحديد", "زر_حسب_الماده",
        "زر_حسب_التاريخ", "زر_اضافة_محاضره", "زر_اضافة_تكليف", "زر_اضافة_ملخص",
        "زر_اضافة_سعر", "زر_اضافة_تنبيه", "زر_اضافة_ملزمه", "زر_تعديل_محاضره", "زر_تعديل_تكليف",
        "زر_تعديل_ملخص", "زر_تعديل_سعر", "زر_تعديل_تنبيه", "زر_تعديل_ملزمه", "زر_تعديل_زرار", "زر_حذف_زرار"
    ]
    for key in button_keys:
        BUTTON_TEXTS.add(bt(key))
    BUTTON_TEXTS.update([
        "↩️ رجوع خطوة",
        "🤖 مساعد نايف", "🟢 🤖 مساعد نايف", "🔴 🤖 مساعد نايف",
        "📢 النشر التلقائي", "🔕 النشر التلقائي",
        "📤 إرسال الآن", "✅ إرسال", "➕ إضافة محاضرة أخرى",
        "🚫 لا يوجد", "⏭️ تخطي", "🔄 استبدال", "✏️ بجانبه", "🔄 بدله",
        "✅ نعم، احذف", "❌ إلغاء", "📤 إرسال بدون نص", "👤 للمستخدمين",
        "👑 للأدمن", "👤 تعليمات المستخدم", "👑 تعليمات الأدمن",
        "🔍 بحث عن مستخدم",
        "🇾🇪 العربية", "🇬🇧 English", "📋 عرض جميع المستخدمين", "📋 آخر 3 مستخدمين"
    ])

def main_menu(uid, admin=False, owner=False):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    if admin or owner:
        m.row(bt("زر_التاريخ", uid), bt("زر_المواد", uid))
        m.row(bt("زر_التكاليف", uid), bt("زر_الجدول", uid))
        m.row(bt("زر_الاسعار", uid), bt("زر_الملخصات", uid), bt("زر_التنبيهات", uid))
        m.row(bt("زر_الملازم", uid))
        m.row(bt("زر_تعديل", uid), bt("زر_اضافة", uid))
        m.row(bt("زر_اشعار", uid), bt("زر_رفع_ملف", uid), bt("زر_رفع_تعليمات", uid))
        if owner:
            m.add(bt("زر_المستخدمين", uid))
    else:
        m.row(bt("زر_التاريخ", uid), bt("زر_المواد", uid))
        m.row(bt("زر_التكاليف", uid), bt("زر_الجدول", uid), bt("زر_الملخصات", uid))
        m.row(bt("زر_الاسعار", uid), bt("زر_طلب_رفع", uid), bt("زر_التنبيهات", uid))
        m.row(bt("زر_الملازم", uid))

    row_switches = []
    if AI_PROVIDERS:  # يوجد مزود AI نشط → أظهر أزرار السويتش
        load_user_auto_publish(uid)
        pub_status = "📢" if user_auto_publish.get(uid, False) else "🔕"
        row_switches.append(f"{pub_status} {bt('زر_نشر_تلقائي', uid)}")
        ai_status = "🟢" if user_ai_enabled.get(uid, False) else "🔴"
        row_switches.append(f"{ai_status} 🤖 {bt('زر_مساعد_نايف', uid)}")
    if row_switches:
        m.row(*row_switches)

    return m

def back_only_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add(bt("زر_عوده", uid))
    return m

def back_step_menu(uid):
    """زر رجوع خطوة + خروج — يُستخدم داخل flows متعددة الخطوات"""
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row("↩️ رجوع خطوة", bt("زر_عوده", uid))
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
    for k in ["خيار_الجدول", "خيار_التكاليف", "خيار_السعر", "خيار_الملخص", "خيار_التنبيهات", "خيار_الملزمه"]:
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
    m.row(bt("زر_اضافة_تنبيه", uid), bt("زر_اضافة_ملزمه", uid))
    m.add(bt("زر_عوده", uid))
    return m

def edit_data_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row(bt("زر_تعديل_محاضره", uid), bt("زر_تعديل_تكليف", uid))
    m.row(bt("زر_تعديل_ملخص", uid), bt("زر_تعديل_سعر", uid))
    m.row(bt("زر_تعديل_تنبيه", uid), bt("زر_تعديل_ملزمه", uid))
    m.add(bt("زر_عوده", uid))
    return m

def edit_action_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(bt("زر_تعديل_زرار", uid), bt("زر_حذف_زرار", uid))
    m.row("↩️ رجوع خطوة", bt("زر_عوده", uid))
    return m

def buildings_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("🏛 القديم", "🏫 الاداب")
    m.row("↩️ رجوع خطوة", bt("زر_عوده", uid))
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
    m.add("لا يوجد")
    m.row("↩️ رجوع خطوة", bt("زر_عوده", uid))
    return m

def manage_users_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row("🔍 بحث عن مستخدم", "📋 آخر 3 مستخدمين")
    m.row("📋 عرض جميع المستخدمين", "🔙 العودة")
    return m

def _smart_search_user(query):
    """
    يبحث في الثلاثة حقول في نفس الوقت: ID + رقم الهاتف + الاسم
    ويجمع النتائج بدون تكرار.
    """
    # دعم #اسم_المستخدم → اسم المستخدم
    q = query.strip().lstrip('#').replace('_', ' ').strip()
    clean = re.sub(r'[\s\-\+]', '', query.strip().lstrip('#'))
    found_uids = set()
    results = []

    try:
        rows = users_sheet.get_all_values()[1:]
    except:
        return None, "all"

    for row in rows:
        if not row or not any(c.strip() for c in row):
            continue
        uid_str = row[2].strip().lstrip("'") if len(row) > 2 else ""
        if not uid_str.isdigit():
            continue
        name  = row[0].strip()
        phone = re.sub(r'[\s\-\+]', '', row[1].strip() if len(row) > 1 else "")

        matched = False

        # 1. تطابق ID
        if clean and uid_str == clean:
            matched = True

        # 2. تطابق رقم الهاتف (جزئي — يقبل مع/بدون كود الدولة)
        if clean and phone and (phone == clean or phone.endswith(clean) or clean.endswith(phone)):
            matched = True

        # 3. تطابق الاسم (جزء من الاسم)
        if q and len(q) >= 2:
            name_clean = name.replace("🆕️", "").replace("🆕", "").strip()
            if q.lower() in name_clean.lower():
                matched = True

        if matched and uid_str not in found_uids:
            found_uids.add(uid_str)
            results.append(row)

    if not results:
        return None, "all"
    if len(results) == 1:
        return results[0], "all"
    return results, "all"

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
    """يجلب المواد من الشيت الرئيسي وشيت القاعات والمواد معاً"""
    try:
        seen, result = set(), []
        # أولاً: من شيت القاعات والمواد (العمود D)
        if rooms_sheet:
            try:
                for row in rooms_sheet.get_all_values()[1:]:
                    s = row[3].strip() if len(row) > 3 else ""
                    if s and s not in seen:
                        seen.add(s)
                        result.append(s)
            except:
                pass
        # ثانياً: من الشيت الرئيسي (العمود B)
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
    """يجلب قائمة القاعات حسب المبنى — يتجاهل السطر الأول (headers)"""
    try:
        if not rooms_sheet:
            return []
        rows = rooms_sheet.get_all_values()[1:]  # تخطي header
        return [r[1].strip() for r in rows
                if len(r) > 1 and r[0].strip() == building and r[1].strip()]
    except:
        return []

def get_subject_doctor(subject):
    """
    يرجع اسم الدكتور الافتراضي لمادة معينة.
    يعمل فقط إذا كان العمود D (المادة) مُعبَّأ في الشيت.
    إذا كان هناك أكثر من دكتور لنفس المادة يعتمد الأول.
    """
    try:
        if not rooms_sheet:
            return ""
        rows = rooms_sheet.get_all_values()[1:]
        for r in rows:
            if len(r) > 3 and r[3].strip() == subject and r[2].strip():
                return r[2].strip()
        return ""
    except:
        return ""

def get_subjects_with_doctors():
    """
    يرجع قاموس {اسم_المادة: [قائمة_الأساتذة]} من الشيت.
    يشتغل فقط إذا كان العمود D (المادة) مُعبَّأ.
    إذا العمود فارغ يرجع قاموس فارغ (الشيت الحالي).
    """
    try:
        if not rooms_sheet:
            return {}
        result = {}
        rows = rooms_sheet.get_all_values()[1:]
        for r in rows:
            doctor  = r[2].strip() if len(r) > 2 else ""
            subject = r[3].strip() if len(r) > 3 else ""
            if subject:  # فقط إذا عمود المادة مُعبَّأ
                if subject not in result:
                    result[subject] = []
                if doctor and doctor not in result[subject]:
                    result[subject].append(doctor)
        return result
    except:
        return {}

def get_last_lectures_for_subject(subject, n=3):
    try:
        seen, dates = set(), []
        for r in get_data():
            s = safe_get(r, 1); d = safe_get(r, 0); t = safe_get(r, 2)
            if s == subject and d and t:
                p = parse_date(d)
                if p not in seen:
                    seen.add(p); dates.append(p)
        dates.sort(key=lambda x: datetime.strptime(x, "%d/%m/%Y"), reverse=True)
        return dates[:n]
    except:
        return []

def date_suggestions_menu(subject=None, for_lecture=False, for_alert=False, uid=None):
    """
    يرجع ReplyKeyboardMarkup بأزرار التواريخ المقترحة.
    الترتيب: الأحدث في الأعلى (غد → اليوم → أمس → قديم من الشيت)
    """
    now = datetime.now(YEMEN_TZ)
    yesterday = (now - timedelta(days=1)).strftime("%d/%m/%Y")
    today     = now.strftime("%d/%m/%Y")
    tmrw      = (now + timedelta(days=1)).strftime("%d/%m/%Y")

    if for_lecture or for_alert:
        # غد، اليوم، أمس
        dates = [tmrw, today, yesterday]
    else:
        # اليوم، أمس، ثم تواريخ قديمة من الشيت (الأحدث أولاً)
        dates = [today, yesterday]
        if subject:
            try:
                for d in get_last_lectures_for_subject(subject, 3):
                    if d not in dates:
                        dates.append(d)
            except:
                pass
        dates = dates[:4]

    m = telebot.types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    for d in dates:
        m.add(d)
    back = bt("زر_عوده", uid) if uid else "🔙 العودة"
    m.add(back)
    return m

def send_date_suggestions(chat_id, subject=None, for_lecture=False, for_alert=False, uid=None):
    """للتوافق الخلفي — لم تعد ترسل رسالة منفصلة."""
    pass

def get_settings():
    return bt("رسالة_الترحيب"), bt("رسالة_الرفض")

# ─────────────────────────────────────────────────────
# دوال الأوامر الإدارية النصية (محسنة للغة الطبيعية)
# ─────────────────────────────────────────────────────
def normalize_name(text):
    # أزل # واستبدل _ بمسافة (لدعم #عبدالله_حسن_منصور)
    text = text.lstrip('#').replace('_', ' ').strip()
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    text = re.sub(r'[أآإ]', 'ا', text)
    text = re.sub(r'[ؤ]', 'و', text)
    text = re.sub(r'[ئ]', 'ي', text)
    text = re.sub(r'[ى]', 'ي', text)
    text = re.sub(r'^ال', '', text)
    text = re.sub(r'\s+ال', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    text = ' '.join(text.split())
    return text.strip().lower()

def search_users_by_name(query):
    try:
        normalized_query = normalize_name(query)
        if not normalized_query:
            return []
        query_words = set(normalized_query.split())
        rows = users_sheet.get_all_values()
        matches = []
        for row in rows[1:]:
            if len(row) < 3:
                continue
            uid_str = row[2].strip().lstrip("'")
            if not uid_str.isdigit():
                continue
            name = row[0].strip() if len(row) > 0 else ""
            if not name:
                continue
            normalized_name = normalize_name(name)
            name_words = set(normalized_name.split())
            if normalized_query in normalized_name:
                matches.append((row, 3))
            elif query_words.issubset(name_words):
                matches.append((row, 2))
            elif any(word in normalized_name for word in query_words):
                matches.append((row, 1))
            elif normalized_name in normalized_query:
                matches.append((row, 1))
        matches.sort(key=lambda x: x[1], reverse=True)
        return [row for row, _ in matches[:10]]
    except Exception as e:
        log_error(f"search_users_by_name: {e}")
        return []

def get_last_users(n=3):
    try:
        rows = users_sheet.get_all_values()
        data_rows = []
        for row in rows[1:]:
            if not row or not any(c.strip() for c in row):
                continue
            uid_str = row[2].strip().lstrip("'") if len(row) > 2 else ""
            if not uid_str.isdigit():
                continue
            data_rows.append(row)
        data_rows.reverse()
        return data_rows[:n]
    except Exception as e:
        log_error(f"get_last_users: {e}")
        return []

def notify_auto_publish(title, message, file_ids=None):
    _, _, _, _, _, _, _, auto_publish_uids = get_users()
    if not auto_publish_uids:
        return
    full_msg = f"{title}\n━━━━━━━━━━━━━━━━━━━━\n{message}"
    success = 0
    fail = 0
    for uid in auto_publish_uids:
        try:
            if file_ids:
                for fid in file_ids:
                    _try_send_file(uid, fid, caption=full_msg[:1024])
            else:
                bot.send_message(uid, full_msg, parse_mode="Markdown")
            success += 1
        except:
            fail += 1
    if success > 0:
        log_info(f"إشعارات تلقائية: {success} نجاح, {fail} فشل")

def log_data_addition(adder_uid, item_type, details):
    """إرسال تقرير إلى بوت اللوج عند إضافة بيانات"""
    if not LOG_BOT_TOKEN:
        return
    name, phone = _get_user_name_phone(adder_uid)
    role_icon = _get_role_icon(adder_uid)
    msg = (f"📝 *إضافة {item_type}*\n"
           f"👤 {name} (ID: `{adder_uid}`)\n"
           f"📌 {details}")
    try:
        _requests.post(
            f"https://api.telegram.org/bot{LOG_BOT_TOKEN}/sendMessage",
            json={"chat_id": LOG_BOT_TOKEN, "text": msg, "parse_mode": "Markdown"},
            timeout=5
        )
    except:
        pass

def send_or_update_log(user_id, user_name, phone, role, ai_status, actor):
    """إرسال أو تحديث بطاقة المستخدم في بوت اللوج (بدون أزرار)"""
    if not LOG_BOT_TOKEN:
        return
    icon = {"مالك": "👑", "أدمن": "⭐", "مستخدم": "👤", "غير مصرح": "❌"}.get(role, "❌")
    ai_icon = "🤖" if ai_status == "مفعل" else "🚫"
    ph = f"\n📞 `{phone}`" if phone else ""
    text = (f"{icon} *{user_name}*\n🆔 `{user_id}`{ph}\n{ai_icon} AI: {ai_status}\n{'─' * 23}\n"
            f"🔧 {actor}")

    try:
        if user_id in _log_messages:
            old = _log_messages[user_id]
            bot.edit_message_text(text, old["chat_id"], old["message_id"], parse_mode="Markdown")
        else:
            msg = bot.send_message(LOG_BOT_TOKEN, text, parse_mode="Markdown")
            _log_messages[user_id] = {"chat_id": LOG_BOT_TOKEN, "message_id": msg.message_id}
    except Exception as e:
        log_error(f"فشل إرسال/تحديث اللوج للمستخدم {user_id}: {e}")

def get_last_file_id_from_log():
    """جلب آخر file_id من رسائل بوت اللوج"""
    if not LOG_BOT_TOKEN:
        return None
    try:
        url = f"https://api.telegram.org/bot{LOG_BOT_TOKEN}/getUpdates"
        params = {"limit": 50}
        resp = _requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data.get("ok"):
            return None
        for update in reversed(data.get("result", [])):
            if "message" not in update:
                continue
            msg = update["message"]
            text = msg.get("text", "")
            if "نايف" in text:
                match = re.search(r'🆔 `([^`]+)`', text)
                if match:
                    return match.group(1)
        return None
    except Exception as e:
        log_error(f"get_last_file_id_from_log: {e}")
        return None

def get_file_id_from_log(keyword):
    """البحث عن file_id في سجل اللوج باستخدام كلمة مفتاحية"""
    if not LOG_BOT_TOKEN:
        return None
    try:
        url = f"https://api.telegram.org/bot{LOG_BOT_TOKEN}/getUpdates"
        params = {"limit": 100}
        resp = _requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data.get("ok"):
            return None
        for update in reversed(data.get("result", [])):
            if "message" not in update:
                continue
            msg = update["message"]
            text = msg.get("text", "")
            if "نايف" in text and keyword in text:
                match = re.search(r'🆔 `([^`]+)`', text)
                if match:
                    return match.group(1)
        return None
    except Exception as e:
        log_error(f"get_file_id_from_log: {e}")
        return None

def get_help_file_id(key, file_type="photo"):
    """استرجاع file_id من صفحة المساعدة حسب المفتاح"""
    try:
        rows = help_sheet.get_all_values()
        for row in rows:
            if len(row) >= 3 and row[0].strip() == key and row[2].strip() == file_type:
                return row[1].strip()
        return None
    except Exception as e:
        log_error(f"get_help_file_id: {e}")
        return None

def try_execute_admin_command(text, uid, user_role, chat_id, bot_instance):
    if user_role not in ("admin", "owner"):
        return False, None

    text = text.strip()

    # كشف النص الذي يحتوي على عناوين مرقمة مثل "١/ ... ٢/ ..."
    pattern_multi = r'(\d+[\/\-\–]\s*[^\n]+(?:\n[^\d].*)*)'
    matches = re.findall(pattern_multi, text)
    if len(matches) > 1:
        short_key = f"multi_{int(time.time())}_{uid}"
        _temp_admin_actions[short_key] = {
            "uid": uid,
            "data": matches,
            "original": text,
            "expires": time.time() + 300
        }
        preview = "\n".join([f"📌 {item.strip()}" for item in matches])
        markup = telebot.types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            _make_inline("زر_confirm_multi", "✅ إرسال", f"confirm_multi_{short_key}"),
            _make_inline("زر_edit_multi",    "✏️ تعديل", f"edit_multi_{short_key}"),
            _make_inline("زر_reject_multi",  "❌ رفض",   f"reject_multi_{short_key}"),
        )
        return True, f"📋 *سيتم إضافة البيانات التالية:*\n\n{preview}\n\nهل تريد المتابعة؟", markup

    # إعادة تعيين نموذج AI
    pattern_reset_ai = r'(?:أعد|إعادة)?\s*تعيين\s*(?:نموذج)?\s*(?:الذكاء الاصطناعي|AI|النموذج)|ai_reset'
    m = re.search(pattern_reset_ai, text, re.IGNORECASE)
    if m:
        if user_role != "owner":
            return True, "⛔ هذا الأمر يتطلب صلاحية المالك."
        ai_reset_model()
        return True, f"✅ تم إعادة تعيين نموذج الذكاء الاصطناعي."

    # إرسال إشعار لمستخدم محدد
    pattern_broadcast_user = r'(?:أرسل إشعار للمستخدم|بلغ|أرسل إشعار لـ?)\s*(\d+)\s*(?:(?:يقول له|النص:?)\s*(.+))?'
    m = re.search(pattern_broadcast_user, text, re.IGNORECASE)
    if m:
        target_uid = int(m.group(1))
        broadcast_text = m.group(2).strip() if m.group(2) else ""
        if not broadcast_text:
            return True, "❌ يجب إدخال نص الإشعار. مثال: بلغ المستخدم 123456789 يقول له مرحباً"
        _, row = find_user_row_by_id(target_uid)
        if not row:
            return True, f"⚠️ لم أجد مستخدم بالـ ID {target_uid}"
        try:
            bot_instance.send_message(target_uid, f"📢 *إشعار:*\n\n{broadcast_text}", parse_mode="Markdown")
            return True, f"✅ تم إرسال الإشعار للمستخدم {target_uid}"
        except:
            return True, f"❌ فشل إرسال الإشعار للمستخدم {target_uid}"

    # إرسال إشعار للجميع
    pattern_broadcast_all = r'(?:أرسل إشعار للجميع|بلغ الجميع|أعلن)\s*(.+)'
    m = re.search(pattern_broadcast_all, text, re.IGNORECASE)
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
            return False, "❌ يجب إدخال نص الإشعار."

    # إضافة محاضرة
    pattern_lecture = r'(?:أضف|إضافة)\s*محاضرة\s*(?:مادة\s*)?([^\s]+)\s*(?:يوم\s*)?(\d{1,2}/\d{1,2}/\d{4}|\d{1,2})\s*(?:الساعة|وقت)?\s*(\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})\s*(?:قاعة\s*)?(.+)'
    m = re.search(pattern_lecture, text, re.IGNORECASE)
    if m:
        subject = m.group(1).strip()
        date_str = m.group(2).strip()
        time_val = m.group(3).strip()
        room = m.group(4).strip()
        if date_str.isdigit():
            date_str = smart_date_from_day(int(date_str))
        if not is_valid_date(date_str):
            return True, f"❌ التاريخ '{date_str}' غير صحيح. استخدم صيغة DD/MM/YYYY أو رقم اليوم فقط"
        if save_lecture(date_str, subject, time_val, room):
            log_data_addition(uid, "محاضرة", f"{subject} - {date_str}")
            return True, f"✅ تم إضافة المحاضرة:\n📌 {subject}\n📅 {date_str}\n🕐 {time_val}\n📍 {room}"
        return True, "❌ حدث خطأ أثناء الإضافة"

    # إضافة تكليف
    pattern_task = r'(?:أضف|إضافة)\s*(?:تكليف|واجب)\s*(?:مادة\s*)?([^\s]+)\s*(?:تاريخ\s*)?(\d{1,2}/\d{1,2}/\d{4})\s*(?:نص\s*)?(.+)'
    m = re.search(pattern_task, text, re.IGNORECASE)
    if m:
        subject = m.group(1).strip()
        date = m.group(2).strip()
        task_text = m.group(3).strip()
        if not is_valid_date(date):
            return True, "❌ التاريخ غير صحيح."
        if save_text_to_cell(date, subject, 4, task_text):
            log_data_addition(uid, "تكليف", f"{subject} - {date}")
            return True, f"✅ تم إضافة التكليف:\n📌 {subject}\n📅 {date}\n📝 {task_text}"
        return True, "❌ خطأ في الحفظ"

    # إضافة ملخص
    pattern_summary = r'(?:أضف|إضافة)\s*ملخص\s*(?:مادة\s*)?([^\s]+)\s*(?:تاريخ\s*)?(\d{1,2}/\d{1,2}/\d{4})\s*(?:نص\s*)?(.+)'
    m = re.search(pattern_summary, text, re.IGNORECASE)
    if m:
        subject = m.group(1).strip()
        date = m.group(2).strip()
        summary_text = m.group(3).strip()
        if not is_valid_date(date):
            return True, "❌ التاريخ غير صحيح."
        if save_text_to_cell(date, subject, 6, summary_text):
            log_data_addition(uid, "ملخص", f"{subject} - {date}")
            return True, f"✅ تم إضافة الملخص:\n📌 {subject}\n📅 {date}\n📖 {summary_text}"
        return True, "❌ خطأ في الحفظ"

    # إضافة سعر
    pattern_price = r'(?:أضف|إضافة)\s*سعر\s*(?:مادة\s*)?([^\s]+)\s*(?:سعر\s*)?(.+)'
    m = re.search(pattern_price, text, re.IGNORECASE)
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
        log_data_addition(uid, "سعر", f"{subject} - {price}")
        return True, f"✅ تم تحديث سعر مادة {subject} إلى {price}"

    # إضافة تنبيه
    pattern_alert = r'(?:أضف|إضافة)\s*تنبيه\s*(?:مادة\s*)?([^\s]+)\s*(?:تاريخ\s*)?(\d{1,2}/\d{1,2}/\d{4})\s*(?:نص\s*)?(.+)'
    m = re.search(pattern_alert, text, re.IGNORECASE)
    if m:
        subject = m.group(1).strip()
        date = m.group(2).strip()
        alert_text = m.group(3).strip()
        if not is_valid_date(date):
            return True, "❌ التاريخ غير صحيح."
        if save_text_to_cell(date, subject, 7, alert_text):
            log_data_addition(uid, "تنبيه", f"{subject} - {date}")
            return True, f"✅ تم إضافة التنبيه:\n📌 {subject}\n📅 {date}\n⚠️ {alert_text}"
        return True, "❌ خطأ في الحفظ"

    # حذف عنصر
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
                return True, f"❌ لم يتم العثور على {type_word} للمادة {subject} بتاريخ {date}"
        else:
            return True, "النوع غير معروف."

    # تغيير رتبة مستخدم (للمالك فقط)
    pattern_change_role = r'(?:اجعل|حول|غير)\s*(?:المستخدم)?\s*(\d+)\s*(أدمن|مستخدم)'
    m = re.search(pattern_change_role, text, re.IGNORECASE)
    if m:
        if user_role != "owner":
            return True, "⛔ هذا الأمر يتطلب صلاحية المالك."
        target_uid = int(m.group(1))
        target_role = m.group(2).strip()
        try:
            rows = users_sheet.get_all_values()
            for i, row in enumerate(rows[1:], start=2):
                if len(row) > 2 and row[2].strip().lstrip("'") == str(target_uid):
                    if target_role == "أدمن":
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
                    update_user_card_in_chat(target_uid, chat_id)
                    return True, f"✅ تم تغيير رتبة المستخدم {name} إلى {role_name}"
            return True, f"❌ لم أجد المستخدم {target_uid}"
        except Exception as e:
            log_error(f"change_role: {e}")
            return True, "❌ حدث خطأ أثناء تغيير الرتبة"

    # تفعيل/تعطيل AI لمستخدم (للمالك فقط)
    pattern_toggle_ai = r'(?:فعّل|عطّل|تفعيل|تعطيل)\s*AI\s*(?:للمستخدم)?\s*(\d+)'
    m = re.search(pattern_toggle_ai, text, re.IGNORECASE)
    if m:
        if user_role != "owner":
            return True, "⛔ هذا الأمر يتطلب صلاحية المالك."
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
            notify_owners_action(target_uid, name, "", f"أمر من {uid}", "ai_enabled" if is_enable else "ai_disabled")
            update_user_card_in_chat(target_uid, chat_id)
            return True, f"✅ تم {status} AI للمستخدم {name} (ID: {target_uid})"
        else:
            return True, f"❌ فشل تغيير صلاحية AI للمستخدم {target_uid}"

    # إضافة مستخدم جديد (للمالك فقط)
    pattern_add_user = r'(?:أضف|إضافة)\s*مستخدم\s*(.+?)(?:\s+ID\s*(\d+))?'
    m = re.search(pattern_add_user, text, re.IGNORECASE)
    if m:
        if user_role != "owner":
            return True, "⛔ هذا الأمر يتطلب صلاحية المالك."
        name = m.group(1).strip()
        uid_str = m.group(2) if m.group(2) else ""
        if uid_str and uid_str.isdigit():
            new_uid = int(uid_str)
            _, row = find_user_row_by_id(new_uid)
            if row:
                return True, f"⚠️ المستخدم {new_uid} موجود بالفعل."
            if add_user_to_sheet(name, new_uid, auto=False, allowed=True):
                notify_owners_action(new_uid, name, "", f"أمر من {uid}", "approve")
                return True, f"✅ تم إضافة المستخدم {name} (ID: {new_uid}) بنجاح."
            else:
                return True, "❌ حدث خطأ أثناء إضافة المستخدم."
        else:
            return False, "❌ يجب إدخال ID صحيح. مثال: أضف مستخدم أحمد 123456789"

    # استدعاء ملف عبر file_id مباشرة (للمالك فقط)
    pattern_file_by_id = r'(?:أعطني|ابعتلي|أرسل)\s*الملف\s*[`]?([a-zA-Z0-9_\-]+)[`]?'
    m = re.search(pattern_file_by_id, text, re.IGNORECASE)
    if m:
        if user_role != "owner":
            return True, "⚠️ لا يوجد ملف بهذا الاسم."
        file_id = m.group(1).strip()
        if file_id:
            try:
                _try_send_file(chat_id, file_id, caption="📎 الملف المطلوب")
                return True, f"✅ تم إرسال الملف"
            except:
                return True, f"❌ فشل إرسال الملف"
        else:
            return True, "⚠️ لا يوجد ملف بهذا الاسم."

    # استدعاء آخر ملف في بوت اللوج (للمالك فقط)
    pattern_last_file = r'(?:أعطني|ابعتلي|أرسل)\s*(?:آخر|اخر)\s*(?:ملف|صورة|فيديو)'
    m = re.search(pattern_last_file, text, re.IGNORECASE)
    if m:
        if user_role != "owner":
            return True, "⚠️ لا يوجد ملف بهذا الاسم."
        file_id = get_last_file_id_from_log()
        if file_id:
            try:
                _try_send_file(chat_id, file_id, caption="📎 آخر ملف مرفوع")
                return True, f"✅ تم إرسال آخر ملف"
            except:
                return True, f"❌ فشل إرسال الملف"
        else:
            return True, "⚠️ لا يوجد ملفات في سجل اللوج"

    # استدعاء ملف عبر الكلمة المفتاحية (للمالك فقط)
    pattern_get_by_keyword = r'(?:أعطني|ابعتلي|أرسل)\s*(?:الملف|الصورة|الفيديو)\s*(.+)'
    m = re.search(pattern_get_by_keyword, text, re.IGNORECASE)
    if m:
        if user_role != "owner":
            return True, "⚠️ لا يوجد ملف بهذا الاسم."
        keyword = m.group(1).strip()
        # البحث في القاموس المحلي أولاً
        if keyword in _naif_files:
            file_id = _naif_files[keyword]
            try:
                _try_send_file(chat_id, file_id, caption=f"📎 الملف المطلوب: {keyword}")
                return True, f"✅ تم إرسال الملف: {keyword}"
            except:
                return True, f"❌ فشل إرسال الملف"
        # البحث في بوت اللوج
        file_id = get_file_id_from_log(keyword)
        if file_id:
            _naif_files[keyword] = file_id
            try:
                _try_send_file(chat_id, file_id, caption=f"📎 الملف المطلوب: {keyword}")
                return True, f"✅ تم إرسال الملف: {keyword}"
            except:
                return True, f"❌ فشل إرسال الملف"
        else:
            return True, f"⚠️ لا يوجد ملف بهذا الاسم."

    return False, None

def update_user_card_in_chat(user_id, chat_id):
    """تحديث بطاقة المستخدم في الدردشة المحددة إذا كانت موجودة"""
    if user_id in _user_card_messages:
        old = _user_card_messages[user_id]
        if old["chat_id"] == chat_id:
            _, row = find_user_row_by_id(user_id)
            if row:
                send_user_card(chat_id, row, edit_existing=True)

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
    openrouter_key = None
    for p in AI_PROVIDERS:
        if p["provider"] == "openrouter":
            openrouter_key = p["api_key"]
            break
    if not openrouter_key:
        return None
    try:
        file_info = bot.get_file(file_id)
        file_path = file_info.file_path
        file_url = f"https://api.telegram.org/file/bot{STUDY_BOT_TOKEN}/{file_path}"
        response = _requests.get(file_url)
        if response.status_code != 200:
            log_error(f"فشل تحميل الملف الصوتي: {response.status_code}")
            return None
        headers = {"Authorization": f"Bearer {openrouter_key}"}
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
# دوال إشعارات المالكين (مع منع التكرار)
# ─────────────────────────────────────────────────────
_last_notifications = {}
_NOTIFICATION_COOLDOWN = 10

def notify_owners_new_request(requester_id, requester_name, phone=""):
    owners = get_owner_ids()
    _approval_counter[0] += 1
    short_key = str(_approval_counter[0])
    _approval_store[short_key] = {
        "requester_id": requester_id,
        "requester_name": requester_name,
        "phone": phone,
    }
    ph = f"\n📞 `{phone}`" if phone else ""
    text = (f"👤 *طلب انضمام جديد*\n━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {requester_name}\n🆔 `{requester_id}`{ph}\n"
            f"━━━━━━━━━━━━━━━━━━━━")
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        _make_inline("زر_approve_admin",  "⭐ أدمن",         f"approve_role_admin_{short_key}"),
        _make_inline("زر_approve_user",   "👤 مستخدم",       f"approve_role_user_{short_key}"),
    )
    markup.row(
        _make_inline("زر_approve_rename", "✏️ تغيير الاسم",  f"approve_rename_{short_key}"),
        _make_inline("زر_approve_ai",     "🤖 تفعيل AI",     f"approve_ai_on_{short_key}"),
        _make_inline("زر_reject",         "❌ رفض",           f"reject_{short_key}"),
    )
    if requester_id not in request_msg_ids:
        request_msg_ids[requester_id] = {}
    for oid in owners:
        try:
            sent = bot.send_message(oid, text, parse_mode="Markdown", reply_markup=markup)
            request_msg_ids[requester_id][oid] = sent.message_id
        except:
            pass

def notify_owners_action(target_id, target_name, phone, actor, action):
    # منع التكرار
    notification_key = f"{target_id}_{action}_{actor}"
    now = time.time()
    if notification_key in _last_notifications:
        if now - _last_notifications[notification_key] < _NOTIFICATION_COOLDOWN:
            return
    _last_notifications[notification_key] = now
    if len(_last_notifications) > 100:
        for key in list(_last_notifications.keys()):
            if now - _last_notifications[key] > 3600:
                del _last_notifications[key]

    # تحديد إذا كان الفاعل هو المالك نفسه (من خلال البوت) → لا نرسل إشعار
    is_external = (actor in ("الشيت", "الكود السري") or actor.startswith("أمر من"))
    if not is_external:
        return

    # هنا التغيير خارجي (شيت أو كود سري) → نرسل إلى بوت اللوج فقط
    _, row = find_user_row_by_id(target_id)
    if row:
        name = row[0].strip()
        phone = row[1].strip() if len(row) > 1 else ""
        allowed = (row[3].strip().upper() if len(row) > 3 else "FALSE") == "TRUE"
        admin = (row[4].strip().upper() if len(row) > 4 else "FALSE") == "TRUE"
        owner = (row[5].strip().upper() if len(row) > 5 else "FALSE") == "TRUE"
        ai_allowed = (row[AI_ALLOWED_COL].strip().upper() if len(row) > AI_ALLOWED_COL else "FALSE") == "TRUE"
        if owner:
            role = "مالك"
        elif admin:
            role = "أدمن"
        elif allowed:
            role = "مستخدم"
        else:
            role = "غير مصرح"
        ai_status = "مفعل" if ai_allowed else "معطل"
        send_or_update_log(target_id, name, phone, role, ai_status, actor)
    else:
        log_error(f"لم أجد المستخدم {target_id} لإرسال التقرير")

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
def send_user_card(chat_id, row, edit_existing=False):
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
    ai_status = "مفعل" if ai_val == "TRUE" else "معطل"
    ph_line = f"\n📞 [{phone}](tel:{phone})" if phone else ""

    # الـ ID كرابط يفتح الحساب مباشرة
    uid_link = f"[{uid_str}](tg://user?id={uid_str})"
    text = f"{role_icon} *{name}*\n🆔 {uid_link}{ph_line}\n{ai_icon} AI: {ai_status}\n{'─' * 23}"

    # ── أزرار البطاقة: زرين فقط بمنطق ذكي ──
    # ⭐ أدمن:
    #   - مستخدم عادي → يرتقي لأدمن
    #   - أدمن → يُقفل (يلغي كل صلاحياته)
    # 👤 مستخدم:
    #   - أدمن → ينزل لمستخدم عادي
    #   - مستخدم عادي → تُلغى صلاحيته نهائياً
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)

    # نص الزر يعكس ما سيحدث
    if adm == "TRUE" and own != "TRUE":
        admin_btn_text = "⭐ أدمن ← 🔒 إقفال"   # أدمن → ضغط أدمن = إقفال
        user_btn_text  = "👤 تخفيض لمستخدم"
    elif allow_val == "TRUE" and adm != "TRUE" and own != "TRUE":
        admin_btn_text = "⭐ ترقية لأدمن"
        user_btn_text  = "👤 مستخدم ← ⛔ إلغاء"  # مستخدم → ضغط مستخدم = إلغاء
    elif own == "TRUE":
        admin_btn_text = "⭐ تخفيض لأدمن"
        user_btn_text  = "👤 تخفيض لمستخدم"
    else:
        # غير مصرح
        admin_btn_text = "⭐ ترقية لأدمن"
        user_btn_text  = "👤 منح صلاحية"

    markup.row(
        _make_inline("زر_role_admin", admin_btn_text, f"role_admin_{uid_str}"),
        _make_inline("زر_role_user",  user_btn_text,  f"role_user_{uid_str}"),
    )

    # الصف الثاني: تفعيل/تعطيل AI + تغيير الاسم
    ai_button_text = "🚫 تعطيل AI" if ai_val == "TRUE" else "🤖 تفعيل AI"
    ai_key = "زر_ai_off" if ai_val == "TRUE" else "زر_ai_on"
    markup.row(
        _make_inline(ai_key,           ai_button_text,   f"ai_{'off' if ai_val == 'TRUE' else 'on'}_{uid_str}"),
        _make_inline("زر_rename_user", "✏️ تغيير الاسم", f"rename_{uid_str}"),
    )

    if edit_existing and int(uid_str) in _user_card_messages:
        old = _user_card_messages[int(uid_str)]
        if old["chat_id"] == chat_id:
            try:
                bot.edit_message_text(text, old["chat_id"], old["message_id"], parse_mode="Markdown", reply_markup=markup)
                return
            except:
                pass
    msg = bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)
    _user_card_messages[int(uid_str)] = {"chat_id": chat_id, "message_id": msg.message_id}

def format_all_users_message():
    try:
        rows = users_sheet.get_all_values()
        active_lines  = ["👥 *المستخدمون النشطون:*\n" + "━" * 30]
        new_lines     = ["\n🆕️ *زوار جدد (لم تُمنح لهم صلاحية بعد):*\n" + "━" * 30]
        has_active = has_new = False

        for row in rows[1:]:
            if len(row) < 3:
                continue
            uid_str = row[2].strip().lstrip("'")
            if not uid_str.isdigit():
                continue
            name    = row[0].strip() or "مجهول"
            phone   = row[1].strip() if len(row) > 1 else ""
            allowed = (row[3].strip().upper() if len(row) > 3 else "FALSE") == "TRUE"
            admin   = (row[4].strip().upper() if len(row) > 4 else "FALSE") == "TRUE"
            owner   = (row[5].strip().upper() if len(row) > 5 else "FALSE") == "TRUE"
            ai      = (row[AI_ALLOWED_COL].strip().upper() if len(row) > AI_ALLOWED_COL else "FALSE") == "TRUE"
            is_new  = name.startswith("🆕️") and not allowed and not admin and not owner

            uid_link   = f"[{uid_str}](tg://user?id={uid_str})"
            phone_part = f" | 📞 `{phone}`" if phone else ""
            ai_part    = " | 🤖" if ai else ""

            if is_new:
                has_new = True
                display_name = name.replace("🆕️ ", "").replace("🆕 ", "").strip()
                new_lines.append(f"🆕️ `{display_name}`\n🆔 {uid_link}{phone_part}\n─" * 1 + "─" * 29)
            else:
                has_active = True
                if owner:   icon = "👑"
                elif admin: icon = "⭐"
                elif allowed: icon = "👤"
                else: icon = "❌"
                active_lines.append(f"{icon}{ai_part} `{name}`\n🆔 {uid_link}{phone_part}\n" + "─" * 30)

        result = []
        if has_active:
            result.extend(active_lines)
        if has_new:
            result.extend(new_lines)
        if not result:
            return "❌ لا يوجد مستخدمين مسجلين."
        return "\n".join(result)
    except Exception as e:
        log_error(f"format_all_users_message: {e}")
        return "❌ حدث خطأ في قراءة بيانات المستخدمين."

def _execute_search(chat_id, uid):
    state = user_state.get(uid, {})
    df = state.get("date_filter")
    subjs = [v for v in state.get("sel_subjects", []) if v != "__all__"]
    types_f = [v for v in state.get("sel_types", []) if v != "__all__"]
    display_mode = state.get("display_mode", "subject")
    user_state.pop(uid, None)
    welcome, _ = get_settings()
    allowed, admins, owners, open_all, admin_all, _, _, _ = get_users()
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
            _, _, _, open_all, _, _, _, _ = get_users()
        if not open_all:
            return
        uid_str = str(message.from_user.id)
        for row in users_sheet.get_all_values()[1:]:
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                return
        add_user_to_sheet(message.from_user.full_name or "مجهول", message.from_user.id, auto=True, allowed=False)
    except:
        pass

def _register_new_visitor(message):
    """
    يُسجّل أي شخص يضغط /start في الشيت بعلامة 🆕️
    حتى لو ليس مسموحاً له — بدون allowed=True.
    لا يعيد التسجيل إذا كان موجوداً بالفعل.
    """
    try:
        uid_str = str(message.from_user.id)
        rows = users_sheet.get_all_values()[1:]
        for row in rows:
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                return  # موجود بالفعل
        name = message.from_user.full_name or "مجهول"
        # allowed=False حتى لا يدخل البوت تلقائياً
        users_sheet.append_row(
            [f"🆕️ {name}", "", message.from_user.id,
             False, False, False, False, False, False, False, False],
            value_input_option="USER_ENTERED"
        )
        invalidate_users_cache()
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
    """
    يحوّل الوقت بأي تنسيق إلى HH:MM - HH:MM بنظام 24 ساعة.
    يقبل: 10-12 | 8:00-10 | من 11 | ١٠-١٢ | 10 to 12 | من الساعة 8 الى 10
    """
    return _time12_to_24(t)

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
        invalidate_sheet_cache()
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
def set_bot_commands():
    commands = [
        telebot.types.BotCommand("start", "بدء البوت"),
        telebot.types.BotCommand("help", "عرض التعليمات"),
        telebot.types.BotCommand("lang", "تغيير اللغة"),
        telebot.types.BotCommand("ai", "تشغيل المساعد الذكي"),
        telebot.types.BotCommand("refresh", "تحديث بيانات البوت"),
    ]
    bot.set_my_commands(commands)

def send_typing_animation(chat_id, uid, duration=2):
    base_text = bt("رسالة_نايف_يكتب", uid)
    msg = bot.send_message(chat_id, f"{base_text} .")
    frames = [" .", " ..", " ..."]
    start = time.time()
    i = 0
    while time.time() - start < duration:
        try:
            bot.edit_message_text(f"{base_text}{frames[i % len(frames)]}",
                                  chat_id, msg.message_id)
            i += 1
            time.sleep(0.3)
        except:
            break
    try:
        bot.delete_message(chat_id, msg.message_id)
    except:
        pass

@bot.message_handler(commands=['start'])
def start_message(message):
    text = message.text.strip()
    uid = message.from_user.id
    load_user_lang(uid)

    parts = text.split()

    # ── /start refresh — يشتغل فقط للمالك أو من بوت اللوج ──
    if len(parts) > 1 and parts[1] == "refresh":
        invalidate_users_cache()
        invalidate_sheet_cache()
        allowed, admins, owners, open_all, admin_all, _, _, _ = get_users()
        _owner = uid in owners
        if _owner:
            n = _do_full_refresh()
            bot.send_message(message.chat.id,
                f"✅ تم تحديث البيانات!\n🤖 مزودي AI النشطين: {n}")
        else:
            bot.send_message(message.chat.id, "✅ تم تجديد البيانات")
        return

    if len(parts) > 1 and parts[1].startswith("show_user_"):
        target_uid = parts[1].split("_")[2]
        _, row = find_user_row_by_id(target_uid)
        if row:
            send_user_card(message.chat.id, row)
            return
        else:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود")
            return

    # ── تسجيل الزائر تلقائياً في الشيت (🆕️) بغض النظر عن الصلاحية ──
    threading.Thread(target=_register_new_visitor, args=(message,), daemon=True).start()

    welcome, rejection = get_settings()
    allowed, admins, owners, open_all, admin_all, _, _, _ = get_users()
    is_allowed = open_all or uid in allowed
    if not is_allowed:
        if not is_pending(uid):
            pending_requests.add(uid)

        # ── تحقق هل الرقم موجود في الشيت مسبقاً ──
        _row_idx, _user_row = find_user_row_by_id(uid)
        _has_phone = bool(_user_row and len(_user_row) > 1 and _user_row[1].strip())

        if _has_phone:
            # الرقم موجود → أرسل طلب للمالك مباشرة بدون طلب الرقم مجدداً
            _uname   = _user_row[0].strip() if _user_row else (message.from_user.full_name or "مجهول")
            _uphone  = _user_row[1].strip()
            notify_owners_new_request(uid, _uname, _uphone)
            bot.send_message(message.chat.id, bt("رسالة_انتظار", uid))
            return

        # ١ - الترتيب: لا أريد أولاً (أحمر)، مشاركة ثانياً (أخضر)
        inline_markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        inline_markup.row(
            _make_inline("زر_لا_اريد",    bt("زر_لا_اريد", uid),    "request_contact_no"),
            _make_inline("زر_مشاركة_رقم", bt("زر_مشاركة_رقم", uid), "request_contact"),
        )

        caption = bt("رسالة_غير_مسموح", uid)

        help_image_id = get_help_file_id("help_request_photo", "photo")
        if help_image_id:
            try:
                bot.send_photo(message.chat.id, help_image_id,
                               caption=caption, parse_mode="Markdown",
                               reply_markup=inline_markup)
            except Exception as e:
                log_error(f"فشل إرسال الصورة: {e}")
                bot.send_message(message.chat.id, caption,
                                 parse_mode="Markdown", reply_markup=inline_markup)
        else:
            bot.send_message(message.chat.id, caption,
                             parse_mode="Markdown", reply_markup=inline_markup)
        return

    user_state.pop(uid, None)
    admin = admin_all or uid in admins
    owner = uid in owners
    log_info("START", uid)
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin, owner=owner))

@bot.callback_query_handler(func=lambda call: call.data == "request_contact")
def handle_request_contact_confirm(call):
    uid = call.from_user.id
    load_user_lang(uid)
    bot.answer_callback_query(call.id)

    # زر الكيبورد الكبير (request_contact)
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=False, one_time_keyboard=True)
    keyboard.add(telebot.types.KeyboardButton(bt("زر_مشاركة_كيبورد", uid), request_contact=True))

    # زر رجوع inline (يُرفق مع الرسالة الأصلية)
    back_markup = telebot.types.InlineKeyboardMarkup()
    back_markup.add(_make_inline("زر_عوده_مشاركه", bt("زر_عوده_مشاركه", uid), "request_contact_back"))

    # نعدّل الرسالة الأصلية لإضافة زر الرجوع
    try:
        bot.edit_message_caption(
            bt("رسالة_مشاركة", uid),
            call.message.chat.id, call.message.message_id,
            parse_mode="Markdown", reply_markup=back_markup
        )
    except:
        try:
            bot.edit_message_text(
                bt("رسالة_مشاركة", uid),
                call.message.chat.id, call.message.message_id,
                parse_mode="Markdown", reply_markup=back_markup
            )
        except:
            pass

    # إرسال زر الكيبورد وحفظ message_id لحذفه عند الرجوع
    try:
        _kb_msg = bot.send_message(call.message.chat.id, bt("رسالة_كيبورد_مشاركة", uid) or "📲",
                                   reply_markup=keyboard)
        _pending_kb_msgs[uid] = _kb_msg.message_id
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data == "request_contact_no")
def handle_request_contact_no(call):
    uid = call.from_user.id
    load_user_lang(uid)
    bot.answer_callback_query(call.id)
    # لا يوجد كيبورد هنا — استبدال الرسالة مباشرة بدون أي إرسال إضافي
    # استبدال الرسالة الأولى بالرسالة البديلة
    contact_url = bt("رابط_بوت_تواصل", uid)
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(bt("زر_بوت_تواصل", uid), url=contact_url))
    markup.add(_make_inline("زر_عوده_مشاركه", bt("زر_عوده_مشاركه", uid), "request_contact_back"))
    try:
        bot.edit_message_caption(
            bt("رسالة_لا_اريد", uid),
            call.message.chat.id, call.message.message_id,
            parse_mode="Markdown", reply_markup=markup
        )
    except:
        try:
            bot.edit_message_text(
                bt("رسالة_لا_اريد", uid),
                call.message.chat.id, call.message.message_id,
                parse_mode="Markdown", reply_markup=markup
            )
        except:
            pass


@bot.callback_query_handler(func=lambda call: call.data == "request_contact_back")
def handle_request_contact_back(call):
    uid = call.from_user.id
    load_user_lang(uid)
    bot.answer_callback_query(call.id)

    # ① إعادة أزرار المحادثة فوراً
    inline_markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    inline_markup.row(
        _make_inline("زر_لا_اريد",    bt("زر_لا_اريد", uid),    "request_contact_no"),
        _make_inline("زر_مشاركة_رقم", bt("زر_مشاركة_رقم", uid), "request_contact"),
    )
    caption = bt("رسالة_غير_مسموح", uid)
    try:
        bot.edit_message_caption(
            caption, call.message.chat.id, call.message.message_id,
            parse_mode="Markdown", reply_markup=inline_markup
        )
    except:
        try:
            bot.edit_message_text(
                caption, call.message.chat.id, call.message.message_id,
                parse_mode="Markdown", reply_markup=inline_markup
            )
        except:
            pass

    # ② بالتوازي: حذف رسالة الكيبورد + إرسال رسالة حذف الكيبورد السفلي ثم حذفها
    def _remove_kb():
        try:
            # حذف رسالة_كيبورد_مشاركة
            kb_mid = _pending_kb_msgs.pop(uid, None)
            if kb_mid:
                try: bot.delete_message(call.message.chat.id, kb_mid)
                except: pass
            # إرسال ReplyKeyboardRemove لإخفاء الكيبورد السفلي ثم حذفها
            rm_msg = bot.send_message(
                call.message.chat.id, "​",
                reply_markup=telebot.types.ReplyKeyboardRemove()
            )
            time.sleep(0.3)
            try: bot.delete_message(call.message.chat.id, rm_msg.message_id)
            except: pass
        except Exception as e:
            log_error(f"_remove_kb: {e}", uid)

    threading.Thread(target=_remove_kb, daemon=True).start()

@bot.message_handler(commands=['ai'])
def ai_command(message):
    uid = message.from_user.id
    if not AI_PROVIDERS:
        bot.send_message(message.chat.id, bt("رسالة_ai_غير_مفعل", uid))
        return
    if not is_ai_allowed(uid):
        bot.send_message(message.chat.id, bt("رسالة_ai_غير_مسموح", uid))
        return
    user_ai_enabled[uid] = True
    threading.Thread(target=set_user_ai_switch, args=(uid, True), daemon=True).start()
    default_model = AI_PROVIDERS[0] if AI_PROVIDERS else {"icon": "❌", "name": "غير متاح"}
    # لا نُرسل reply_markup حتى لا تتغير الواجهة الحالية
    bot.send_message(
        message.chat.id,
        bt("رسالة_ai_ترحيب", uid).format(model=f"{default_model['icon']} {default_model['name']}"),
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['refresh'])
def refresh_command(message):
    uid = message.from_user.id
    invalidate_users_cache()
    invalidate_sheet_cache()
    allowed, admins, owners, open_all, admin_all, _, _, _ = get_users()
    _admin = admin_all or uid in admins
    _owner = uid in owners
    msg = bot.send_message(message.chat.id, "🔄 جاري التجديد...")
    if _owner:
        n = _do_full_refresh()
        bot.edit_message_text(
            f"✅ تم تحديث البيانات!\n"
            f"🤖 مزودي AI النشطين: {n}\n"
            f"🔄 cache المستخدمين والبيانات أُبطل.",
            message.chat.id, msg.message_id)
    else:
        # يحدّث النصوص والأزرار للجميع
        load_bot_texts()
        load_button_texts()
        invalidate_users_cache()
        invalidate_sheet_cache()
        bot.edit_message_text("✅ تم تجديد البيانات", message.chat.id, msg.message_id)

@bot.message_handler(commands=['ai_reset'])
def ai_reset_command(message):
    uid = message.from_user.id
    if not is_owner_id(uid):
        bot.send_message(message.chat.id, "⛔ هذا الأمر متاح للمالك فقط.")
        return
    global _ai_histories
    _ai_histories.pop(uid, None)
    bot.send_message(message.chat.id, "✅ تم إعادة تعيين سياق المحادثة والنموذج إلى الأول.")

@bot.message_handler(commands=['ai_clear'])
def ai_clear_command(message):
    uid = message.from_user.id
    if not is_owner_id(uid):
        bot.send_message(message.chat.id, "⛔ هذا الأمر متاح للمالك فقط.")
        return
    _ai_histories.pop(uid, None)
    bot.send_message(message.chat.id, "✅ تم مسح سياق المحادثة.")

@bot.message_handler(commands=['lang'])
def language_command(message):
    uid = message.from_user.id
    load_user_lang(uid)
    _, rejection = get_settings()
    allowed, _, _, open_all, _, _, _, _ = get_users()
    if not (open_all or uid in allowed):
        bot.send_message(message.chat.id, rejection)
        return
    user_state[uid] = {"choosing_lang": True}
    bot.send_message(message.chat.id, bt("رسالة_تغيير_اللغة", uid), reply_markup=lang_menu(uid))

@bot.message_handler(commands=['help'])
def help_message(message):
    uid = message.from_user.id
    load_user_lang(uid)
    _, admins, owners, _, admin_all, _, _, _ = get_users()
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
            users_sheet.append_row([name, phone, uid, False, False, False, False, False, False, False, False],
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
    allowed, admins, owners, open_all, admin_all, _, _, _ = get_users()
    if not (open_all or uid in allowed):
        bot.send_message(message.chat.id, rejection)
        return

    # ========== ميزة نايف: إرسال file_id إلى اللوج والتوقف ==========
    caption = message.caption or ""
    if "نايف" in caption:
        if message.document:
            file_id = message.document.file_id
            file_type = "مستند"
        elif message.photo:
            file_id = message.photo[-1].file_id
            file_type = "صورة"
        elif message.video:
            file_id = message.video.file_id
            file_type = "فيديو"
        elif message.audio:
            file_id = message.audio.file_id
            file_type = "صوت"
        elif message.voice:
            file_id = message.voice.file_id
            file_type = "تسجيل صوتي"
        else:
            bot.send_message(message.chat.id, "⚠️ نوع الملف غير مدعوم")
            return

        # استخراج كلمة مفتاحية من النص (آخر كلمة بعد نايف)
        words = caption.split()
        keyword = None
        if len(words) > 1:
            keyword = words[-1]
            _naif_files[keyword] = file_id

        name, phone = _get_user_name_phone(uid)
        log_msg = (
            f"🤖 *نايف*\n"
            f"📎 *{file_type}*\n"
            f"🆔 `{file_id}`\n"
            f"👤 {name} (ID: `{uid}`)\n"
            f"📝 النص: `{caption[:100]}`"
        )
        if keyword:
            log_msg += f"\n📌 الكلمة المفتاحية: `{keyword}`"

        try:
            _requests.post(
                f"https://api.telegram.org/bot{LOG_BOT_TOKEN}/sendMessage",
                json={"chat_id": LOG_BOT_TOKEN, "text": log_msg, "parse_mode": "Markdown"},
                timeout=5
            )
            bot.send_message(
                message.chat.id,
                "✅ تم إرسال الملف إلى المالك بنجاح.\n\n"
                "📌 يمكنك الآن استخدام الأمر:\n"
                f"`أعطني الملف {keyword or file_id}` لاستدعاء هذا الملف.",
                parse_mode="Markdown"
            )
        except Exception as e:
            log_error(f"❌ فشل إرسال file_id إلى اللوج: {e}", uid)
            bot.send_message(message.chat.id, "❌ حدث خطأ أثناء إرسال الملف.")
        return
    # ====================================================

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
        cap = (message.caption or "").strip()
        user_state[uid].setdefault("pending_files", []).append({"file_id": file_id, "file_type": ftype, "caption": cap})
        # إذا أُرسل كابشن مع الملف → احفظه كنص للخلية
        if cap and not user_state[uid].get("file_caption"):
            user_state[uid]["file_caption"] = cap

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
        cap = (message.caption or "").strip()
        user_state[uid].setdefault("pending_files", []).append({"file_id": file_id, "file_type": ftype, "caption": cap})
        if cap and not user_state[uid].get("file_caption"):
            user_state[uid]["file_caption"] = cap

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
    load_user_ai_switch(uid)
    load_user_auto_publish(uid)   # تحميل حالة النشر التلقائي من الشيت
    welcome, rejection = get_settings()
    allowed, admins, owners, open_all, admin_all, _, _, _ = get_users()
    is_allowed = open_all or uid in allowed
    admin = admin_all or uid in admins
    owner = uid in owners
    text = (message.text or "").strip()
    state = user_state.get(uid, {})
    back_btn = bt("زر_عوده", uid)
    from_voice = False

    # معالجة التسجيلات الصوتية
    if message.content_type == 'voice':
        if (AI_PROVIDERS and is_ai_allowed(uid) and user_ai_enabled.get(uid, False)):
            processing_msg = bot.send_message(message.chat.id, "🎤 جاري معالجة التسجيل الصوتي...")
            bot.send_chat_action(message.chat.id, "typing")
            transcribed = transcribe_voice(message.voice.file_id, lang="ar")
            if transcribed:
                text = transcribed
                from_voice = True
                try:
                    bot.delete_message(message.chat.id, processing_msg.message_id)
                except:
                    pass
            else:
                bot.edit_message_text("❌ لم أستطع فهم التسجيل الصوتي.", message.chat.id, processing_msg.message_id)
                return
        else:
            # الشروط غير مكتملة → تجاهل الصوت بصمت (لا رسالة خطأ)
            return

    # ─── معالجة تعديل بطاقة الجدول (أولوية عالية قبل الـ AI) ───
    if state.get("editing_schedule"):
        short_key = state["editing_schedule"]
        card = _schedule_cards.get(short_key)
        if not card:
            user_state.pop(uid, None)
            bot.send_message(message.chat.id, "⚠️ انتهت صلاحية البطاقة.")
            return
        user_state.pop(uid, None)
        # نبني سياقاً كاملاً: البيانات الحالية + التعديل المطلوب
        current_entries_text = _format_schedule_card(card["entries"], card.get("note",""))
        combined = (
            f"النص الأصلي:\n{card['raw_text']}\n\n"
            f"البيانات المستخرجة حالياً:\n{current_entries_text}\n\n"
            f"التعديل المطلوب من المستخدم:\n{text}\n\n"
            f"المطلوب: طبّق التعديل وأرجع JSON محدّثاً."
        )
        typing_edit = bot.send_message(message.chat.id, "⏳ جاري تطبيق التعديل...")
        def _redo_extract():
            entries, note = extract_schedule_from_text(combined)
            try:
                bot.delete_message(message.chat.id, typing_edit.message_id)
            except:
                pass
            if entries:
                card["entries"] = entries
                card["note"] = note
                card["raw_text"] = combined
                new_card_text = _format_schedule_card(entries, note)
                card["card_text"] = new_card_text
                mk = _schedule_card_markup(short_key)
                try:
                    bot.edit_message_text(new_card_text, card["chat_id"], card["msg_id"],
                                          parse_mode="Markdown", reply_markup=mk)
                except:
                    sent = bot.send_message(card["chat_id"], new_card_text,
                                            parse_mode="Markdown", reply_markup=mk)
                    card["msg_id"] = sent.message_id
            else:
                bot.send_message(message.chat.id,
                                 "❌ لم أستطع تطبيق التعديل.\n"
                                 "اضغط ✏️ تعديل مرة أخرى وأرسل التعديل بشكل أوضح.")
        threading.Thread(target=_redo_extract, daemon=True).start()
        return

    # ─── إذا كل مزودي AI معطّلون → أطفئ السويتش في الذاكرة فقط (لا تكتب الشيت) ───
    if not AI_PROVIDERS and user_ai_enabled.get(uid, False):
        user_ai_enabled[uid] = False

    # ─── معالجة الأزرار (أولوية قصوى، تتجاوز الـ AI دائماً) ───
    if text in BUTTON_TEXTS and not from_voice:
        pass  # يكمل للكود العادي أدناه

    # ─── معالجة AI: يشتغل فقط في المنيو الرئيسي (state فارغ أو subject فقط) ───
    elif (
        AI_PROVIDERS                                    # يوجد مزود نشط
        and is_ai_allowed(uid)                          # لدى المستخدم صلاحية
        and user_ai_enabled.get(uid, False)             # السويتش ON
        and not state                                          # في الصفحة الرئيسية فقط (state فارغ تماماً)
        and text                                        # النص غير فارغ
    ):
        user_role = get_user_role(uid)
        typing_msg = bot.send_message(message.chat.id, f"{bt('رسالة_نايف_يكتب', uid)} ...")
        def animate_typing():
            frames = [" .", " ..", " ..."]
            i = 0
            start = time.time()
            while time.time() - start < 8:
                try:
                    bot.edit_message_text(f"{bt('رسالة_نايف_يكتب', uid)}{frames[i % len(frames)]}",
                                          message.chat.id, typing_msg.message_id)
                    i += 1
                    time.sleep(0.3)
                except:
                    break
        threading.Thread(target=animate_typing, daemon=True).start()
        def run_ai():
            # ─── للأدمن/المالك: نحاول استخراج جدول أولاً ───
            if user_role in ("admin", "owner"):
                entries, note = extract_schedule_from_text(text)
                # entries = None → فشل الاستخراج كلياً
                # entries = []   → النص ليس جدولاً
                # entries = [...] → وُجد جدول ✅
                if entries:  # قائمة غير فارغة = يوجد جدول
                    try:
                        bot.delete_message(message.chat.id, typing_msg.message_id)
                    except:
                        pass
                    short_key = f"sched_{int(time.time())}_{uid}"
                    card_text = _format_schedule_card(entries, note)
                    mk = _schedule_card_markup(short_key)
                    sent = bot.send_message(message.chat.id, card_text,
                                            parse_mode="Markdown", reply_markup=mk)
                    _schedule_cards[short_key] = {
                        "uid": uid,
                        "entries": entries,
                        "note": note,
                        "card_text": card_text,
                        "msg_id": sent.message_id,
                        "chat_id": message.chat.id,
                        "raw_text": text,
                    }
                    return
                # entries فارغة أو None → رسالة عادية، يكمل للرد العادي

            # ─── رد عادي من الـ AI ───
            response, used_model = ask_ai(uid, text, user_role=user_role,
                                          notify_fn=None, send_notify=(owner or admin))
            try:
                bot.delete_message(message.chat.id, typing_msg.message_id)
            except:
                pass
            if response:
                bot.send_message(message.chat.id, response, parse_mode="Markdown",
                                 reply_markup=main_menu(uid, admin=admin, owner=owner))
            else:
                bot.send_message(message.chat.id, bt("رسالة_ai_فشل", uid),
                                 reply_markup=main_menu(uid, admin=admin, owner=owner))
        threading.Thread(target=run_ai, daemon=True).start()
        return

    # ─── إذا اختلت أي شرط → الرسالة تروح للبوت العادي بصمت تام ───
    # (لا يوجد أي رسالة خطأ عن AI — كأنه غير موجود)

    # ========== باقي معالجة البوت العادي ==========
    if state.get("awaiting_rename_for_approval"):
        short_key = state["awaiting_rename_for_approval"]
        req_data = _approval_store.get(short_key)
        if not req_data:
            user_state.pop(uid, None)
            bot.send_message(message.chat.id, "⚠️ انتهت صلاحية الطلب")
            return
        new_name = text.strip()
        if not new_name:
            bot.send_message(message.chat.id, "❌ الاسم لا يمكن أن يكون فارغاً.")
            return
        requester_id = req_data["requester_id"]
        requester_name = req_data["requester_name"]
        phone = req_data["phone"]
        decided_by = (f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name)
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
                    users_sheet.update_cell(i, 1, new_name)
                    users_sheet.update_cell(i, 4, True)
                    found = True
                    break
            if not found:
                users_sheet.append_row([new_name, phone, requester_id, True, False, False, False, False, False, False, False])
            pending_requests.discard(requester_id)
            _approval_store.pop(short_key, None)
            try:
                bot.send_message(requester_id, f"✅ تمت الموافقة على طلبك! اسمك الجديد: {new_name}\nأرسل /start للبدء.")
            except:
                pass
            notify_owners_action(requester_id, new_name, phone, decided_by, "approve")
            bot.send_message(message.chat.id, f"✅ تمت الموافقة وتغيير الاسم إلى: {new_name}")
            msg_ids = request_msg_ids.pop(requester_id, {})
            for oid, mid in msg_ids.items():
                try:
                    bot.delete_message(oid, mid)
                except:
                    pass
        except Exception as e:
            log_error(f"approve_with_rename: {e}")
            bot.send_message(message.chat.id, "❌ حدث خطأ أثناء الموافقة")
        user_state.pop(uid, None)
        return

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
                invalidate_users_cache()  # ← إبطال الـ cache فوراً
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

        ai_button_text = f"🤖 {bt('زر_مساعد_نايف', uid)}"
        if text in [f"🟢 {ai_button_text}", f"🔴 {ai_button_text}", ai_button_text]:
            if not AI_PROVIDERS:
                # لا يوجد مزود AI → لا شيء
                bot.send_message(message.chat.id, bt("رسالة_ai_غير_مفعل", uid),
                                 reply_markup=main_menu(uid, admin=admin, owner=owner))
                return
            if not is_ai_allowed(uid):
                # ليس لديه صلاحية → اسأله إذا يريد طلب صلاحية
                markup = telebot.types.InlineKeyboardMarkup()
                markup.row(
                    _make_inline("زر_ai_request_yes", "✅ نعم", "ai_request_yes"),
                    _make_inline("زر_ai_request_no",  "❌ لا",  "ai_request_no"),
                )
                bot.send_message(
                    message.chat.id,
                    f"🤖 *مساعد نايف*\n\n"
                    f"ليس لديك صلاحية استخدام المساعد الذكي.\n\n"
                    f"هل تريد إرسال طلب للمالك لتفعيل الصلاحية؟",
                    parse_mode="Markdown",
                    reply_markup=markup
                )
                return
            # لديه صلاحية → تبديل السويتش وحفظه في الشيت
            current = user_ai_enabled.get(uid, False)
            new_state = not current
            user_ai_enabled[uid] = new_state
            # حفظ في الشيت في ثريد منفصل لعدم إبطاء الاستجابة
            threading.Thread(target=set_user_ai_switch, args=(uid, new_state), daemon=True).start()
            if new_state:
                bot.send_message(
                    message.chat.id,
                    f"✅ تم تفعيل مساعد نايف!\n\n"
                    "اكتب سؤالك مباشرة وسأرد عليك.\n"
                    "الأزرار لا تزال تعمل بشكل طبيعي.\n\n"
                    "لإيقاف المساعد، اضغط على الزر مرة أخرى.",
                    reply_markup=main_menu(uid, admin=admin, owner=owner)
                )
            else:
                bot.send_message(
                    message.chat.id,
                    f"🔴 تم إيقاف مساعد نايف.",
                    reply_markup=main_menu(uid, admin=admin, owner=owner)
                )
            return

        publish_button_text = f"{bt('زر_نشر_تلقائي', uid)}"
        if text in [f"📢 {publish_button_text}", f"🔕 {publish_button_text}", publish_button_text]:
            if not is_ai_allowed(uid):
                bot.send_message(message.chat.id, bt("رسالة_ai_غير_مسموح", uid))
                return
            current = get_user_auto_publish(uid)
            new_state = not current
            if set_user_auto_publish(uid, new_state):
                user_auto_publish[uid] = new_state
                status = "مفعل" if new_state else "معطل"
                bot.send_message(
                    message.chat.id,
                    f"{'✅' if new_state else '❌'} تم {status} النشر التلقائي!\n\n"
                    "ستصلك إشعارات عند إضافة أي محتوى جديد للبوت." if new_state else "لن تصلك إشعارات المحتوى الجديد.",
                    reply_markup=main_menu(uid, admin=admin, owner=owner)
                )
            else:
                bot.send_message(message.chat.id, "❌ حدث خطأ أثناء تغيير الإعداد.")
            return

        # ══════════════════════════════════════════
        # ↩️ رجوع خطوة — يرجع خطوة واحدة في الـ flow الحالي
        # ══════════════════════════════════════════
        if text == "↩️ رجوع خطوة":
            step = state.get("step", "")

            # ── إضافة بيانات ──
            if state.get("adding_data"):
                if step == "choose_subject":
                    user_state[uid]["step"] = "choose_type"
                    bot.send_message(message.chat.id, "اختر نوع البيانات:", reply_markup=add_data_menu(uid))
                elif step == "choose_building":
                    user_state[uid]["step"] = "choose_subject"
                    _kb, _ = subjects_with_noexist_kb(uid)
                    bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=_kb)
                elif step == "choose_room":
                    user_state[uid]["step"] = "choose_building"
                    bot.send_message(message.chat.id, "🏛 اختر المبنى:", reply_markup=buildings_menu(uid))
                elif step == "enter_date":
                    dtype = state.get("data_type", "")
                    if dtype == "lecture":
                        user_state[uid]["step"] = "choose_building"
                        bot.send_message(message.chat.id, "🏛 اختر المبنى:", reply_markup=buildings_menu(uid))
                    else:
                        user_state[uid]["step"] = "choose_subject"
                        _kb, _ = subjects_with_noexist_kb(uid)
                        bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=_kb)
                elif step == "enter_time":
                    user_state[uid]["step"] = "enter_date"
                    bot.send_message(message.chat.id, "📅 أدخل تاريخ المحاضرة:",
                                     reply_markup=date_suggestions_menu(for_lecture=True, uid=uid))
                elif step in ("enter_value", "enter_new_val"):
                    user_state[uid]["step"] = "enter_date"
                    dtype = state.get("data_type", "")
                    for_lec = dtype == "lecture"
                    for_alt = dtype == "alert"
                    bot.send_message(message.chat.id, "📅 أدخل التاريخ:",
                                     reply_markup=date_suggestions_menu(
                                         subject=state.get("subject", ""),
                                         for_lecture=for_lec, for_alert=for_alt, uid=uid))
                else:
                    user_state[uid]["step"] = "choose_type"
                    bot.send_message(message.chat.id, "اختر نوع البيانات:", reply_markup=add_data_menu(uid))
                return

            # ── تعديل بيانات ──
            if state.get("editing_data"):
                if step == "choose_subject":
                    user_state[uid]["step"] = "choose_type"
                    bot.send_message(message.chat.id, "اختر نوع البيانات:", reply_markup=edit_data_menu(uid))
                elif step == "choose_date_edit":
                    user_state[uid]["step"] = "choose_subject"
                    _kb, _ = subjects_menu_kb(uid)
                    bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=_kb)
                elif step == "choose_action":
                    user_state[uid]["step"] = "choose_date_edit"
                    dates = state.get("dates_cache", [])
                    bot.send_message(message.chat.id, "📅 اختر التاريخ:", reply_markup=dates_menu_kb(dates, uid) if dates else back_only_menu(uid))
                elif step in ("enter_new_val", "confirm_delete"):
                    user_state[uid]["step"] = "choose_action"
                    bot.send_message(message.chat.id, "اختر الإجراء:", reply_markup=edit_action_menu(uid))
                else:
                    user_state[uid]["step"] = "choose_type"
                    bot.send_message(message.chat.id, "اختر نوع البيانات:", reply_markup=edit_data_menu(uid))
                return

            # ── رفع ملف (أدمن) ──
            if state.get("uploading"):
                if step == "choose_type":
                    user_state[uid]["step"] = "choose_subject"
                    _kb, _ = subjects_menu_kb(uid)
                    bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=_kb)
                elif step in ("choose_date", "waiting_files", "confirm_files"):
                    user_state[uid]["step"] = "choose_type"
                    bot.send_message(message.chat.id, "اختر نوع الملف:", reply_markup=file_type_menu(uid))
                else:
                    user_state[uid]["step"] = "choose_subject"
                    _kb, _ = subjects_menu_kb(uid)
                    bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=_kb)
                return

            # ── طلب رفع (مستخدم) ──
            if state.get("requesting_upload"):
                if step == "choose_type":
                    user_state[uid]["step"] = "choose_subject"
                    _kb, _ = subjects_menu_kb(uid)
                    bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=_kb)
                elif step in ("choose_date", "waiting_files_req", "confirm_req"):
                    user_state[uid]["step"] = "choose_type"
                    bot.send_message(message.chat.id, "اختر نوع الملف:", reply_markup=file_type_menu(uid))
                else:
                    user_state[uid]["step"] = "choose_subject"
                    _kb, _ = subjects_menu_kb(uid)
                    bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=_kb)
                return

            # ── رفع تعليمات ──
            if state.get("uploading_help"):
                if step == "waiting_file_help":
                    user_state[uid]["step"] = "enter_note"
                    bot.send_message(message.chat.id, "📝 أدخل نصاً توضيحياً أو تخطي:", reply_markup=back_skip_menu(uid))
                elif step == "enter_note":
                    user_state[uid]["step"] = "choose_audience"
                    bot.send_message(message.chat.id, "👥 هذه التعليمات لمن؟", reply_markup=help_audience_menu(uid))
                else:
                    user_state[uid]["step"] = "choose_audience"
                    bot.send_message(message.chat.id, "👥 هذه التعليمات لمن؟", reply_markup=help_audience_menu(uid))
                return

            # ── إدارة المستخدمين ──
            if state.get("managing_users"):
                if step in ("search_unified",):
                    user_state[uid]["step"] = "menu"
                    bot.send_message(message.chat.id, "👥 إدارة المستخدمين:", reply_markup=manage_users_menu(uid))
                else:
                    user_state.pop(uid, None)
                    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin, owner=owner))
                return

            # ── بث الإشعارات ──
            if state.get("broadcasting"):
                if step == "waiting_file_or_send":
                    user_state[uid]["step"] = "waiting_text"
                    m_bcast = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                    m_bcast.add("📤 إرسال بدون نص", back_btn)
                    bot.send_message(message.chat.id, "اكتب نص الإشعار:", reply_markup=m_bcast)
                else:
                    user_state.pop(uid, None)
                    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin, owner=owner))
                return

            # ── fallback: رجوع للرئيسية ──
            user_state.pop(uid, None)
            bot.send_message(message.chat.id, welcome, reply_markup=main_menu(uid, admin=admin, owner=owner))
            return

        if text == back_btn:
            if state.get("renaming_user"):
                user_state.pop(uid, None)
                bot.send_message(message.chat.id, "❌ تم إلغاء تغيير الاسم.", reply_markup=manage_users_menu(uid))
                return
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

        if text == bt("زر_المواد", uid):
            user_state.pop(uid, None)
            bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=subjects_kb)
            return

        _free = not state or set(state.keys()) <= {"subject"}
        if _free and text in subjects_list:
            user_state[uid] = {"subject": text}
            bot.send_message(message.chat.id, f"📌 *{text}*\nماذا تحتاج؟", parse_mode="Markdown", reply_markup=subject_options_menu(uid))
            return

        SUBJ_OPTS = [bt(k, uid) for k in ["خيار_الجدول", "خيار_التكاليف", "خيار_السعر", "خيار_الملخص", "خيار_التنبيهات", "خيار_الملزمه"]]
        if _free and state.get("subject") and text in SUBJ_OPTS:
            subj = state["subject"]
            rows_s = [r for r in data if safe_get(r, 1) == subj]
            if text == bt("خيار_الملزمه", uid):
                note = next((get_text(safe_get(r, 8)) for r in rows_s if safe_get(r, 8)), None)
                msg2 = (f"📋 *{subj}*:\n{note}" if note else f"لا توجد ملزمة لـ *{subj}*")
                bot.send_message(message.chat.id, msg2, parse_mode="Markdown", reply_markup=subject_options_menu(uid))
                return
            if text == bt("خيار_السعر", uid):
                price = next((get_text(safe_get(r, 5)) for r in rows_s if safe_get(r, 5)), None)
                msg2 = (f"💰 *{subj}*: {price}" if price else f"لا يوجد سعر لـ *{subj}*")
                bot.send_message(message.chat.id, msg2, parse_mode="Markdown", reply_markup=subject_options_menu(uid))
                return
            col_map3 = {bt("خيار_الجدول", uid): 2, bt("خيار_التكاليف", uid): 4, bt("خيار_الملخص", uid): 6, bt("خيار_التنبيهات", uid): 7, bt("خيار_الملزمه", uid): 8}
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
            day  = get_day_name(ld, uid)
            # تحويل التاريخ: dd/mm/yyyy → yyyy/mm/dd
            try:
                dt_obj = datetime.strptime(ld, "%d/%m/%Y")
                date_fmt = dt_obj.strftime("%Y/%m/%d")
            except:
                date_fmt = ld
            ORDINALS_AR = ["الأولى","الثانية","الثالثة","الرابعة","الخامسة","السادسة","السابعة","الثامنة"]
            sep = "ـ" * 34
            resp = f"🎓 *جدول المحاضرات | {day} {date_fmt}*\n{sep}\n"
            for idx, r in enumerate(rows_s):
                subj   = safe_get(r, 1)
                time_v = get_text(safe_get(r, 2))
                room   = safe_get(r, 3)
                doctor = get_subject_doctor(subj)
                num    = ORDINALS_AR[idx] if idx < len(ORDINALS_AR) else str(idx+1)
                # تحويل الوقت إلى ص/م
                def fmt_time(t):
                    try:
                        parts = [p.strip() for p in t.split("-")]
                        result = []
                        for p in parts:
                            h, m_ = (p.split(":") + ["00"])[:2]
                            h = int(h); suffix = "ص" if h < 12 else "م"
                            h12 = h if h <= 12 else h - 12
                            result.append(f"{h12:02d}:{m_} {suffix}")
                        return " - ".join(result)
                    except:
                        return t
                time_ar = fmt_time(time_v)
                resp += f"\n🔹 *المحاضرة {num}:*\n"
                resp += f"📖 المقرر: {subj}\n"
                if doctor:
                    resp += f"👨‍🏫 الدكتور: {doctor}\n"
                resp += f"🕒 الوقت: {time_ar}\n"
                if room:
                    resp += f"🏛️ المكان: {room}\n"
            resp += f"\n{sep}"
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

        if text == bt("زر_الملازم", uid):
            notes = get_notes()
            if not notes:
                bot.send_message(message.chat.id, "📭 لا توجد ملازم حالياً.",
                                 reply_markup=main_menu(uid, admin=admin, owner=owner))
                return
            lines = ["📋 *الملازم المتاحة:*\n" + "─" * 25]
            for subj, note_list in notes.items():
                lines.append(f"\n📌 *{subj}:*")
                for note in note_list:
                    # لو رابط → زر inline، لو نص → عرض مباشرة
                    lines.append(f"  • {note}")
            bot.send_message(message.chat.id, "\n".join(lines),
                             parse_mode="Markdown",
                             reply_markup=main_menu(uid, admin=admin, owner=owner))
            return

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
                bot.send_message(message.chat.id, "📅 أدخل التاريخ:", reply_markup=date_suggestions_menu(subject=subj, uid=uid))
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
                    _, admins2, owners2, _, admin_all2, _, _, _ = get_users()
                    targets = list(set(admins2 + owners2))
                    col_label = "تكليف" if col == 4 else "ملخص"
                    for fdata in files:
                        fid = fdata["file_id"]
                        _file_req_counter[0] += 1
                        short_key = str(_file_req_counter[0])
                        _file_req_store[short_key] = {"req_uid": req_uid, "date": date, "subj": subj, "col": col, "fid": fid}
                        mk_req = telebot.types.InlineKeyboardMarkup()
                        mk_req.row(
                            _make_inline("زر_file_approve", "✅ قبول", f"file_req:approve:{short_key}"),
                            _make_inline("زر_file_reject",  "❌ رفض",  f"file_req:reject:{short_key}"),
                        )
                        caption = (f"📨 طلب رفع {col_label}\n👤 من: {message.from_user.full_name}\n📌 {subj} | 📅 {date}")
                        for tid in targets:
                            try:
                                _try_send_file(tid, fid, caption=caption)
                                bot.send_message(tid, "", reply_markup=mk_req)
                            except:
                                pass
                    bot.send_message(message.chat.id, "✅ تم إرسال الطلب! سيتم إخبارك بالنتيجة.", reply_markup=main_menu(uid, admin=admin, owner=owner))
                    user_state.pop(uid, None)
                return
            return

        if text == bt("زر_المستخدمين", uid):
            if not owner:
                bot.send_message(message.chat.id, bt("رسالة_ادمن_فقط", uid))
                return
            user_state[uid] = {"managing_users": True, "step": "menu"}
            bot.send_message(message.chat.id, "👥 *إدارة المستخدمين*", parse_mode="Markdown", reply_markup=manage_users_menu(uid))
            return

        if state.get("managing_users"):
            step = state.get("step", "menu")
            if step == "menu":
                if text == "🔍 بحث عن مستخدم":
                    user_state[uid]["step"] = "search_unified"
                    bot.send_message(message.chat.id,
                        "🔍 أدخل ID أو رقم هاتف أو اسم المستخدم:",
                        reply_markup=back_only_menu(uid))
                elif text == "📋 عرض جميع المستخدمين":
                    all_msg = format_all_users_message()
                    bot.send_message(message.chat.id, all_msg, parse_mode="Markdown")
                elif text == "📋 آخر 3 مستخدمين":
                    last_users = get_last_users(3)
                    if not last_users:
                        bot.send_message(message.chat.id, "⚠️ لا يوجد مستخدمين مسجلين.")
                        return
                    for row in last_users:
                        send_user_card(message.chat.id, row)
                    bot.send_message(message.chat.id, "✅ تم عرض آخر 3 مستخدمين.", reply_markup=manage_users_menu(uid))
                return

            elif step == "search_unified":
                result, stype = _smart_search_user(text.strip())
                if result is None:
                    bot.send_message(message.chat.id, "❌ لم يُعثر على مستخدم")
                elif isinstance(result, list):
                    bot.send_message(message.chat.id, f"🔍 {len(result)} نتيجة:")
                    for row in result[:5]:
                        send_user_card(message.chat.id, row)
                    if len(result) > 5:
                        bot.send_message(message.chat.id, f"⚠️ تم عرض 5 من {len(result)}. دقّق بحثك.")
                else:
                    send_user_card(message.chat.id, result)
                user_state[uid]["step"] = "menu"
                bot.send_message(message.chat.id, "👥 إدارة المستخدمين:", reply_markup=manage_users_menu(uid))
                return
            return

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
                bot.send_message(message.chat.id, "📅 أدخل التاريخ:", reply_markup=date_suggestions_menu(subject=subj, uid=uid))
                return
            if step == "choose_date":
                d = parse_smart_date(text)
                if not d:
                    bot.send_message(message.chat.id, "❌ صيغة غير صحيحة. مثال: `27/02/2026`", parse_mode="Markdown", reply_markup=date_suggestions_menu(subject=state.get("subject", ""), uid=uid))
                    return
                user_state[uid]["date"] = d
                user_state[uid]["step"] = "waiting_files"
                bot.send_message(message.chat.id, "📎 أرسل الملف أو الملفات:", reply_markup=back_only_menu(uid))
                return
            if step == "confirm_files":
                if text == "✅ إرسال":
                    files  = state.get("pending_files", [])
                    col    = state.get("col", 4)
                    subj   = state.get("subject", "")
                    date   = state.get("date", "")
                    fids   = [f["file_id"] for f in files]
                    cap    = state.get("file_caption", "").strip()
                    # إذا يوجد كابشن → احفظ النص مع الملفات في نفس الخلية
                    if cap:
                        # نص|file_id1,file_id2
                        cell_val = cap + "|" + ",".join(fids)
                        rows_s = sheet.get_all_values()
                        saved = False
                        for i, row in enumerate(rows_s[1:], start=2):
                            if safe_get(row, 0) and parse_date(safe_get(row, 0)) == date and safe_get(row, 1) == subj:
                                sheet.update_cell(i, col + 1, cell_val)
                                saved = True; break
                        if not saved:
                            new_row = [""] * 8
                            new_row[0] = date; new_row[1] = subj; new_row[col] = cell_val
                            sheet.append_row(new_row, value_input_option="USER_ENTERED")
                        invalidate_sheet_cache()
                        bot.send_message(message.chat.id, bt("رسالة_تم_الحفظ", uid), reply_markup=main_menu(uid, admin=admin, owner=owner))
                    else:
                        if save_file_to_cell(date, subj, col, fids, merge=False):
                            bot.send_message(message.chat.id, bt("رسالة_تم_الحفظ", uid), reply_markup=main_menu(uid, admin=admin, owner=owner))
                        else:
                            bot.send_message(message.chat.id, bt("رسالة_خطأ", uid))
                    user_state.pop(uid, None)
                return
            return

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
                       bt("زر_اضافة_تنبيه", uid): "alert", bt("زر_اضافة_ملزمه", uid): "notes"}
            if step == "choose_type" and text in ADD_MAP:
                dtype = ADD_MAP[text]
                user_state[uid]["data_type"] = dtype
                if dtype == "lecture":
                    user_state[uid]["step"] = "enter_date"
                    bot.send_message(message.chat.id, "📅 أدخل تاريخ المحاضرة:", reply_markup=date_suggestions_menu(for_lecture=True, uid=uid))
                elif dtype == "notes":
                    # الملزمة بلا تاريخ → اختر مادة مباشرة
                    user_state[uid]["step"] = "choose_subject"
                    _kb_no, _ = subjects_with_noexist_kb(uid)
                    bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=_kb_no)
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
                elif dtype == "notes":
                    user_state[uid]["step"] = "enter_value"
                    bot.send_message(message.chat.id, "📋 أدخل رابط الملزمة أو نصها:", reply_markup=back_only_menu(uid))
                else:
                    user_state[uid]["step"] = "enter_date"
                    bot.send_message(message.chat.id, "📅 أدخل التاريخ:", reply_markup=date_suggestions_menu(subject=text, for_alert=(state.get("data_type") == "alert"), uid=uid))
                return
            if step == "enter_date":
                d = parse_smart_date(text)
                if not d:
                    bot.send_message(message.chat.id, "❌ صيغة غير صحيحة. مثال: `27/02/2026`", parse_mode="Markdown",
                                     reply_markup=date_suggestions_menu(for_lecture=(state.get("data_type") == "lecture"), for_alert=(state.get("data_type") == "alert"), uid=uid))
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
                    bot.send_message(message.chat.id,
                                     "⏰ أدخل الوقت بأي تنسيق:\n"
                                     "• `10-12` أو `10:00-12:00`\n"
                                     "• `من 11` (ساعتان تلقائياً)\n"
                                     "• `١٠-١٢` (أرقام عربية)\n"
                                     "• `10 to 12`",
                                     parse_mode="Markdown", reply_markup=back_with_noexist(uid))
                    return
                elif text == "لا يوجد":
                    time_val = "لا يوجد"
                else:
                    # أي نص آخر → حاول تحويله مباشرة
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
                    invalidate_sheet_cache()
                    bot.send_message(message.chat.id, bt("رسالة_تم_الحفظ", uid), reply_markup=main_menu(uid, admin=admin, owner=owner))
                    user_state.pop(uid, None)
                elif dtype == "notes":
                    rows_s = sheet.get_all_values()
                    updated = False
                    for i, row in enumerate(rows_s[1:], start=2):
                        if safe_get(row, 1) == subj:
                            sheet.update_cell(i, 9, val)
                            updated = True
                            break
                    if not updated:
                        sheet.append_row(["", subj, "", "", "", "", "", "", val], value_input_option="USER_ENTERED")
                    invalidate_sheet_cache()
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
                        bt("زر_تعديل_تنبيه", uid): "alert", bt("زر_تعديل_ملزمه", uid): "notes"}
            COL_MAP = {"lecture": 2, "task": 4, "summary": 6, "price": 5, "alert": 7, "notes": 8}
            if step == "choose_type" and text in EDIT_MAP:
                user_state[uid]["data_type"] = EDIT_MAP[text]
                user_state[uid]["step"] = "choose_subject"
                bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=subjects_kb)
                return
            if step == "choose_subject" and text in subjects_list:
                user_state[uid]["subject"] = text
                dtype = state.get("data_type", "")
                col = COL_MAP.get(dtype, 2)
                if dtype in ("price", "notes"):
                    col_idx = 5 if dtype == "price" else 8
                    matched = [r for r in data if safe_get(r, 1) == text]
                    current = next((get_text(safe_get(r, col_idx)) for r in matched if safe_get(r, col_idx)), "")
                    user_state[uid]["step"] = "choose_action"
                    user_state[uid]["current_val"] = current
                    user_state[uid]["date"] = ""
                    label = "سعر الملزمة" if dtype == "price" else "رابط/نص الملزمة"
                    bot.send_message(message.chat.id, f"*{label}* الحالي: *{current or 'فارغ'}*", parse_mode="Markdown", reply_markup=edit_action_menu(uid))
                else:
                    matched = [r for r in data if safe_get(r, 1) == text]
                    # فقط التواريخ اللي فيها بيانات للعمود المحدد (نوع البيانات المختار)
                    dates = list(dict.fromkeys(
                        parse_date(safe_get(r, 0)) for r in matched
                        if (get_text(safe_get(r, col)) or get_file_ids(safe_get(r, col)))
                        and safe_get(r, 0)
                    ))
                    # ترتيب: الأحدث في الأعلى
                    try:
                        dates.sort(key=lambda x: datetime.strptime(x, "%d/%m/%Y"), reverse=True)
                    except:
                        pass
                    if not dates:
                        bot.send_message(message.chat.id, bt("رسالة_لا_بيانات", uid), reply_markup=edit_data_menu(uid))
                        user_state[uid] = {"editing_data": True, "step": "choose_type"}
                    else:
                        user_state[uid]["step"] = "choose_date_edit"
                        user_state[uid]["col"] = col
                        user_state[uid]["dates_cache"] = dates
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
                    bot.send_message(message.chat.id, f"⚠️ هل أنت متأكد من حذف:\n*{cur}*؟", parse_mode="Markdown", reply_markup=mk_del)
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
                                sheet.update_cell(i, 6, ""); break
                        invalidate_sheet_cache()
                        bot.send_message(message.chat.id, bt("رسالة_تم_الحذف", uid), reply_markup=main_menu(uid, admin=admin, owner=owner))
                    elif dtype == "notes":
                        rows_s = sheet.get_all_values()
                        for i, row in enumerate(rows_s[1:], start=2):
                            if safe_get(row, 1) == subj:
                                sheet.update_cell(i, 9, ""); break
                        invalidate_sheet_cache()
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
                    invalidate_sheet_cache()
                    bot.send_message(message.chat.id, bt("رسالة_تم_التعديل", uid), reply_markup=main_menu(uid, admin=admin, owner=owner))
                elif dtype == "notes":
                    rows_s = sheet.get_all_values()
                    for i, row in enumerate(rows_s[1:], start=2):
                        if safe_get(row, 1) == subj:
                            sheet.update_cell(i, 9, text)
                            break
                    invalidate_sheet_cache()
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
@bot.callback_query_handler(func=lambda call: call.data.startswith("role_admin_") or call.data.startswith("role_user_") or call.data.startswith("role_owner_"))
def handle_role(call):
    caller_id = call.from_user.id
    if not is_owner_id(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح")
        return
    parts      = call.data.split("_", 2)
    btn        = parts[1]   # "admin" أو "user" أو "owner"
    target_uid = parts[2]
    decided_by = f"@{call.from_user.username}" if call.from_user.username else call.from_user.full_name

    try:
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if not row or row[2].strip().lstrip("'") != target_uid:
                continue
            cur_allow = row[3].strip().upper() if len(row) > 3 else "FALSE"
            cur_adm   = row[4].strip().upper() if len(row) > 4 else "FALSE"
            cur_own   = row[5].strip().upper() if len(row) > 5 else "FALSE"
            t_name    = row[0].strip()
            t_phone   = row[1].strip() if len(row) > 1 else ""

            # ── منطق زر ⭐ أدمن ──
            if btn == "admin":
                if cur_adm == "TRUE" and cur_own != "TRUE":
                    # أدمن + ضغط أدمن → إقفال كامل
                    users_sheet.update(f"D{i}:F{i}", [[False, False, False]])
                    label = "🔒 تم إقفال صلاحياته"
                    try: bot.send_message(int(target_uid), "🔒 تم إقفال صلاحيتك من البوت.")
                    except: pass
                    notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "remove")
                elif cur_own == "TRUE":
                    # مالك + ضغط أدمن → ينزل لأدمن
                    users_sheet.update(f"D{i}:F{i}", [[True, True, False]])
                    label = "⬇️ تخفيض لأدمن"
                    try: bot.send_message(int(target_uid), "⬇️ تم تخفيض رتبتك من مالك إلى أدمن.")
                    except: pass
                    notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "downgrade_owner")
                else:
                    # مستخدم / بدون صلاحية + ضغط أدمن → ترقية لأدمن
                    users_sheet.update(f"D{i}:F{i}", [[True, True, False]])
                    label = "⭐ تم تعيين أدمن"
                    try: bot.send_message(int(target_uid), "⭐ تهانينا! تمت ترقيتك إلى أدمن.")
                    except: pass
                    notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "set_admin")

            # ── منطق زر 👤 مستخدم ──
            elif btn == "user":
                if cur_allow == "TRUE" and cur_adm != "TRUE" and cur_own != "TRUE":
                    # مستخدم عادي + ضغط مستخدم → إلغاء صلاحية نهائياً
                    users_sheet.update(f"D{i}:F{i}", [[False, False, False]])
                    label = "⛔ تم إلغاء الصلاحية"
                    try: bot.send_message(int(target_uid), "⛔ تم إلغاء صلاحيتك من البوت.")
                    except: pass
                    notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "remove")
                elif cur_adm == "TRUE" and cur_own != "TRUE":
                    # أدمن + ضغط مستخدم → ينزل لمستخدم
                    users_sheet.update(f"D{i}:F{i}", [[True, False, False]])
                    label = "⬇️ تخفيض لمستخدم"
                    try: bot.send_message(int(target_uid), "⬇️ تم تخفيض رتبتك من أدمن إلى مستخدم عادي.")
                    except: pass
                    notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "downgrade_admin")
                elif cur_own == "TRUE":
                    # مالك + ضغط مستخدم → ينزل لمستخدم
                    users_sheet.update(f"D{i}:F{i}", [[True, False, False]])
                    label = "⬇️ تخفيض لمستخدم"
                    try: bot.send_message(int(target_uid), "⬇️ تم تخفيض رتبتك من مالك إلى مستخدم عادي.")
                    except: pass
                    notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "downgrade_owner_to_user")
                else:
                    # بدون صلاحية + ضغط مستخدم → منح صلاحية
                    users_sheet.update(f"D{i}:F{i}", [[True, False, False]])
                    label = "👤 تم منح الصلاحية"
                    try: bot.send_message(int(target_uid), bt("رسالة_موافقة", int(target_uid)))
                    except: pass
                    notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "set_user")

            # ── زر 👑 مالك (للحالات الخاصة) ──
            elif btn == "owner":
                users_sheet.update(f"D{i}:F{i}", [[True, True, True]])
                label = "👑 تم تعيين مالك"
                try: bot.send_message(int(target_uid), "👑 تهانينا! تمت ترقيتك إلى مالك.")
                except: pass
                notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "set_owner")
            else:
                bot.answer_callback_query(call.id, "❌ غير معروف")
                return

            invalidate_users_cache()
            update_user_card_in_chat(int(target_uid), call.message.chat.id)
            bot.answer_callback_query(call.id, label)
            return

        bot.answer_callback_query(call.id, "❌ المستخدم غير موجود")
    except Exception as e:
        log_error(f"handle_role: {e}")
        bot.answer_callback_query(call.id, "❌ خطأ")

@bot.callback_query_handler(func=lambda call: call.data.startswith("role_revoke_"))
def handle_role_revoke(call):
    """إلغاء صلاحية المستخدم نهائياً من البوت"""
    caller_id = call.from_user.id
    if not is_owner_id(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح")
        return
    target_uid = call.data.split("_", 2)[2]
    try:
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            cell_id = row[2].strip().lstrip("'") if len(row) > 2 else ""
            if cell_id != target_uid:
                continue
            t_name  = row[0].strip()
            t_phone = row[1].strip() if len(row) > 1 else ""
            decided_by = f"@{call.from_user.username}" if call.from_user.username else call.from_user.full_name
            # إلغاء كل الصلاحيات
            users_sheet.update(f"D{i}:F{i}", [[False, False, False]])
            try: bot.send_message(int(target_uid), "⛔ تم إلغاء صلاحيتك من البوت.")
            except: pass
            invalidate_users_cache()
            notify_owners_action(int(target_uid), t_name, t_phone, decided_by, "remove")
            update_user_card_in_chat(int(target_uid), call.message.chat.id)
            bot.answer_callback_query(call.id, "⛔ تم إلغاء الصلاحية نهائياً")
            return
        bot.answer_callback_query(call.id, "❌ المستخدم غير موجود")
    except Exception as e:
        log_error(f"handle_role_revoke: {e}")
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
    allowed = (action == "on")
    if set_ai_allowed(int(target_uid), allowed):
        label = "✅ تم تفعيل AI" if allowed else "❌ تم تعطيل AI"
        try:
            rows = users_sheet.get_all_values()
            for row in rows[1:]:
                if len(row) > 2 and row[2].strip().lstrip("'") == target_uid:
                    send_user_card(call.message.chat.id, row, edit_existing=True)
                    break
        except:
            pass
        bot.answer_callback_query(call.id, label)
    else:
        bot.answer_callback_query(call.id, "❌ فشل التحديث")

@bot.callback_query_handler(func=lambda call: call.data.startswith("rename_"))
def handle_rename_user(call):
    caller_id = call.from_user.id
    if not is_owner_id(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح")
        return
    target_uid = call.data.split("_")[1]
    user_state[caller_id] = {"renaming_user": target_uid, "step": "waiting_new_name"}
    bot.answer_callback_query(call.id, "✏️ أرسل الاسم الجديد للمستخدم")
    bot.send_message(
        call.message.chat.id,
        f"📝 أرسل الاسم الجديد للمستخدم (ID: `{target_uid}`):\n\n"
        f"يمكنك إرسال الاسم كاملاً (مثال: أحمد محمد)",
        parse_mode="Markdown",
        reply_markup=back_only_menu(caller_id)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("show_user_"))
def handle_show_user(call):
    uid_str = call.data.split("_")[2]
    _, row = find_user_row_by_id(uid_str)
    if row:
        send_user_card(call.message.chat.id, row)
        bot.answer_callback_query(call.id)
    else:
        bot.answer_callback_query(call.id, "❌ المستخدم غير موجود")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_role_"))
def handle_approve_with_role(call):
    caller_id = call.from_user.id
    if not is_owner_id(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح")
        return
    parts = call.data.split("_", 3)
    new_role = parts[2]
    short_key = parts[3]
    req_data = _approval_store.get(short_key)
    if not req_data:
        bot.answer_callback_query(call.id, "⚠️ انتهت صلاحية الطلب")
        return
    requester_id = req_data["requester_id"]
    requester_name = req_data["requester_name"]
    phone = req_data["phone"]
    decided_by = (f"@{call.from_user.username}" if call.from_user.username else call.from_user.full_name)
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
                if new_role == "owner":
                    users_sheet.update(f"D{i}:F{i}", [[True, True, True]])
                elif new_role == "admin":
                    users_sheet.update(f"D{i}:F{i}", [[True, True, False]])
                else:
                    users_sheet.update(f"D{i}:F{i}", [[True, False, False]])
                found = True
                break
        if not found:
            if new_role == "owner":
                users_sheet.append_row([requester_name, phone, requester_id, True, True, True, False, False, False, False, False])
            elif new_role == "admin":
                users_sheet.append_row([requester_name, phone, requester_id, True, True, False, False, False, False, False, False])
            else:
                users_sheet.append_row([requester_name, phone, requester_id, True, False, False, False, False, False, False, False])
        pending_requests.discard(requester_id)
        _approval_store.pop(short_key, None)
        role_name = "مالك" if new_role == "owner" else ("أدمن" if new_role == "admin" else "مستخدم")
        try:
            bot.send_message(requester_id, f"✅ تمت الموافقة على طلبك! رتبتك: {role_name}\nأرسل /start للبدء.")
        except:
            pass
        notify_owners_action(requester_id, requester_name, phone, decided_by, f"set_{new_role}")
        bot.answer_callback_query(call.id, f"✅ تمت الموافقة كـ {role_name}")
        msg_ids = request_msg_ids.pop(requester_id, {})
        for oid, mid in msg_ids.items():
            try:
                bot.delete_message(oid, mid)
            except:
                pass
    except Exception as e:
        log_error(f"approve_with_role: {e}")
        bot.answer_callback_query(call.id, "❌ خطأ في الحفظ")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_ai_on_"))
def handle_approve_with_ai(call):
    caller_id = call.from_user.id
    if not is_owner_id(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح")
        return
    short_key = call.data.split("_")[3]
    req_data = _approval_store.get(short_key)
    if not req_data:
        bot.answer_callback_query(call.id, "⚠️ انتهت صلاحية الطلب")
        return
    requester_id = req_data["requester_id"]
    requester_name = req_data["requester_name"]
    phone = req_data["phone"]
    decided_by = (f"@{call.from_user.username}" if call.from_user.username else call.from_user.full_name)
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
                users_sheet.update_cell(i, AI_ALLOWED_COL + 1, True)
                found = True
                break
        if not found:
            users_sheet.append_row([requester_name, phone, requester_id, True, False, False, False, False, False, True, False])
        pending_requests.discard(requester_id)
        _approval_store.pop(short_key, None)
        try:
            bot.send_message(requester_id, f"✅ تمت الموافقة على طلبك! رتبتك: مستخدم\n🤖 تم تفعيل المساعد الذكي لك!\nأرسل /start للبدء.")
        except:
            pass
        notify_owners_action(requester_id, requester_name, phone, decided_by, "set_user")
        notify_owners_action(requester_id, requester_name, phone, decided_by, "ai_enabled")
        bot.answer_callback_query(call.id, "✅ تمت الموافقة مع تفعيل AI")
        msg_ids = request_msg_ids.pop(requester_id, {})
        for oid, mid in msg_ids.items():
            try:
                bot.delete_message(oid, mid)
            except:
                pass
    except Exception as e:
        log_error(f"approve_with_ai: {e}")
        bot.answer_callback_query(call.id, "❌ خطأ في الحفظ")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") and not call.data.startswith("approve_role_") and not call.data.startswith("approve_ai_on_"))
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
        bot.answer_callback_query(call.id, "✅ تمت الموافقة")
        msg_ids = request_msg_ids.pop(requester_id, {})
        for oid, mid in msg_ids.items():
            try:
                bot.delete_message(oid, mid)
            except:
                pass
    except Exception as e:
        log_error(f"approve: {e}")
        bot.answer_callback_query(call.id, "❌ خطأ في الحفظ")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_"))
def handle_rejection(call):
    caller_id = call.from_user.id
    if not is_owner_id(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح")
        return
    short_key = call.data.split("_", 1)[1]
    req_data = _approval_store.get(short_key)
    if not req_data:
        bot.answer_callback_query(call.id, "⚠️ انتهت صلاحية الطلب")
        return
    requester_id = req_data["requester_id"]
    requester_name = req_data["requester_name"]
    phone = req_data["phone"]
    decided_by = (f"@{call.from_user.username}" if call.from_user.username else call.from_user.full_name)
    pending_requests.discard(requester_id)
    _approval_store.pop(short_key, None)
    try:
        bot.send_message(requester_id, bt("رسالة_رفض_طلب", requester_id))
    except:
        pass
    notify_owners_action(requester_id, requester_name, phone, decided_by, "reject")
    bot.answer_callback_query(call.id, "❌ تم الرفض")
    msg_ids = request_msg_ids.pop(requester_id, {})
    for oid, mid in msg_ids.items():
        try:
            bot.delete_message(oid, mid)
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_multi_"))
def handle_confirm_multi(call):
    short_key = call.data.split("_")[2]
    data = _temp_admin_actions.get(short_key)
    if not data or data["expires"] < time.time():
        bot.answer_callback_query(call.id, "انتهت صلاحية الطلب")
        return
    uid = data["uid"]
    for item in data["data"]:
        try:
            line = item.strip()
            executed, response = try_execute_admin_command(line, uid, get_user_role(uid), call.message.chat.id, bot)
            if executed:
                bot.send_message(call.message.chat.id, response)
            else:
                bot.send_message(call.message.chat.id, f"⚠️ لم يتم إضافة: {line[:100]}")
        except Exception as e:
            log_error(f"خطأ في إضافة بند متعدد: {e}")
    bot.answer_callback_query(call.id, "✅ تمت الإضافة")
    _temp_admin_actions.pop(short_key, None)
    bot.send_message(call.message.chat.id, "✅ تم إضافة جميع البيانات بنجاح.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_multi_"))
def handle_edit_multi(call):
    short_key = call.data.split("_")[2]
    data = _temp_admin_actions.get(short_key)
    if not data or data["expires"] < time.time():
        bot.answer_callback_query(call.id, "انتهت صلاحية الطلب")
        return
    bot.answer_callback_query(call.id, "✏️ أرسل النص المعدل")
    user_state[data["uid"]] = {"editing_multi": short_key, "original": data["original"]}
    bot.send_message(call.message.chat.id, "أرسل النص المعدل ليتم إعادة عرضه للتأكيد.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_multi_"))
def handle_reject_multi(call):
    short_key = call.data.split("_")[2]
    data = _temp_admin_actions.pop(short_key, None)
    bot.answer_callback_query(call.id, "❌ تم الإلغاء")
    bot.send_message(call.message.chat.id, "تم إلغاء إضافة البيانات.")

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

@bot.callback_query_handler(func=lambda call: call.data in ("ai_request_yes", "ai_request_no"))
def handle_ai_permission_request(call):
    uid = call.from_user.id
    load_user_lang(uid)
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=telebot.types.InlineKeyboardMarkup())
    except:
        pass
    if call.data == "ai_request_yes":
        # أرسل طلب لكل المالكين
        owners = get_owner_ids()
        name, phone = _get_user_name_phone(uid)
        ph = f"\n📞 `{phone}`" if phone else ""
        req_text = (
            f"🤖 *طلب صلاحية مساعد نايف*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {name}\n🆔 `{uid}`{ph}"
        )
        markup_owners = telebot.types.InlineKeyboardMarkup()
        markup_owners.row(
            _make_inline("زر_grant_ai", "✅ منح الصلاحية", f"grant_ai_{uid}"),
            _make_inline("زر_deny_ai",  "❌ رفض",           f"deny_ai_{uid}"),
        )
        sent_any = False
        for oid in owners:
            try:
                bot.send_message(oid, req_text, parse_mode="Markdown", reply_markup=markup_owners)
                sent_any = True
            except:
                pass
        if sent_any:
            bot.answer_callback_query(call.id, "✅ تم إرسال الطلب")
            bot.send_message(call.message.chat.id,
                             "⏳ تم إرسال طلبك للمالك. سيتم إخبارك عند الموافقة.")
        else:
            bot.answer_callback_query(call.id, "❌ فشل إرسال الطلب")
    else:
        bot.answer_callback_query(call.id, "تم الإلغاء")

@bot.callback_query_handler(func=lambda call: call.data.startswith("grant_ai_") or call.data.startswith("deny_ai_"))
def handle_ai_grant_deny(call):
    caller_id = call.from_user.id
    if not is_owner_id(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح")
        return
    parts = call.data.split("_", 2)
    action = parts[0]  # grant or deny
    target_uid = int(parts[2])
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=telebot.types.InlineKeyboardMarkup())
    except:
        pass
    if action == "grant":
        if set_ai_allowed(target_uid, True):
            name, _ = _get_user_name_phone(target_uid)
            bot.answer_callback_query(call.id, f"✅ تم منح الصلاحية لـ {name}")
            bot.send_message(call.message.chat.id, f"✅ تم منح صلاحية مساعد نايف لـ {name}")
            try:
                bot.send_message(target_uid,
                                 "🤖 *مساعد نايف*\n\n"
                                 "✅ تمت الموافقة على طلبك!\n"
                                 "اضغط على زر مساعد نايف في القائمة لتفعيله.",
                                 parse_mode="Markdown")
            except:
                pass
        else:
            bot.answer_callback_query(call.id, "❌ فشل التحديث")
    else:
        bot.answer_callback_query(call.id, "تم الرفض")
        bot.send_message(call.message.chat.id, "❌ تم رفض طلب صلاحية مساعد نايف")
        try:
            bot.send_message(target_uid, "❌ تم رفض طلب صلاحية مساعد نايف.")
        except:
            pass

# ─────────────────────────────────────────────────────
# Callbacks بطاقة الجدول الدراسي
# ─────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: call.data.startswith("sched_accept_"))
def handle_sched_accept(call):
    uid = call.from_user.id
    if not _is_admin_or_owner(uid):
        bot.answer_callback_query(call.id, "⛔ غير مسموح")
        return
    short_key = call.data[len("sched_accept_"):]
    card = _schedule_cards.get(short_key)
    if not card:
        bot.answer_callback_query(call.id, "⚠️ انتهت صلاحية البطاقة")
        return

    bot.answer_callback_query(call.id, "⏳ جاري الإضافة والتحقق...")

    # إزالة الأزرار فوراً
    try:
        bot.edit_message_reply_markup(card["chat_id"], card["msg_id"],
                                      reply_markup=telebot.types.InlineKeyboardMarkup())
    except:
        pass

    entries = card["entries"]
    verified_ok = []
    verified_fail = []
    save_errors = []

    for e in entries:
        subj   = e.get("subject", "").strip()
        date   = e.get("date", "").strip()
        time_v = e.get("time", "").strip()
        place  = e.get("place", "").strip()

        if not (subj and date and time_v):
            save_errors.append(f"⚠️ بيانات ناقصة: المادة={subj} التاريخ={date}")
            continue

        # تأكد من صيغة التاريخ
        try:
            parsed_date = parse_date(date)
        except:
            parsed_date = date

        # حفظ في الشيت
        saved = save_lecture(parsed_date, subj, time_v, place)
        if not saved:
            save_errors.append(f"❌ فشل الحفظ: {subj} | {parsed_date}")
            continue

        # ─── التحقق الفعلي من الشيت ───
        found_in_sheet = False
        try:
            all_rows = sheet.get_all_values()
            for row in all_rows[1:]:
                row_date = parse_date(safe_get(row, 0)) if safe_get(row, 0) else ""
                row_subj = safe_get(row, 1)
                row_time = safe_get(row, 2)
                if row_date == parsed_date and row_subj == subj:
                    found_in_sheet = True
                    break
        except Exception as ex:
            log_error(f"sched verify: {ex}")

        if found_in_sheet:
            verified_ok.append(f"✅ {subj}\n    📅 {parsed_date} | 🕒 {time_v} | 📍 {place}")
        else:
            verified_fail.append(f"⚠️ لم يُعثر عليه في الشيت: {subj} | {parsed_date}")

    # بناء رسالة النتيجة
    result_lines = []
    if verified_ok:
        result_lines.append("✅ *تم التحقق من إضافتها في الشيت:*")
        result_lines.extend(verified_ok)
    if verified_fail:
        result_lines.append("\n⚠️ *تمت المحاولة لكن لم يُتحقق منها:*")
        result_lines.extend(verified_fail)
    if save_errors:
        result_lines.append("\n❌ *أخطاء:*")
        result_lines.extend(save_errors)
    if not result_lines:
        result_lines.append("⚠️ لم يتم إضافة أي شيء.")

    result_text = "\n".join(result_lines)

    try:
        bot.edit_message_text(result_text, card["chat_id"], card["msg_id"],
                              parse_mode="Markdown",
                              reply_markup=telebot.types.InlineKeyboardMarkup())
    except:
        bot.send_message(card["chat_id"], result_text, parse_mode="Markdown")

    _schedule_cards.pop(short_key, None)


@bot.callback_query_handler(func=lambda call: call.data.startswith("sched_edit_"))
def handle_sched_edit(call):
    uid = call.from_user.id
    if not _is_admin_or_owner(uid):
        bot.answer_callback_query(call.id, "⛔ غير مسموح")
        return
    short_key = call.data[len("sched_edit_"):]
    card = _schedule_cards.get(short_key)
    if not card:
        bot.answer_callback_query(call.id, "⚠️ انتهت صلاحية البطاقة")
        return
    bot.answer_callback_query(call.id, "✏️ أرسل التعديل")
    user_state[uid] = {"editing_schedule": short_key}
    bot.send_message(card["chat_id"],
                     "✏️ أرسل النص المعدل أو التعديلات المطلوبة وسأعيد استخراج البيانات:")


@bot.callback_query_handler(func=lambda call: call.data.startswith("sched_cancel_"))
def handle_sched_cancel(call):
    uid = call.from_user.id
    short_key = call.data[len("sched_cancel_"):]
    card = _schedule_cards.pop(short_key, None)
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=telebot.types.InlineKeyboardMarkup())
    except:
        pass
    bot.answer_callback_query(call.id, "❌ تم الإلغاء")

def _check_bot_texts():
    """
    يفحص أن كل مفاتيح BOT_TEXTS موجودة وغير فارغة.
    يرسل تقرير عبر اللوج إذا وُجد نقص.
    يُستدعى فقط من _do_full_refresh.
    """
    if not LOG_BOT_TOKEN:
        return

    # كل المفاتيح المطلوبة (بدون لاحقة _ar/_en)
    required_keys = set()
    for k in DEFAULT_BOT_TEXTS.keys():
        # المفتاح الأساسي بدون _ar أو _en
        if k.endswith("_ar"):
            required_keys.add(k[:-3])
        elif k.endswith("_en"):
            required_keys.add(k[:-3])
        else:
            required_keys.add(k)

    missing = []
    empty   = []

    for key in sorted(required_keys):
        ar_val = BOT_TEXTS.get(f"{key}_ar", "")
        en_val = BOT_TEXTS.get(f"{key}_en", "")
        # غير موجود كلياً
        if not ar_val and not en_val:
            missing.append(key)
        # موجود لكن فارغ
        elif not ar_val:
            empty.append(f"{key} (ar فارغ)")
        elif not en_val:
            empty.append(f"{key} (en فارغ)")

    if not missing and not empty:
        log_info("✅ فحص bot_texts: جميع المفاتيح موجودة وكاملة")
        return

    # بناء التقرير
    lines = ["⚠️ *تحذير: نقص في bot_texts*", ""]
    if missing:
        lines.append(f"❌ *مفاتيح مفقودة كلياً ({len(missing)}):*")
        for k in missing:
            lines.append("  • `" + k + "`")
    if empty:
        lines.append("")
        lines.append(f"🟡 *مفاتيح فارغة ({len(empty)}):*")
        for k in empty:
            lines.append("  • `" + k + "`")
    lines.append("")
    lines.append("🔧 أضف المفاتيح الناقصة في صفحة bot_texts في الشيت.")

    report = "\n".join(lines)
    try:
        _requests.post(
            f"https://api.telegram.org/bot{LOG_BOT_TOKEN}/sendMessage",
            json={"chat_id": LOG_BOT_TOKEN, "text": report, "parse_mode": "Markdown"},
            timeout=5
        )
    except Exception as e:
        logger.warning(f"_check_bot_texts: فشل إرسال التقرير: {e}")


def _do_full_refresh():
    """
    يعيد قراءة كل شيء من الشيت:
    - bot_texts → BOT_TEXTS
    - ai_providers → AI_PROVIDERS (مع تحديث السويتش لكل مستخدم)
    - button_texts → BUTTON_TEXTS
    - يُبطل cache البيانات والمستخدمين
    ثم يتحقق من كل مستخدم سويتشه ON في الشيت → يُعيد تفعيله إذا صار AI مسموح
    """
    global AI_PROVIDERS
    invalidate_users_cache()
    invalidate_sheet_cache()
    load_bot_texts()
    load_button_texts()
    old_count = len(AI_PROVIDERS)
    load_ai_providers()
    new_count = len(AI_PROVIDERS)

    # إذا كل المزودين صاروا FALSE → امسح الذاكرة فقط (الشيت يبقى محفوظ للعودة)
    if not AI_PROVIDERS:
        user_ai_enabled.clear()

    # إذا عاد مزود واحد على الأقل → امسح الذاكرة كلها
    # حتى يُعاد تحميل حالة كل مستخدم من الشيت في رسالته القادمة
    elif AI_PROVIDERS and old_count == 0:
        user_ai_enabled.clear()  # سيُعاد تحميل كل مستخدم من الشيت عند أول رسالة

    # فحص اكتمال النصوص وإرسال تقرير عبر اللوج إذا وُجد نقص
    threading.Thread(target=_check_bot_texts, daemon=True).start()

    log_info(f"🔄 Refresh: providers {old_count}→{new_count}, users_cache invalidated")
    return new_count

def _sheet_cache_loop():
    """يحدّث الـ cache كل دقيقة تلقائياً"""
    while True:
        time.sleep(60)
        try:
            invalidate_users_cache()
            invalidate_sheet_cache()
            # إعادة تحميل AI providers للتحقق من التغييرات
            old_count = len(AI_PROVIDERS)
            load_ai_providers()
            new_count = len(AI_PROVIDERS)
            if old_count != new_count:
                load_button_texts()
                # auto-disable إذا صفر
                if not AI_PROVIDERS:
                    # نمسح الذاكرة فقط — الشيت يبقى محفوظ للعودة
                    user_ai_enabled.clear()
                # auto-enable إذا عاد → امسح الذاكرة، يُعاد تحميل كل مستخدم من الشيت
                elif old_count == 0:
                    user_ai_enabled.clear()
                log_info(f"🔄 auto-refresh: AI providers {old_count}→{new_count}")
        except:
            pass

def run():
    load_bot_texts()
    load_button_texts()
    load_ai_providers()
    set_bot_commands()
    if not AI_PROVIDERS:
        log_warning("⚠️ لا يوجد مزود AI نشط. لن يعمل المساعد الذكي.")
    else:
        log_info(f"✅ تم تحميل {len(AI_PROVIDERS)} مزود AI.")
    threading.Thread(target=_watch_sheet_loop, daemon=True).start()
    threading.Thread(target=_sheet_cache_loop, daemon=True).start()
    log_info("بوت الدراسة يعمل ✅")
    bot.infinity_polling()

if __name__ == "__main__":
    run()