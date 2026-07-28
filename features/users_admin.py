"""
users_admin.py — إدارة المستخدمين للمالكين (البحث، عرض بطاقة المستخدم، الترقية والتخفيض).
"""

import re
import telebot

import config
from logging_utils import log_error
from sheets.texts_repo import bt, _make_inline
from sheets.users_repo import users_sheet

_user_card_messages = {}


def _smart_search_user(query: str):
    """
    البحث الموحد الذكي في ID أو الهاتف أو الاسم.
    """
    q = query.strip().lstrip('#').replace('_', ' ').strip()
    clean = re.sub(r'[\s\-\+]', '', query.strip().lstrip('#'))
    found_uids = set()
    results = []

    try:
        if not users_sheet:
            return None, "all"
        rows = users_sheet.get_all_values()[1:]
    except Exception:
        return None, "all"

    for row in rows:
        if not row or not any(c.strip() for c in row if c):
            continue
        uid_str = row[config.COL_ID].strip().lstrip("'") if len(row) > config.COL_ID else ""
        if not uid_str.isdigit():
            continue
        name = row[config.COL_NAME].strip()
        phone = re.sub(r'[\s\-\+]', '', row[config.COL_PHONE].strip() if len(row) > config.COL_PHONE else "")

        matched = False

        # 1. ID
        if clean and uid_str == clean:
            matched = True

        # 2. الهاتف
        if clean and phone and (phone == clean or phone.endswith(clean) or clean.endswith(phone)):
            matched = True

        # 3. الاسم
        if q and len(q) >= 2:
            name_clean = name.replace("🆕️", "").replace("🆕", "").strip()
            if q.lower() in name_clean.lower():
                matched = True

        if matched and uid_str not in found_uids:
            found_uids.add(uid_str)
            results.append(row)

    if not results:
        return None, "all"
    if len(results) == 1:
        return results[0], "all"
    return results, "all"


def send_user_card(bot, chat_id: int, row: list, edit_existing: bool = False):
    """عرض أو تحديث بطاقة المستخدم الذكية."""
    name = row[0].strip() if row else ""
    uid_str = row[config.COL_ID].strip().lstrip("'") if len(row) > config.COL_ID else ""
    phone = row[config.COL_PHONE].strip() if len(row) > config.COL_PHONE else ""
    own = row[config.COL_OWNER].strip().upper() if len(row) > config.COL_OWNER else "FALSE"
    adm = row[config.COL_ADMIN].strip().upper() if len(row) > config.COL_ADMIN else "FALSE"
    allow_val = row[config.COL_ALLOWED].strip().upper() if len(row) > config.COL_ALLOWED else "FALSE"
    ai_val = row[config.AI_ALLOWED_COL].strip().upper() if len(row) > config.AI_ALLOWED_COL else "FALSE"

    if own == "TRUE":
        role_icon, role = "👑", "مالك"
    elif adm == "TRUE":
        role_icon, role = "⭐", "أدمن"
    elif allow_val == "TRUE":
        role_icon, role = "👤", "مستخدم"
    else:
        role_icon, role = "❌", "غير مصرح"

    ai_icon = "🤖" if ai_val == "TRUE" else "🚫"
    ai_status = "مفعل" if ai_val == "TRUE" else "معطل"
    ph_line = f"\n📞 [{phone}](tel:{phone})" if phone else ""

    uid_link = f"[{uid_str}](tg://user?id={uid_str})"
    text = f"{role_icon} *{name}*\n🆔 {uid_link}{ph_line}\n{ai_icon} AI: {ai_status}\n{'─' * 23}"

    markup = telebot.types.InlineKeyboardMarkup(row_width=2)

    if adm == "TRUE" and own != "TRUE":
        admin_btn_text = "⭐ أدمن ← 🔒 إقفال"
        user_btn_text = "👤 تخفيض لمستخدم"
    elif allow_val == "TRUE" and adm != "TRUE" and own != "TRUE":
        admin_btn_text = "⭐ ترقية لأدمن"
        user_btn_text = "👤 مستخدم ← ⛔ إلغاء"
    elif own == "TRUE":
        admin_btn_text = "⭐ تخفيض لأدمن"
        user_btn_text = "👤 تخفيض لمستخدم"
    else:
        admin_btn_text = "⭐ ترقية لأدمن"
        user_btn_text = "👤 منح صلاحية"

    markup.row(
        _make_inline("زر_role_admin", admin_btn_text, f"role_admin_{uid_str}"),
        _make_inline("زر_role_user", user_btn_text, f"role_user_{uid_str}"),
    )

    ai_key = "زر_ai_off" if ai_val == "TRUE" else "زر_ai_on"
    markup.row(
        _make_inline(ai_key, bt(ai_key), f"ai_{'off' if ai_val == 'TRUE' else 'on'}_{uid_str}"),
        _make_inline("زر_rename_user", bt("زر_rename_user"), f"rename_{uid_str}"),
    )

    if edit_existing and int(uid_str) in _user_card_messages:
        old = _user_card_messages[int(uid_str)]
        if old["chat_id"] == chat_id:
            try:
                bot.edit_message_text(text, old["chat_id"], old["message_id"], parse_mode="Markdown", reply_markup=markup)
                return
            except Exception:
                pass

    msg = bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)
    _user_card_messages[int(uid_str)] = {"chat_id": chat_id, "message_id": msg.message_id}


def update_user_card_in_chat(bot, search_id):
    """تحديث تلقائي للبطاقة المفتوحة عند تغيير رتبة مستخدم."""
    try:
        rows = users_sheet.get_all_values()
        sid = str(search_id).strip()
        target_row = None
        for r in rows:
            if len(r) > config.COL_ID and r[config.COL_ID].strip().lstrip("'") == sid:
                target_row = r
                break
        if not target_row:
            return
        uid_int = int(sid)
        if uid_int in _user_card_messages:
            cid = _user_card_messages[uid_int]["chat_id"]
            send_user_card(bot, cid, target_row, edit_existing=True)
    except Exception as e:
        log_error(f"update_user_card_in_chat: {e}")


def format_all_users_message() -> str:
    """تنسيق قائمة جميع المستخدمين (نشطين وزوار جدد)."""
    try:
        if not users_sheet:
            return "❌ تعذر الوصول لصفحة المستخدمين."
        rows = users_sheet.get_all_values()
        active_lines = ["👥 *المستخدمون النشطون:*\n" + "━" * 15]
        new_lines = ["\n🆕️ *زوار جدد (لم تُمنح لهم صلاحية بعد):*\n" + "━" * 15]
        has_active = has_new = False

        for row in rows[1:]:
            if len(row) < 3:
                continue
            uid_str = row[config.COL_ID].strip().lstrip("'")
            if not uid_str.isdigit():
                continue
            name = row[config.COL_NAME].strip() or "مجهول"
            phone = row[config.COL_PHONE].strip() if len(row) > config.COL_PHONE else ""
            allowed = (row[config.COL_ALLOWED].strip().upper() if len(row) > config.COL_ALLOWED else "FALSE") == "TRUE"
            admin = (row[config.COL_ADMIN].strip().upper() if len(row) > config.COL_ADMIN else "FALSE") == "TRUE"
            owner = (row[config.COL_OWNER].strip().upper() if len(row) > config.COL_OWNER else "FALSE") == "TRUE"
            ai = (row[config.AI_ALLOWED_COL].strip().upper() if len(row) > config.AI_ALLOWED_COL else "FALSE") == "TRUE"
            is_new = name.startswith("🆕️") and not allowed and not admin and not owner

            uid_link = f"[{uid_str}](tg://user?id={uid_str})"
            phone_part = f" | 📞 `{phone}`" if phone else ""
            ai_part = " | 🤖" if ai else ""

            if is_new:
                has_new = True
                display_name = name.replace("🆕️ ", "").replace("🆕 ", "").strip()
                new_lines.append(f"🆕️ `{display_name}`\n🆔 {uid_link}{phone_part}\n" + "─" * 15)
            else:
                has_active = True
                if owner:
                    icon = "👑"
                elif admin:
                    icon = "⭐"
                elif allowed:
                    icon = "👤"
                else:
                    icon = "❌"
                active_lines.append(f"{icon}{ai_part} `{name}`\n🆔 {uid_link}{phone_part}\n" + "─" * 15)

        result = []
        if has_active:
            result.extend(active_lines)
        if has_new:
            result.extend(new_lines)
        if not result:
            return "❌ لا يوجد مستخدمين مسجلين."
        return "\n".join(result)
    except Exception as e:
        log_error(f"format_all_users_message: {e}")
        return "❌ حدث خطأ في قراءة بيانات المستخدمين."


def handle_users_admin_callback(bot, call):
    """معالجة التفاعل مع أزرار بطاقة المستخدم (ترقية، تخفيض، تفعيل AI، تغيير الاسم)."""
    from sheets.users_repo import get_user_record, set_user_role, set_ai_allowed
    from state import user_state

    data = call.data
    parts = data.rsplit("_", 1)
    if len(parts) < 2:
        return
    action, target_uid_str = parts[0], parts[1]
    if not target_uid_str.isdigit():
        return
    target_uid = int(target_uid_str)
    rec = get_user_record(target_uid) or {}
    name = rec.get("name", str(target_uid))

    if action == "role_admin":
        is_admin = rec.get("admin", False)
        new_admin = not is_admin
        set_user_role(target_uid, allowed=True, admin=new_admin, owner=False)
        status_str = "أدمن" if new_admin else "مستخدم عادي"
        bot.answer_callback_query(call.id, f"✅ تم تغيير رتبة {name} إلى {status_str}")
        update_user_card_in_chat(bot, target_uid)

    elif action == "role_user":
        is_allowed = rec.get("allowed", False)
        new_allowed = not is_allowed
        set_user_role(target_uid, allowed=new_allowed, admin=False, owner=False)
        status_str = "مصرح له" if new_allowed else "غير مصرح له"
        bot.answer_callback_query(call.id, f"✅ تم تغيير حالة {name} إلى {status_str}")
        update_user_card_in_chat(bot, target_uid)

    elif action in ("ai_on", "ai_off"):
        enable = (action == "ai_on")
        set_ai_allowed(target_uid, enable)
        status_str = "مفعل" if enable else "معطل"
        bot.answer_callback_query(call.id, f"🤖 تم جعل AI {status_str} لـ {name}")
        update_user_card_in_chat(bot, target_uid)

    elif action == "rename":
        user_state[call.from_user.id] = {"step": "awaiting_user_card_rename", "target_id": target_uid}
        bot.answer_callback_query(call.id, "✏️ أرسل الاسم الجديد:")
        bot.send_message(call.message.chat.id, f"✏️ أرسل الاسم الجديد للمستخدم `{name}` (`{target_uid}`):", parse_mode="Markdown")

