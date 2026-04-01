import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os, json, requests, threading
from dotenv import load_dotenv

load_dotenv()

# --- الإعدادات ---
# تأكد من إضافة STUDY_TEST_TOKEN في ريندر
TEST_TOKEN = os.getenv("STUDY_TEST_TOKEN")
test_bot = telebot.TeleBot(TEST_TOKEN)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
client = gspread.authorize(creds)
spreadsheet = client.open("telegram-bot") # تأكد من اسم الشيت بدقة

AI_PROVIDERS = []

def load_ai_providers():
    global AI_PROVIDERS
    try:
        ws = spreadsheet.worksheet("ai_providers")
        records = ws.get_all_records()
        # المنطق المطلوب: فحص العمود K (Active) والمفتاح
        AI_PROVIDERS = [
            r for r in records 
            if str(r.get('Active', '')).upper() == 'TRUE' and r.get('API_Key', '').strip()
        ]
        return True
    except:
        AI_PROVIDERS = []
        return False

def call_openrouter(text):
    if not AI_PROVIDERS: return None
    p = AI_PROVIDERS[0]
    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {p['API_Key']}", "Content-Type": "application/json"},
            json={"model": p.get('Model', 'google/gemini-2.0-flash-exp:free'), "messages": [{"role": "user", "content": text}]},
            timeout=15
        )
        return res.json()['choices'][0]['message']['content'] if res.status_code == 200 else None
    except: return None

@test_bot.message_handler(func=lambda message: True)
def handle_messages(message):
    load_ai_providers() # تحديث الحالة من الشيت مع كل رسالة للاختبار
    
    if AI_PROVIDERS:
        try:
            status_msg = test_bot.reply_to(message, "⏳ نايف يكتب (نسخة التجربة)...")
            reply = call_openrouter(message.text)
            test_bot.delete_message(message.chat.id, status_msg.message_id)
            if reply:
                test_bot.reply_to(message, reply)
            else:
                test_bot.reply_to(message, "الرد التقليدي: (فشل الـ AI)")
        except:
            test_bot.reply_to(message, "الرد التقليدي: (حدث خطأ)")
    else:
        # الوضع الصامت: لا يوجد AI مفعل في الشيت
        test_bot.reply_to(message, "مرحباً! أنا في وضع الردود التقليدية لأن الذكاء الاصطناعي معطل في الشيت.")

def run():
    print("🚀 البوت التجريبي بدأ العمل...")
    test_bot.polling(none_stop=True)
