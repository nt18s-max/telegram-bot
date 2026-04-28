import threading
import os
import time
import subprocess
import sys
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

def run_bot_subprocess(script_name, token_var):
    while True:
        if not os.environ.get(token_var):
            print(f"ℹ️ {token_var} غير موجود — {script_name} لن يشتغل")
            return
        print(f"▶️ تشغيل {script_name}...")
        proc = subprocess.Popen(
            [sys.executable, script_name],
            env=os.environ.copy()
        )
        proc.wait()
        print(f"❌ {script_name} توقف (exit {proc.returncode}) — إعادة التشغيل بعد 5 ثواني...")
        time.sleep(5)

def run_flask_server():
    """يشغل سيرفر التطبيق الذكي على port 5001"""
    try:
        from server.app import app
        port = int(os.environ.get("APP_SERVER_PORT", 5001))
        print(f"▶️ تشغيل سيرفر التطبيق على port {port}...")
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ خطأ في سيرفر التطبيق: {e}")

if __name__ == "__main__":
    # HTTP Keep-alive
    threading.Thread(target=run_server, daemon=True).start()

    # study_bot
    threading.Thread(
        target=run_bot_subprocess,
        args=("study_bot.py", "STUDY_BOT_TOKEN"),
        daemon=True
    ).start()

    # study_test_bot
    threading.Thread(
        target=run_bot_subprocess,
        args=("study_test_bot.py", "STUDY_TEST_TOKEN"),
        daemon=True
    ).start()

    # contact_bot
    threading.Thread(
        target=run_bot_subprocess,
        args=("contact_bot.py", "CONTACT_BOT_TOKEN"),
        daemon=True
    ).start()

    # سيرفر التطبيق الذكي ← جديد
    threading.Thread(
        target=run_flask_server,
        daemon=True
    ).start()

    print("✅ جميع البوتات والسيرفر تم تشغيلها")
    while True:
        time.sleep(60)