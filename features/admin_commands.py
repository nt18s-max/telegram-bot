"""
admin_commands.py — معالجة الأوامر النصية الإدارية الحرة (محددة بـ 3 أنماط فقط حسب القرار 4.5).
"""

import re

from features.onboarding import notify_owners_action
from features.users_admin import update_user_card_in_chat
from logging_utils import log_error
from sheets.users_repo import (
    get_user_record,
    set_ai_allowed,
    set_user_role,
    get_all_registered_uids,
)


def try_execute_admin_command(bot, text: str, uid: int, user_role: str, chat_id: int):
    """
    يفحص ويفسّر الأوامر النصية الإدارية الحرة.
    ملاحظة (القرار 4.5): تم تقليص الأوامر النصية إلى 3 أنماط فقط (إرسال إشعار، تفعيل/تعطيل AI، تغيير الرتبة).
    """
    if user_role not in ("admin", "owner"):
        return False, None

    text = text.strip()

    # 1. إرسال إشعار (لمستخدم محدد بالـ ID أو للجميع)
    pattern_broadcast_user = r'(?:أرسل إشعار للمستخدم|بلغ|أرسل إشعار لـ?)\s*(\d+)\s*(?:(?:يقول له|النص:?)\s*(.+))?'
    m = re.search(pattern_broadcast_user, text, re.IGNORECASE)
    if m:
        target_uid = int(m.group(1))
        broadcast_text = m.group(2).strip() if m.group(2) else ""
        if not broadcast_text:
            return True, "❌ يجب إدخال نص الإشعار. مثال: بلغ المستخدم 123456789 يقول له مرحباً"
        rec = get_user_record(target_uid)
        if not rec:
            return True, f"⚠️ لم أجد مستخدم بالـ ID {target_uid}"
        try:
            bot.send_message(target_uid, f"📢 *إشعار:*\n\n{broadcast_text}", parse_mode="Markdown")
            return True, f"✅ تم إرسال الإشعار للمستخدم {target_uid}"
        except Exception:
            return True, f"❌ فشل إرسال الإشعار للمستخدم {target_uid}"

    pattern_broadcast_all = r'(?:أرسل إشعار للجميع|بلغ الجميع|أعلن)\s*(.+)'
    m = re.search(pattern_broadcast_all, text, re.IGNORECASE)
    if m:
        broadcast_text = m.group(1).strip()
        if broadcast_text:
            uids = get_all_registered_uids()
            if not uids:
                return True, "⚠️ لا يوجد مستخدمون لإرسال الإشعار لهم."
            success = 0
            fail = 0
            for user_id in uids:
                try:
                    bot.send_message(user_id, f"📢 *إشعار:*\n\n{broadcast_text}", parse_mode="Markdown")
                    success += 1
                except Exception:
                    fail += 1
            return True, f"✅ تم إرسال الإشعار!\n✅ {success} | ❌ {fail}"
        else:
            return True, "❌ يجب إدخال نص الإشعار."

    # 2. تغيير رتبة مستخدم (اجعل [ID] أدمن/مستخدم) — للمالك فقط
    pattern_change_role = r'(?:اجعل|حول|غير)\s*(?:المستخدم)?\s*(\d+)\s*(أدمن|مستخدم)'
    m = re.search(pattern_change_role, text, re.IGNORECASE)
    if m:
        if user_role != "owner":
            return True, "⛔ هذا الأمر يتطلب صلاحية المالك."
        target_uid = int(m.group(1))
        target_role = m.group(2).strip()
        try:
            rec = get_user_record(target_uid)
            if not rec:
                return True, f"❌ لم أجد المستخدم {target_uid}"

            name = rec.get("name", str(target_uid))
            phone = rec.get("phone", "")

            if target_role == "أدمن":
                ok = set_user_role(target_uid, allowed=True, admin=True, owner=False)
                role_name = "أدمن"
            else:
                ok = set_user_role(target_uid, allowed=True, admin=False, owner=False)
                role_name = "مستخدم"

            if ok:
                notify_owners_action(target_uid, name, phone, f"أمر من {uid}", f"set_{role_name}")
                try:
                    bot.send_message(target_uid, f"✅ تم تغيير رتبتك إلى {role_name}")
                except Exception:
                    pass
                update_user_card_in_chat(bot, target_uid)
                return True, f"✅ تم تغيير رتبة المستخدم {name} إلى {role_name}"
            return True, "❌ حدث خطأ أثناء تغيير الرتبة"
        except Exception as e:
            log_error(f"change_role: {e}")
            return True, "❌ حدث خطأ أثناء تغيير الرتبة"

    # 3. تفعيل/تعطيل AI لمستخدم (فعّل/عطّل AI للمستخدم [ID]) — للمالك فقط
    pattern_toggle_ai = r'(?:فعّل|عطّل|تفعيل|تعطيل)\s*AI\s*(?:للمستخدم)?\s*(\d+)'
    m = re.search(pattern_toggle_ai, text, re.IGNORECASE)
    if m:
        if user_role != "owner":
            return True, "⛔ هذا الأمر يتطلب صلاحية المالك."
        target_uid = int(m.group(1))
        is_enable = "فعّل" in text or "تفعيل" in text
        rec = get_user_record(target_uid)
        name = rec.get("name", str(target_uid)) if rec else str(target_uid)

        if set_ai_allowed(target_uid, is_enable):
            status = "مفعل" if is_enable else "معطل"
            try:
                msg = f"🤖 *مساعد نايف*\n\nتم {'تفعيل' if is_enable else 'تعطيل'} صلاحية المساعد الذكي لك."
                bot.send_message(target_uid, msg, parse_mode="Markdown")
            except Exception:
                pass
            notify_owners_action(target_uid, name, "", f"أمر من {uid}", "ai_enabled" if is_enable else "ai_disabled")
            update_user_card_in_chat(bot, target_uid)
            return True, f"✅ تم {status} AI للمستخدم {name} (ID: {target_uid})"
        else:
            return True, f"❌ فشل تغيير صلاحية AI للمستخدم {target_uid}"

    return False, None
