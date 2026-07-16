import threading
import os
import time
import subprocess
import sys
import fcntl

# ─────────────────────────────────────────────────────
# قفل ملف — يمنع تشغيل أكثر من نسخة من main.py بنفس الوقت
# (يحصل أحياناً عند ريستارت مزدوج من Render أثناء النشر،
#  ويسبب تعارض 409 على توكنات تيليجرام لكل البوتات)
# ─────────────────────────────────────────────────────
_LOCK_FILE = "/tmp/study_bot_main.lock"

def acquire_single_instance_lock():
    lock_fd = open(_LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("⛔ نسخة ثانية من main.py شغّالة بالفعل — هذي النسخة بتنسحب فوراً لتفادي تعارض التوكنات (409).")
        sys.exit(0)
    lock_fd.write(str(os.getpid()))
    lock_fd.flush()
    return lock_fd  # نحتفظ بالمرجع حتى لا يُغلق القفل تلقائياً

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

if __name__ == "__main__":
    _lock_handle = acquire_single_instance_lock()  # يوقف العملية فوراً لو فيه نسخة ثانية شغّالة

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

    # log_bot — يشتغل فقط إذا STUDY_BOT_LOG_TOKEN موجود
    threading.Thread(
        target=run_bot_subprocess,
        args=("log_bot.py", "STUDY_BOT_LOG_TOKEN"),
        daemon=True
    ).start()

    # stealth_bot — بوت التشفير
    threading.Thread(
        target=run_bot_subprocess,
        args=("stealth_bot.py", "STEALTH_BOT_TOKEN"),
        daemon=True
    ).start()

    print("✅ جميع البوتات تم تشغيلها")

    # Flask يشتغل على PORT الرئيسي — آخر شيء في الكود
    try:
        from server.app import app
        port = int(os.environ.get("PORT", 10000))
        print(f"▶️ تشغيل Flask على port {port}...")
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ خطأ في Flask: {e}")
        while True:
            time.sleep(60)
