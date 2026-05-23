import threading
import os
import time
import subprocess
import sys

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

    # log_bot — يشتغل فقط إذا STUDY_BOT_LOG_TOKEN موجود
    threading.Thread(
        target=run_bot_subprocess,
        args=("log_bot.py", "STUDY_BOT_LOG_TOKEN"),
        daemon=True
    ).start()

    # stealth_bot
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
