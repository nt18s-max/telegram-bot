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

def run_bot1_with_restart():
    import study_bot
    while True:
        try:
            importlib.reload(study_bot)
            study_bot.run()
        except Exception as e:
            print(f"❌ Bot1 توقف: {e} — إعادة التشغيل بعد 5 ثواني...")
            time.sleep(5)

def run_bot2():
    import contact_bot
    contact_bot.run()

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    threading.Thread(target=run_bot1_with_restart, daemon=True).start()
    run_bot2()