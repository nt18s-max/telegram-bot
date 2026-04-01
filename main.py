import threading
import time
import os

def run_original_bot():
    try:
        import study_bot
        study_bot.run()
    except Exception as e:
        print(f"Error in Original Bot: {e}")

def run_test_bot():
    try:
        import study_test_bot
        study_test_bot.run()
    except Exception as e:
        print(f"Error in Test Bot: {e}")

if __name__ == "__main__":
    # تشغيل البوت الأصلي في Thread
    t1 = threading.Thread(target=run_original_bot)
    t1.start()

    # تشغيل بوت التجربة في Thread آخر
    t2 = threading.Thread(target=run_test_bot)
    t2.start()
    
    # ابقاء البرنامج حياً
    t1.join()
    t2.join()
