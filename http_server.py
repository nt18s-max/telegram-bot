"""
http_server.py — خادم HTTP الداخلي والتكامل مع بوت اللوج لتحديث الكاش ومراقبة الحالة.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import threading
import urllib.parse as _urlparse

import config
from ai.providers import AI_PROVIDERS, load_ai_providers
from logging_utils import log_info, log_error
from sheets.data_repo import refresh_data_cache, TAB_SHEETS
from sheets.texts_repo import load_bot_texts, BOT_TEXTS
from sheets.users_repo import refresh_users_cache, get_users, get_log_user_ids

INTERNAL_PORT = int(os.environ.get("INTERNAL_PORT", config.INTERNAL_PORT))
_INTERNAL_SECRET = os.environ.get("INTERNAL_SECRET", config.INTERNAL_SECRET)


class _InternalHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()
            params = dict(_urlparse.parse_qsl(body))
            secret = params.get("secret", "")
            if secret != _INTERNAL_SECRET:
                self._respond(403, "forbidden")
                return
            cmd = params.get("cmd", "")
            result = _handle_internal_cmd(cmd)
            self._respond(200, result)
        except Exception as e:
            self._respond(500, str(e))

    def _respond(self, code: int, text: str):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(text.encode())

    def log_message(self, *args):
        pass


def _handle_internal_cmd(cmd: str) -> str:
    """تنفيذ أوامر تحديث الكاش القادمة عبر HTTP من بوت اللوج."""
    if cmd == "refresh_texts":
        load_bot_texts()
        return f"✅ تم تحديث النصوص — {len(BOT_TEXTS)} مفتاح"

    elif cmd == "refresh_users":
        refresh_users_cache()
        r = get_users()
        return f"✅ تم تحديث المستخدمين — {len(r[0])} مصرح"

    elif cmd == "refresh_ai":
        old = len(AI_PROVIDERS)
        load_ai_providers()
        new = len(AI_PROVIDERS)
        return f"✅ AI providers: {old}→{new}"

    elif cmd == "refresh_data":
        refresh_data_cache()
        return "✅ تم تحديث كاش كل صفحات البيانات"

    elif cmd == "refresh_all":
        load_bot_texts()
        refresh_users_cache()
        old = len(AI_PROVIDERS)
        load_ai_providers()
        new = len(AI_PROVIDERS)
        refresh_data_cache()
        return f"✅ تحديث كامل — AI: {old}→{new}, نصوص: {len(BOT_TEXTS)}"

    elif cmd == "status":
        log_users = get_log_user_ids()
        return (
            f"📊 حالة البوت\n"
            f"🤖 AI providers: {len(AI_PROVIDERS)}\n"
            f"📝 نصوص: {len(BOT_TEXTS)} مفتاح\n"
            f"👁 مستخدمو اللوج: {len(log_users)}"
        )
    else:
        return "❌ أمر غير معروف"


def start_internal_server():
    """تشغيل خادم HTTP الداخلي في thread مستقل خلفي."""

    def _run():
        try:
            server = HTTPServer(("0.0.0.0", INTERNAL_PORT), _InternalHandler)
            log_info(f"🌐 Internal HTTP server running on port {INTERNAL_PORT}")
            server.serve_forever()
        except Exception as e:
            log_error(f"❌ Failed to start internal HTTP server: {e}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
