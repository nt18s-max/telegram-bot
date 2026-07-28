"""
upload_request.py — طلب رفع ملف من قِبل المستخدم العادي وتدفق موافقة/رفض الأدمن.
"""

import telebot

from files_io import _try_send_file
from keyboards.main_kb import main_menu
from logging_utils import log_error
from sheets.users_repo import get_user_record, get_users


def process_user_upload_request(bot, chat_id: int, uid: int, subject: str, req_type: str, title: str, text: str, pending_files: list):
    """إرسال طلب رفع ملف من مستخدم عادي إلى جميع أدامن ومالكي النظام."""
    rec = get_user_record(uid) or {}
    user_name = rec.get("name", "مستخدم")

    allowed, admins, owners, _, _, _, _, _ = get_users()
    target_uids = list(set(admins + owners))

    type_name = "تكليف" if req_type == "assignment" else "ملخص"
    card_text = (
        f"📩 *طلب إضافة {type_name} جديد*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 الطالب: *{user_name}* (ID: `{uid}`)\n"
        f"📌 المادة: *{subject}*\n"
        f"📝 العنوان: *{title}*\n"
    )
    if text:
        card_text += f"📜 التفاصيل:\n{text}\n"
    card_text += "━━━━━━━━━━━━━━━━━━━━"

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("✅ موافقة ونشر", callback_data=f"approve_upload_{uid}"),
        telebot.types.InlineKeyboardButton("❌ رفض الطلب", callback_data=f"reject_upload_{uid}"),
    )

    count = 0
    for admin_id in target_uids:
        try:
            bot.send_message(admin_id, card_text, parse_mode="Markdown", reply_markup=markup)
            for pf in pending_files:
                _try_send_file(bot, admin_id, pf["file_id"], caption=pf.get("caption"))
            count += 1
        except Exception as e:
            log_error(f"process_user_upload_request to admin {admin_id}: {e}")

    if count > 0:
        bot.send_message(
            chat_id,
            "✅ تم إرسال طلبك للأدمن للمراجعة والنشر. شكراً لك!",
            reply_markup=main_menu(uid, admin=False, owner=False),
        )
    else:
        bot.send_message(
            chat_id,
            "❌ متعذّر إرسال الطلب للأدمن حالياً. حاول لاحقاً.",
            reply_markup=main_menu(uid, admin=False, owner=False),
        )


def handle_upload_request_callback(bot, call):
    """معالجة قرار الأدمن بموافقة أو رفض طلب رفع الملف."""
    data = call.data
    parts = data.rsplit("_", 1)
    if len(parts) < 2:
        return
    action, requester_id_str = parts[0], parts[1]
    if not requester_id_str.isdigit():
        return
    requester_id = int(requester_id_str)

    if action == "approve_upload":
        bot.answer_callback_query(call.id, "✅ تمت الموافقة على نشر الملف.")
        try:
            bot.send_message(requester_id, "🎉 تمت الموافقة على طلب رفع الملف الخاص بك ونشره بنجاح!")
        except Exception:
            pass
        try:
            bot.edit_message_text(call.message.text + "\n\n✅ *تمت الموافقة من الأدمن*", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        except Exception:
            pass

    elif action == "reject_upload":
        bot.answer_callback_query(call.id, "❌ تم رفض طلب النشر.")
        try:
            bot.send_message(requester_id, "❌ نعتذر، تم رفض طلب رفع الملف الخاص بك من قِبل الأدمن.")
        except Exception:
            pass
        try:
            bot.edit_message_text(call.message.text + "\n\n❌ *تم رفض الطلب*", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        except Exception:
            pass

