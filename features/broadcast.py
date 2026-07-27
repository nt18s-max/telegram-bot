"""
broadcast.py — البث العام، إشعارات النشر التلقائي، وإرسال الإشعارات المستهدفة.
"""

from files_io import _try_send_file
from keyboards.main_kb import main_menu
from logging_utils import log_info, log_error
from sheets.users_repo import (
    get_users,
    get_all_registered_uids,
    get_user_record,
)


def notify_auto_publish(bot, title: str, message: str, file_ids: list = None):
    """إرسال إشعار للمشتركين بخدمة 'النشر التلقائي' عند إضافة المحتوى الجديد."""
    try:
        allowed, admins, owners, open_all, admin_all, log_ids, ai_allowed, auto_publish_uids = get_users()
        if not auto_publish_uids:
            return
        full_msg = f"{title}\n━━━━━━━━━━━━━━━━━━━━\n{message}"
        success = 0
        fail = 0
        for uid in auto_publish_uids:
            try:
                if file_ids:
                    for fid in file_ids:
                        _try_send_file(bot, uid, fid, caption=full_msg[:1024])
                else:
                    bot.send_message(uid, full_msg, parse_mode="Markdown")
                success += 1
            except Exception:
                fail += 1
        if success > 0:
            log_info(f"إشعارات النشر التلقائي: {success} نجاح, {fail} فشل")
    except Exception as e:
        log_error(f"notify_auto_publish: {e}")


def do_broadcast(bot, chat_id: int, uid: int, admin: bool, owner: bool, text_msg: str, files_data: list):
    """تنفيذ بث إشعار عام من قِبل الأدمن/المالك."""
    try:
        allowed, admins, owners, open_all, admin_all, log_ids, ai_allowed, auto_publish_uids = get_users()
        uids = allowed if not open_all else get_all_registered_uids()
        if not uids:
            bot.send_message(chat_id, "⚠️ لا يوجد مستخدمون.")
            return

        success = 0
        fail = 0
        for user_id in uids:
            try:
                if text_msg:
                    bot.send_message(user_id, f"📢 *إشعار:*\n\n{text_msg}", parse_mode="Markdown")
                for fd in files_data or []:
                    _try_send_file(bot, user_id, fd.get("file_id"))
                success += 1
            except Exception:
                fail += 1

        bot.send_message(
            chat_id,
            f"✅ تم الإرسال!\n✅ {success} | ❌ {fail}",
            reply_markup=main_menu(uid, admin=admin, owner=owner),
        )
    except Exception as e:
        log_error(f"do_broadcast: {e}")


def send_direct_notification(bot, target_id_or_all: str, text: str) -> tuple:
    """إرسال إشعار موجه لمستخدم محدد بالـ ID أو للجميع."""
    try:
        target = str(target_id_or_all).strip().lower()
        if target in ("all", "الجميع", "الكل"):
            uids = get_all_registered_uids()
            count = 0
            for u in uids:
                try:
                    bot.send_message(u, f"📢 *إشعار إداري:*\n\n{text}", parse_mode="Markdown")
                    count += 1
                except Exception:
                    pass
            return True, f"✅ تم إرسال الإشعار لـ {count} مستخدم."
        elif target.isdigit():
            uid = int(target)
            bot.send_message(uid, f"📢 *إشعار إداري:*\n\n{text}", parse_mode="Markdown")
            return True, f"✅ تم إرسال الإشعار للمستخدم `{uid}` بنجاح."
        else:
            return False, "❌ المعرّف غير صحيح."
    except Exception as e:
        return False, f"❌ حدث خطأ أثناء إرسال الإشعار: {e}"
