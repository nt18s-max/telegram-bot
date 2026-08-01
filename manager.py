# -*- coding: utf-8 -*-
"""
manager.py — المدير المركزي (Process Manager) + بوت الإدارة/البيع الموحّد.

الفكرة:
- هذا الملف يحل محل main.py كنقطة الدخول الرئيسية على Render.
- يقرأ "شيت الإدارة المركزي" (قائمة العملاء: توكناتهم، مفتاح شيت كل
  واحد، حالته active/stopped).
- لكل عميل active: يشغّل main.py الأصلي (بدون أي تعديل بمنطقه) كـ
  subprocess منفصل تماماً، مع env خاص بيه (توكناته + SHEET_KEY تبعه +
  منافذ داخلية فريدة حتى ما تتصادم مع بقية العملاء).
- يراقب كل subprocess ويعيد تشغيله لو وقع (نفس فلسفة main.py الأصلي،
  بس على مستوى "عميل كامل" بدل "بوت واحد").
- بوت تيليجرام واحد (ADMIN_BOT_TOKEN) يخدم غرضين بنفس الوقت:
    1) لوحة تحكم المالك: عرض حالة العملاء، إيقاف/تشغيل عميل، تسجيل
       عميل جديد بعد ما ينسخ المالك الشيت يدوياً من القالب.
    2) استقبال طلبات العملاء الجدد (يرسلوا توكن بوتهم) وتمريرها
       للمالك ليكمل خطوة نسخ الشيت يدوياً (حسب البرومبت الأصلي).
- Flask بسيط للـ health check على PORT (المطلوب من Render) — يشتغل
  مرة وحدة بس من هذا الملف، مش من أي subprocess عميل.

ملاحظات مهمة:
- لا تعديل إطلاقاً على study_test_bot.py / contact_bot.py / log_bot.py
  / stealth_bot.py — فقط main.py انعدّل تعديل بسيط (IS_PRIMARY لمنع
  تصادم Flask، و lock file بالـ CLIENT_ID).
- ميزة واتساب مو موجودة هون عمداً — الكود الحالي ما فيه أي شي متعلق
  فيها، فتم تجاهلها حسب توجيهك.
- الكود هذا ما تم اختباره على بيئة حقيقية (ما عندي وصول شبكة بهاي
  البيئة) — جرّبه أول بعميل تجريبي واحد على staging قبل ما تعتمد عليه
  بالإنتاج، وراجع تعليقات TODO المحدّدة بالأسفل.
"""

import os
import sys
import json
import time
import logging
import threading
import subprocess
from dataclasses import dataclass, field
from typing import Optional

import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import telebot
from flask import Flask

# ─────────────────────────────────────────────────────
# إعدادات عامة
# ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("manager")

BOT_DIR = os.path.dirname(os.path.abspath(__file__))  # مجلد main.py وبقية البوتات

GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")  # نفس Service Account المستخدم بكل البوتات
MANAGEMENT_SHEET_KEY = os.environ.get("MANAGEMENT_SHEET_KEY", "")

ADMIN_BOT_TOKEN = os.environ.get("ADMIN_BOT_TOKEN", "")
# يدعم أكثر من مالك مفصولين بفاصلة: OWNER_CHAT_IDS="111111,222222"
OWNER_CHAT_IDS = {
    int(x) for x in os.environ.get("OWNER_CHAT_IDS", "").replace(" ", "").split(",") if x
}

PORT = int(os.environ.get("PORT", 10000))

BASE_PORT = 20000     # أول منفذ داخلي يُخصَّص للعملاء (بعيد عن أي منفذ افتراضي قديم)
PORT_STEP = 10         # كل عميل ياخذ نطاق 10 منافذ (نستخدم 3 منها فعلياً، والباقي احتياط)
SYNC_INTERVAL_SEC = 30  # كل كم ثانية نعيد قراءة شيت الإدارة ونطابق الحالة
RESTART_BACKOFF_SEC = 5

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# أعمدة شيت الإدارة المركزي (الصف الأول = هيدر بنفس هاي الأسماء بالضبط)
COLUMNS = [
    "client_id",
    "client_name",
    "STUDY_TEST_TOKEN",
    "CONTACT_BOT_TOKEN",
    "STUDY_BOT_LOG_TOKEN",
    "STEALTH_BOT_TOKEN",
    "SHEET_KEY",
    "BOT_USERNAME",
    "port_base",
    "status",          # active / stopped
    "owner_chat_id",   # chat_id تبع العميل بالتيليجرام (لمعرفة مين يراسل مين)
    "created_at",
]


# ─────────────────────────────────────────────────────
# الاتصال بشيت الإدارة المركزي
# ─────────────────────────────────────────────────────
def _gspread_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(GOOGLE_CREDENTIALS), SCOPE
    ) if GOOGLE_CREDENTIALS else ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", SCOPE
    )
    return gspread.authorize(creds)


def _management_ws():
    gc = _gspread_client()
    sh = gc.open_by_key(MANAGEMENT_SHEET_KEY)
    return sh.sheet1


@dataclass
class ClientRecord:
    row_index: int  # رقم الصف بالشيت (1-based, يشمل الهيدر) — للتحديث السريع
    client_id: str
    client_name: str
    STUDY_TEST_TOKEN: str
    CONTACT_BOT_TOKEN: str
    STUDY_BOT_LOG_TOKEN: str
    STEALTH_BOT_TOKEN: str
    SHEET_KEY: str
    BOT_USERNAME: str
    port_base: int
    status: str
    owner_chat_id: str = ""
    created_at: str = ""


def load_clients() -> list:
    """يقرأ كل صفوف شيت الإدارة ويرجعها كقائمة ClientRecord."""
    ws = _management_ws()
    rows = ws.get_all_records()  # يعتمد على الهيدر بالصف الأول
    clients = []
    for i, row in enumerate(rows, start=2):  # الصف 1 هيدر، البيانات تبلش صف 2
        try:
            clients.append(ClientRecord(
                row_index=i,
                client_id=str(row.get("client_id", "")).strip(),
                client_name=str(row.get("client_name", "")).strip(),
                STUDY_TEST_TOKEN=str(row.get("STUDY_TEST_TOKEN", "")).strip(),
                CONTACT_BOT_TOKEN=str(row.get("CONTACT_BOT_TOKEN", "")).strip(),
                STUDY_BOT_LOG_TOKEN=str(row.get("STUDY_BOT_LOG_TOKEN", "")).strip(),
                STEALTH_BOT_TOKEN=str(row.get("STEALTH_BOT_TOKEN", "")).strip(),
                SHEET_KEY=str(row.get("SHEET_KEY", "")).strip(),
                BOT_USERNAME=str(row.get("BOT_USERNAME", "")).strip(),
                port_base=int(row.get("port_base") or 0),
                status=str(row.get("status", "")).strip().lower(),
                owner_chat_id=str(row.get("owner_chat_id", "")).strip(),
                created_at=str(row.get("created_at", "")).strip(),
            ))
        except Exception as e:
            logger.error(f"❌ صف {i} بشيت الإدارة فيه خطأ وتم تجاهله: {e}")
    return clients


def _next_free_port_base(existing: list) -> int:
    used = {c.port_base for c in existing if c.port_base}
    p = BASE_PORT
    while p in used:
        p += PORT_STEP
    return p


def add_client_row(client_id, client_name, tokens: dict, sheet_key,
                    bot_username="", owner_chat_id="") -> int:
    """يضيف صف عميل جديد ويرجع port_base اللي انخصص له."""
    ws = _management_ws()
    existing = load_clients()
    port_base = _next_free_port_base(existing)
    import datetime
    row = [
        client_id,
        client_name,
        tokens.get("STUDY_TEST_TOKEN", ""),
        tokens.get("CONTACT_BOT_TOKEN", ""),
        tokens.get("STUDY_BOT_LOG_TOKEN", ""),
        tokens.get("STEALTH_BOT_TOKEN", ""),
        sheet_key,
        bot_username,
        port_base,
        "active",
        str(owner_chat_id),
        datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    ]
    ws.append_row(row, value_input_option="RAW")
    return port_base


def update_status(row_index: int, status: str):
    ws = _management_ws()
    col = COLUMNS.index("status") + 1  # gspread 1-based
    ws.update_cell(row_index, col, status)


# ─────────────────────────────────────────────────────
# تشغيل/مراقبة عملية عميل واحد (subprocess = main.py الأصلي)
# ─────────────────────────────────────────────────────
class ClientProcess:
    def __init__(self, record: ClientRecord):
        self.record = record
        self.proc: Optional[subprocess.Popen] = None
        self.should_run = True
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def build_env(self) -> dict:
        env = os.environ.copy()
        env["CLIENT_ID"] = self.record.client_id
        env["IS_PRIMARY"] = "0"  # ما يحاول يفتح Flask على PORT المشترك
        env["STUDY_TEST_TOKEN"] = self.record.STUDY_TEST_TOKEN
        env["CONTACT_BOT_TOKEN"] = self.record.CONTACT_BOT_TOKEN
        env["STUDY_BOT_LOG_TOKEN"] = self.record.STUDY_BOT_LOG_TOKEN
        env["STEALTH_BOT_TOKEN"] = self.record.STEALTH_BOT_TOKEN
        env["SHEET_KEY"] = self.record.SHEET_KEY
        env["BOT_USERNAME"] = self.record.BOT_USERNAME
        pb = self.record.port_base or BASE_PORT
        env["INTERNAL_PORT"] = str(pb + 1)          # study_test_bot + log_bot (نفس القيمة)
        env["CONTACT_INTERNAL_PORT"] = str(pb + 2)  # contact_bot + log_bot
        env["STEALTH_INTERNAL_PORT"] = str(pb + 3)  # stealth_bot + log_bot
        return env

    def start(self):
        with self._lock:
            if self.proc and self.proc.poll() is None:
                return  # شغّال أصلاً
            self.should_run = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def stop(self):
        with self._lock:
            self.should_run = False
            if self.proc and self.proc.poll() is None:
                logger.info(f"⏹️ إيقاف عميل {self.record.client_id}...")
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    self.proc.kill()

    def is_alive(self) -> bool:
        return bool(self.proc and self.proc.poll() is None)

    def _run_loop(self):
        while self.should_run:
            env = self.build_env()
            logger.info(
                f"▶️ تشغيل عميل {self.record.client_id} "
                f"({self.record.client_name}) — منافذ ابتداءً من {env['INTERNAL_PORT']}"
            )
            try:
                self.proc = subprocess.Popen(
                    [sys.executable, "main.py"],
                    env=env,
                    cwd=BOT_DIR,
                )
                self.proc.wait()
            except Exception as e:
                logger.error(f"❌ فشل تشغيل عميل {self.record.client_id}: {e}")

            if not self.should_run:
                break
            logger.warning(
                f"⚠️ عميل {self.record.client_id} توقف (exit "
                f"{self.proc.returncode if self.proc else '?'}) — إعادة تشغيل بعد "
                f"{RESTART_BACKOFF_SEC}s"
            )
            time.sleep(RESTART_BACKOFF_SEC)


class ProcessManager:
    def __init__(self):
        self.clients: dict[str, ClientProcess] = {}
        self._lock = threading.Lock()

    def sync_from_sheet(self):
        try:
            records = load_clients()
        except Exception as e:
            logger.error(f"❌ فشل قراءة شيت الإدارة: {e}")
            return

        seen_ids = set()
        with self._lock:
            for rec in records:
                if not rec.client_id:
                    continue
                seen_ids.add(rec.client_id)
                cp = self.clients.get(rec.client_id)
                if cp is None:
                    cp = ClientProcess(rec)
                    self.clients[rec.client_id] = cp
                else:
                    cp.record = rec  # تحديث التوكنات/الحالة لو تغيّرت بالشيت

                if rec.status == "active" and not cp.is_alive():
                    cp.start()
                elif rec.status != "active" and cp.is_alive():
                    cp.stop()

            # عملاء انشالوا من الشيت بالكامل — نوقفهم احتياطاً
            for cid in list(self.clients.keys()):
                if cid not in seen_ids and self.clients[cid].is_alive():
                    logger.info(f"🗑️ عميل {cid} ما عاد موجود بالشيت — إيقاف")
                    self.clients[cid].stop()

    def status_text(self) -> str:
        with self._lock:
            if not self.clients:
                return "ما في عملاء مسجّلين بعد."
            lines = []
            for cid, cp in sorted(self.clients.items()):
                icon = "🟢" if cp.is_alive() else "🔴"
                lines.append(f"{icon} {cid} — {cp.record.client_name} ({cp.record.status})")
            return "\n".join(lines)

    def stop_client(self, client_id: str) -> bool:
        cp = self.clients.get(client_id)
        if not cp:
            return False
        cp.stop()
        return True

    def start_client(self, client_id: str) -> bool:
        cp = self.clients.get(client_id)
        if not cp:
            return False
        cp.start()
        return True

    def watchdog_loop(self):
        while True:
            self.sync_from_sheet()
            time.sleep(SYNC_INTERVAL_SEC)


manager = ProcessManager()


# ─────────────────────────────────────────────────────
# بوت الإدارة / البيع
# ─────────────────────────────────────────────────────
admin_bot = telebot.TeleBot(ADMIN_BOT_TOKEN) if ADMIN_BOT_TOKEN else None

# طلبات عملاء جدد قيد الانتظار (بانتظار ما المالك يسوي نسخ الشيت يدوياً
# ويعتمد الطلب). key = chat_id تبع العميل المرسل
PENDING_REQUESTS: dict = {}


def _is_owner(chat_id: int) -> bool:
    return chat_id in OWNER_CHAT_IDS


def _validate_bot_token(token: str) -> Optional[str]:
    """يتحقق من صحة توكن بوت عبر Telegram API، يرجع username البوت لو صح."""
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        data = r.json()
        if data.get("ok"):
            return data["result"].get("username", "")
    except Exception as e:
        logger.error(f"❌ فشل التحقق من التوكن: {e}")
    return None


if admin_bot:

    @admin_bot.message_handler(commands=["start"])
    def _cmd_start(msg):
        if _is_owner(msg.chat.id):
            admin_bot.reply_to(
                msg,
                "لوحة تحكم المالك:\n"
                "/clients — عرض حالة كل العملاء\n"
                "/stop <client_id> — إيقاف عميل\n"
                "/run <client_id> — تشغيل عميل\n"
                "/approve <chat_id> <sheet_key> [اسم العميل] — اعتماد طلب عميل جديد\n"
                "بعد ما تستلم توكن من عميل جديد، انسخ الشيت من القالب يدوياً "
                "ثم استخدم /approve.",
            )
        else:
            admin_bot.reply_to(
                msg,
                "أهلاً 👋 لبدء الاشتراك أرسل توكن بوتك (من BotFather) هنا.",
            )

    @admin_bot.message_handler(commands=["clients"])
    def _cmd_clients(msg):
        if not _is_owner(msg.chat.id):
            return
        admin_bot.reply_to(msg, manager.status_text())

    @admin_bot.message_handler(commands=["stop"])
    def _cmd_stop(msg):
        if not _is_owner(msg.chat.id):
            return
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2:
            admin_bot.reply_to(msg, "استخدم: /stop <client_id>")
            return
        cid = parts[1].strip()
        if manager.stop_client(cid):
            update_status(manager.clients[cid].record.row_index, "stopped")
            admin_bot.reply_to(msg, f"⏹️ تم إيقاف {cid}")
        else:
            admin_bot.reply_to(msg, "ما لقيت هاد الـ client_id")

    @admin_bot.message_handler(commands=["run"])
    def _cmd_run(msg):
        if not _is_owner(msg.chat.id):
            return
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2:
            admin_bot.reply_to(msg, "استخدم: /run <client_id>")
            return
        cid = parts[1].strip()
        if manager.start_client(cid):
            update_status(manager.clients[cid].record.row_index, "active")
            admin_bot.reply_to(msg, f"▶️ تم تشغيل {cid}")
        else:
            admin_bot.reply_to(msg, "ما لقيت هاد الـ client_id")

    @admin_bot.message_handler(commands=["approve"])
    def _cmd_approve(msg):
        if not _is_owner(msg.chat.id):
            return
        parts = msg.text.split(maxsplit=3)
        if len(parts) < 3:
            admin_bot.reply_to(msg, "استخدم: /approve <chat_id> <sheet_key> [اسم العميل]")
            return
        _, req_chat_id, sheet_key = parts[0], parts[1], parts[2]
        client_name = parts[3] if len(parts) > 3 else f"client_{req_chat_id}"

        pending = PENDING_REQUESTS.get(req_chat_id)
        if not pending:
            admin_bot.reply_to(msg, "ما في طلب معلّق بهاد الـ chat_id")
            return

        client_id = f"c{req_chat_id}"
        port_base = add_client_row(
            client_id=client_id,
            client_name=client_name,
            tokens=pending["tokens"],
            sheet_key=sheet_key,
            bot_username=pending.get("bot_username", ""),
            owner_chat_id=req_chat_id,
        )
        manager.sync_from_sheet()
        PENDING_REQUESTS.pop(req_chat_id, None)

        admin_bot.reply_to(
            msg,
            f"✅ تم تسجيل العميل {client_id} وتشغيله (منافذ ابتداءً من {port_base}).",
        )
        try:
            admin_bot.send_message(
                int(req_chat_id),
                "🎉 تم تفعيل بوتك بنجاح! جرّبه الحين.\n"
                "لو حاب تضيفنا Viewer على شيتك أرسل بريدك الإلكتروني هنا، "
                "ولو عندك مفتاح ذكاء اصطناعي خاص أرسله بصيغة:\nAI_KEY: <المفتاح>",
            )
        except Exception as e:
            logger.error(f"❌ ما قدرت أبلّغ العميل {req_chat_id}: {e}")

    @admin_bot.message_handler(func=lambda m: True, content_types=["text"])
    def _client_intake(msg):
        """أي رسالة نصية من غير المالك: نتعامل معها كطلب اشتراك جديد،
        أو بريد إلكتروني لعميل موجود (لإضافته Viewer)، أو مفتاح AI."""
        if _is_owner(msg.chat.id):
            return  # المالك يستخدم الأوامر فوق فقط

        text = (msg.text or "").strip()
        chat_id = str(msg.chat.id)

        # 1) توكن بوت جديد (نمط BotFather: أرقام:أحرف)
        import re
        if re.match(r"^\d+:[A-Za-z0-9_-]{30,}$", text):
            username = _validate_bot_token(text)
            if not username:
                admin_bot.reply_to(msg, "❌ التوكن غير صحيح، تأكد وحاول مرة ثانية.")
                return
            PENDING_REQUESTS[chat_id] = {
                "tokens": {
                    "STUDY_TEST_TOKEN": text,
                    # TODO: لو كل عميل بحاجة بوتات منفصلة فعلاً (تواصل/لوج/
                    # ستيلث) بتوكنات مختلفة، اطلبها بخطوات لاحقة بدل ما
                    # نفترض توكن واحد بس. حالياً نسجل التوكن الأساسي فقط
                    # ونترك الباقي فاضي (main.py أصلاً يتجاهل أي بوت
                    # توكنه فاضي).
                },
                "bot_username": username,
            }
            admin_bot.reply_to(
                msg,
                f"✅ التوكن صحيح (@{username}). تم إرسال طلبك للمالك، "
                "بينتظر تفعيل شيتك — بترجع لك رسالة تأكيد بعد شوي.",
            )
            for owner_id in OWNER_CHAT_IDS:
                try:
                    admin_bot.send_message(
                        owner_id,
                        f"📩 طلب اشتراك جديد!\nchat_id: {chat_id}\nبوت: @{username}\n\n"
                        f"1) انسخ الشيت من القالب يدوياً\n"
                        f"2) استخدم: /approve {chat_id} <sheet_key> [اسم العميل]",
                    )
                except Exception as e:
                    logger.error(f"❌ ما قدرت أبلّغ المالك {owner_id}: {e}")
            return

        # 2) بريد إلكتروني — إضافة العميل Viewer على شيته
        if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", text):
            rec = next(
                (c.record for c in manager.clients.values() if c.record.owner_chat_id == chat_id),
                None,
            )
            if not rec:
                admin_bot.reply_to(msg, "ما لقيت اشتراك مفعّل مربوط بحسابك بعد.")
                return
            try:
                gc = _gspread_client()
                gc.open_by_key(rec.SHEET_KEY).share(text, perm_type="user", role="reader")
                admin_bot.reply_to(msg, "✅ تمت إضافتك Viewer على شيتك.")
            except Exception as e:
                logger.error(f"❌ فشل مشاركة الشيت: {e}")
                admin_bot.reply_to(msg, "❌ صار خطأ بإضافتك، حاول لاحقاً.")
            return

        # 3) مفتاح AI بصيغة "AI_KEY: xxxx"
        if text.upper().startswith("AI_KEY:"):
            rec = next(
                (c.record for c in manager.clients.values() if c.record.owner_chat_id == chat_id),
                None,
            )
            if not rec:
                admin_bot.reply_to(msg, "ما لقيت اشتراك مفعّل مربوط بحسابك بعد.")
                return
            key_value = text.split(":", 1)[1].strip()
            try:
                gc = _gspread_client()
                sh = gc.open_by_key(rec.SHEET_KEY)
                # TODO: عدّل اسم التبويب/الأعمدة حسب بنية ai_providers
                # الفعلية بشيت القالب — هذا افتراض بسيط.
                ws = sh.worksheet("ai_providers")
                ws.append_row([key_value], value_input_option="RAW")
                admin_bot.reply_to(msg, "✅ تم حفظ مفتاح الذكاء الاصطناعي.")
            except Exception as e:
                logger.error(f"❌ فشل حفظ مفتاح AI: {e}")
                admin_bot.reply_to(msg, "❌ صار خطأ بالحفظ، حاول لاحقاً.")
            return

        admin_bot.reply_to(
            msg,
            "أرسل توكن بوتك للاشتراك، أو بريدك الإلكتروني، أو مفتاح AI بصيغة:\nAI_KEY: <المفتاح>",
        )


# ─────────────────────────────────────────────────────
# Flask للـ health check (المطلوب من Render)
# ─────────────────────────────────────────────────────
health_app = Flask(__name__)


@health_app.route("/")
def _health():
    return {"status": "ok", "clients": manager.status_text().splitlines()}


# ─────────────────────────────────────────────────────
# نقطة الدخول
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    if not MANAGEMENT_SHEET_KEY:
        logger.error("❌ MANAGEMENT_SHEET_KEY غير موجود بمتغيرات البيئة — إيقاف.")
        sys.exit(1)

    manager.sync_from_sheet()
    threading.Thread(target=manager.watchdog_loop, daemon=True).start()

    if admin_bot:
        threading.Thread(
            target=lambda: admin_bot.infinity_polling(),
            daemon=True,
        ).start()
        logger.info("✅ بوت الإدارة/البيع شغّال")
    else:
        logger.warning("⚠️ ADMIN_BOT_TOKEN غير موجود — بوت الإدارة لن يشتغل (بس الـ Process Manager شغّال)")

    logger.info(f"▶️ تشغيل Flask (health check) على port {PORT}...")
    health_app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
