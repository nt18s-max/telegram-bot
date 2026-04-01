# ====================================================
# study_test_bot.py — النسخة التجريبية الكاملة المعدلة
# الميزة المضافة: إخفاء الـ AI صامتاً بناءً على Checkbox العمود K
# ====================================================

import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import os, json, threading, time, requests, re
from dotenv import load_dotenv

load_dotenv()

# ── إعدادات الوصول ──────────────────────────────────
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("telegram-bot") # تأكد من مطابقة اسم الشيت
except Exception as e:
    print(f"❌ خطأ اتصال الشيت: {e}")

BOT_TOKEN = os.getenv("STUDY_BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

AI_PROVIDERS = []

# ── التعديل: تحميل المزودين بصمت (العمود K) ──────────
def load_ai_providers():
    global AI_PROVIDERS
    try:
        ws = spreadsheet.worksheet("ai_providers")
        records = ws.get_all_records()
        
        # فلترة المزودين: يجب أن يكون Active (العمود K) هو TRUE ومفتاح API موجود
        AI_PROVIDERS = [
            r for r in records 
            if str(r.get('Active', '')).upper() == 'TRUE' and r.get('API_Key', '').strip()
        ]
        # تم حذف رسائل الـ log_warning لضمان الصمت التام
        return True
    except:
        AI_PROVIDERS = []
        return False

# ── دالة الاتصال بـ OpenRouter (المنطق الأصلي) ────────
def call_active_provider(prompt):
    if not AI_PROVIDERS: return None
    provider = AI_PROVIDERS[0] # يأخذ أول مزود مفعل في القائمة
    try:
        headers = {
            "Authorization": f"Bearer {provider['API_Key']}",
            "Content-Type": "application/json"
        }
        data = {
            "model": provider.get('Model', 'google/gemini-2.0-flash-exp:free'),
            "messages": [{"role": "user", "content": prompt}]
        }
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=15)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
    except:
        return None
    return None

# ── التعديل: معالج الرسائل الذكي (إخفاء الـ AI) ──────
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    # [هنا يتم وضع كود فحص الصلاحيات والمستخدمين الأصلي الخاص بك]
    
    # فحص حالة الذكاء الاصطناعي
    if AI_PROVIDERS:
        # إذا وجدنا علامة "صح" في الشيت، تظهر ميزة نايف يكتب
        try:
            status_msg = bot.reply_to(message, "⏳ نايف يكتب...")
            response = call_active_provider(message.text)
            bot.delete_message(message.chat.id, status_msg.message_id)
            
            if response:
                bot.reply_to(message, response)
            else:
                # إذا فشل الـ API، ابحث في البيانات التقليدية بصمت
                perform_standard_search(message)
        except:
            perform_standard_search(message)
    else:
        # "الوضع الصامت": إذا الكل FALSE، البوت يتجاهل الـ AI تماماً
        # وينتقل فوراً للبحث في القاعات والمواد والملفات
        perform_standard_search(message)

def perform_standard_search(message):
    """
    هذه الدالة تحتوي على كود البحث الأصلي في صفحة 'البيانات' 
    وصفحة 'القاعات والمواد' وإرسال الردود الثابتة.
    """
    # [يتم نسخ منطق البحث الأصلي الخاص بك هنا]
    pass

# ── تشغيل البوت ────────────────────────────────────
def run():
    # تحميل النصوص والأزرار (دوالك الأصلية)
    # load_bot_texts()
    # load_button_texts()
    
    load_ai_providers() # تحميل المزودين حسب حالة الشيت
    
    # set_bot_commands()
    
    print("🚀 Study Test Bot is running...")
    bot.polling(none_stop=True)

if __name__ == "__main__":
    run()
