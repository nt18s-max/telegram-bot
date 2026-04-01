import threading
import os
import time
import importlib
from http.server import HTTPServer, BaseHTTPRequestHandler

class KeepAlive(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bots are running!")
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), KeepAlive)
    server.serve_forever()

# تشغيل البوت الأساسي (Study Bot)
def run_bot1_with_restart():
    import study_bot
    while True:
        try:
            importlib.reload(study_bot)
            study_bot.run()
        except Exception as e:
            print(f"❌ Bot1 (Study) توقف: {e} — إعادة التشغيل...")
            time.sleep(5)

# تشغيل البوت الجديد (Test Bot) 
def run_test_bot_with_restart():
    import study_test_bot
    while True:
        try:
            importlib.reload(study_test_bot)
            study_test_bot.run()
        except Exception as e:
            print(f"❌ Test Bot توقف: {e} — إعادة التشغيل...")
            time.sleep(5)

if __name__ == "__main__":
    # 1. تشغيل السيرفر للبقاء حياً على Render
    threading.Thread(target=run_server, daemon=True).start()
    
    # 2. تشغيل البوت الأساسي
    threading.Thread(target=run_bot1_with_restart, daemon=True).start()
    
    # 3. تشغيل البوت التجريبي الجديد
    threading.Thread(target=run_test_bot_with_restart, daemon=True).start()

    # 4. بوت التواصل يشتغل في الـ Main Thread (لأنه asyncio)
    import contact_bot
    contact_bot.run()
