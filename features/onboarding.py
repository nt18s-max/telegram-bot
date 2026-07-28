"""
onboarding.py — الانضمام، التحقق من الصلاحيات، تسجيل الزوار الجدد، والرمز السري.
"""

from datetime import datetime
import time

import telebot

import config
from logging_utils import log_error
from sheets.texts_repo import bt, _make_inline
from sheets.users_repo import (
    users_sheet,
    refresh_users_cache,
    get_owner_ids,
    find_user_row_by_id,
)

_approval_counter = [0]
_approval_store = {}
request_msg_ids = {}
_last_notifications = {}
_NOTIFICATION_COOLDOWN = 10


def _register_new_visitor(message):
    """يسجّل الزائر الجديد في شيت المستخدمين بعلامة 🆕️ إن لم يكن مسجَّلاً مسبقاً."""
    try:
        if not users_sheet:
            return
        uid_str = str(message.from_user.id)
        rows = users_sheet.get_all_values()[1:]
        for row in rows:
            if len(row) > 2 and row[2].strip().lstrip("'") == uid_str:
                return
        name = message.from_user.full_name or "مجهول"
        users_sheet.append_row(
            [f"🆕️ {name}", "", message.from_user.id,
             False, False, False, False, False, False, False, False, False],
            value_input_option="USER_ENTERED",
        )
        refresh_users_cache()
    except Exception as e:
        log_error(f"_register_new_visitor: {e}")


def calc_secret_code(uid: int) -> str:
    """حساب الكود السري للتفعيل اليدوي السريع."""
    day = datetime.now(config.YEMEN_TZ).day
    total = sum(int(d) for d in str(uid)) + day
    return str(total)


def notify_owners_new_request(bot, requester_id: int, requester_name: str, phone: str = ""):
    """إرسال بطاقة طلب انضمام جديد للمالكين مع أزرار التفاعل."""
    owners = get_owner_ids()
    _approval_counter[0] += 1
    short_key = str(_approval_counter[0])
    _approval_store[short_key] = {
        "requester_id": requester_id,
        "requester_name": requester_name,
        "phone": phone,
    }
    ph = f"\n📞 `{phone}`" if phone else ""
    text = (
        f"❌ *طلب انضمام جديد*\n━━━━━━━━━━━━━━━━━━━━\n"
        f"❌ {requester_name}\n🆔 `{requester_id}`{ph}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        _make_inline("زر_approve_admin", bt("زر_approve_admin"), f"approve_role_admin_{short_key}"),
        _make_inline("زر_approve_user", bt("زر_approve_user"), f"approve_role_user_{short_key}"),
    )
    markup.row(
        _make_inline("زر_approve_rename", bt("زر_approve_rename"), f"approve_rename_{short_key}"),
        _make_inline("زر_approve_ai", bt("زر_approve_ai"), f"approve_ai_on_{short_key}"),
        _make_inline("زر_reject", bt("زر_reject"), f"reject_{short_key}"),
    )
    if requester_id not in request_msg_ids:
        request_msg_ids[requester_id] = {}
    for oid in owners:
        try:
            sent = bot.send_message(oid, text, parse_mode="Markdown", reply_markup=markup)
            request_msg_ids[requester_id][oid] = sent.message_id
        except Exception:
            pass


def notify_owners_action(target_id, target_name, phone, actor, action):
    """تتبع وتسجيل تغييرات الحسابات الميدانية (منع التكرار)."""
    notification_key = f"{target_id}_{action}_{actor}"
    now = time.time()
    if notification_key in _last_notifications:
        if now - _last_notifications[notification_key] < _NOTIFICATION_COOLDOWN:
            return
    _last_notifications[notification_key] = now
    if len(_last_notifications) > 100:
        for key in list(_last_notifications.keys()):
            if now - _last_notifications[key] > 3600:
                del _last_notifications[key]


def handle_onboarding_callback(bot, call):
    """معالجة التفاعل مع أزرار طلبات الانضمام الجديدة."""
    from sheets.users_repo import set_user_role, set_ai_allowed
    from state import user_state

    data = call.data
    parts = data.rsplit("_", 1)
    if len(parts) < 2:
        return
    action, short_key = parts[0], parts[1]
    store = _approval_store.get(short_key)
    if not store:
        bot.answer_callback_query(call.id, "⚠️ انتهت صلاحية هذا الطلب.", show_alert=True)
        return

    requester_id = store["requester_id"]
    requester_name = store["requester_name"]

    if action == "approve_role_admin":
        set_user_role(requester_id, allowed=True, admin=True, owner=False)
        bot.answer_callback_query(call.id, "⭐ تمت ترقية المستخدم إلى أدمن.")
        try:
            bot.send_message(requester_id, "⭐ تمت ترقيتك وتفعيل حسابك كأدمن! مرحباً بك.")
        except Exception:
            pass
        try:
            bot.edit_message_text(f"⭐ *تمت الترقية إلى أدمن*\n👤 {requester_name} (`{requester_id}`)", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        except Exception:
            pass

    elif action == "approve_role_user":
        set_user_role(requester_id, allowed=True, admin=False, owner=False)
        bot.answer_callback_query(call.id, "👤 تم تفعيل حساب المستخدم.")
        try:
            bot.send_message(requester_id, bt("رسالة_موافقة", requester_id) or "✅ تمت الموافقة على طلبك وتفعيل حسابك!")
        except Exception:
            pass
        try:
            bot.edit_message_text(f"✅ *تم تفعيل الحساب كـ مستخدم*\n👤 {requester_name} (`{requester_id}`)", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        except Exception:
            pass

    elif action == "approve_rename":
        user_state[call.from_user.id] = {"step": "awaiting_rename_for_approval", "target_id": requester_id}
        bot.answer_callback_query(call.id, "✏️ أرسل الاسم الجديد للمستخدم الآن:")
        bot.send_message(call.message.chat.id, f"✏️ أرسل الاسم الجديد للمستخدم `{requester_name}` (`{requester_id}`):", parse_mode="Markdown")

    elif action == "approve_ai_on":
        set_ai_allowed(requester_id, True)
        bot.answer_callback_query(call.id, "🤖 تم تفعيل المساعد الذكي للمستخدم.")
        try:
            bot.send_message(requester_id, bt("رسالة_ai_تفعيل", requester_id) or "🤖 تم تفعيل المساعد الذكي لحسابك!")
        except Exception:
            pass

    elif action == "reject":
        set_user_role(requester_id, allowed=False, admin=False, owner=False)
        bot.answer_callback_query(call.id, "❌ تم رفض الطلب.")
        try:
            bot.send_message(requester_id, bt("رسالة_رفض_طلب", requester_id) or "❌ نعتذر، تم رفض طلب التفعيل.")
        except Exception:
            pass
        try:
            bot.edit_message_text(f"❌ *تم رفض الطلب*\n👤 {requester_name} (`{requester_id}`)", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        except Exception:
            pass

