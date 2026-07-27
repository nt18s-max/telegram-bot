"""
settings.py — لوحة الإعدادات (سويتش مساعد نايف / النشر التلقائي / اللغة / طلب الصلاحية).
"""

import threading

import telebot

from ai.providers import AI_PROVIDERS
from keyboards.main_kb import settings_inline_menu
from logging_utils import log_error
from sheets.texts_repo import bt, _make_inline
from sheets.users_repo import (
    get_user_record,
    is_ai_allowed,
    set_user_ai_switch,
    set_user_auto_publish,
    save_user_lang,
    get_owner_ids,
    is_owner_id,
    set_ai_allowed,
)


def handle_settings_callback(bot, call):
    """معالج الضغط على خيارات لوحة الإعدادات."""
    uid = call.from_user.id
    rec = get_user_record(uid) or {}

    if call.data == "settings_toggle_ai":
        if not AI_PROVIDERS:
            bot.answer_callback_query(call.id, bt("رسالة_ai_غير_مفعل", uid))
            return
        if not is_ai_allowed(uid):
            bot.answer_callback_query(call.id)
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                _make_inline("زر_ai_request_yes", bt("زر_ai_request_yes", uid), "ai_request_yes"),
                _make_inline("زر_ai_request_no", bt("زر_ai_request_no", uid), "ai_request_no"),
            )
            bot.send_message(
                call.message.chat.id,
                "🤖 *مساعد نايف*\n\n"
                "ليس لديك صلاحية استخدام المساعد الذكي.\n\n"
                "هل تريد إرسال طلب للمالك لتفعيل الصلاحية؟",
                parse_mode="Markdown",
                reply_markup=markup,
            )
            return
        current = rec.get("ai_switch", False)
        new_state = not current
        threading.Thread(target=set_user_ai_switch, args=(uid, new_state), daemon=True).start()
        bot.answer_callback_query(call.id, "✅ تم تفعيل مساعد نايف" if new_state else "🔴 تم إيقاف مساعد نايف")

    elif call.data == "settings_toggle_publish":
        current = rec.get("auto_publish", False)
        new_state = not current
        if set_user_auto_publish(uid, new_state):
            bot.answer_callback_query(call.id, "✅ تم تفعيل النشر التلقائي" if new_state else "🔕 تم إيقاف النشر التلقائي")
        else:
            bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء تغيير الإعداد")
            return

    elif call.data == "settings_lang_ar":
        save_user_lang(uid, "ar")
        bot.answer_callback_query(call.id, "✅ تم التغيير إلى العربية")

    elif call.data == "settings_lang_en":
        save_user_lang(uid, "en")
        bot.answer_callback_query(call.id, "✅ Switched to English")

    try:
        bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=settings_inline_menu(uid)
        )
    except Exception:
        pass


def handle_ai_permission_request(bot, call):
    """إرسال/إلغاء طلب صلاحية المساعد الذكي من المالك."""
    uid = call.from_user.id
    rec = get_user_record(uid) or {}
    try:
        bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=telebot.types.InlineKeyboardMarkup()
        )
    except Exception:
        pass

    if call.data == "ai_request_yes":
        owners = get_owner_ids()
        name = rec.get("name", "مستخدم")
        phone = rec.get("phone", "")
        ph = f"\n📞 `{phone}`" if phone else ""
        req_text = f"🤖 *طلب صلاحية مساعد نايف*\n━━━━━━━━━━━━━━━━━━━━\n👤 {name}\n🆔 `{uid}`{ph}"
        markup_owners = telebot.types.InlineKeyboardMarkup()
        markup_owners.row(
            _make_inline("زر_grant_ai", bt("زر_grant_ai"), f"grant_ai_{uid}"),
            _make_inline("زر_deny_ai", bt("زر_deny_ai"), f"deny_ai_{uid}"),
        )
        sent_any = False
        for oid in owners:
            try:
                bot.send_message(oid, req_text, parse_mode="Markdown", reply_markup=markup_owners)
                sent_any = True
            except Exception:
                pass
        if sent_any:
            bot.answer_callback_query(call.id, "✅ تم إرسال الطلب")
            bot.send_message(call.message.chat.id, "⏳ تم إرسال طلبك للمالك. سيتم إخبارك عند الموافقة.")
        else:
            bot.answer_callback_query(call.id, "❌ فشل إرسال الطلب")
    else:
        bot.answer_callback_query(call.id, "تم الإلغاء")


def handle_ai_grant_deny(bot, call):
    """معالجة موافقة/رفض المالك لطلب تفعيل AI."""
    caller_id = call.from_user.id
    if not is_owner_id(caller_id):
        bot.answer_callback_query(call.id, "⛔ غير مسموح")
        return
    parts = call.data.split("_", 2)
    action = parts[0]  # grant or deny
    target_uid = int(parts[2])
    rec = get_user_record(target_uid) or {}
    name = rec.get("name", str(target_uid))

    try:
        bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=telebot.types.InlineKeyboardMarkup()
        )
    except Exception:
        pass

    if action == "grant":
        if set_ai_allowed(target_uid, True):
            bot.answer_callback_query(call.id, f"✅ تم منح الصلاحية لـ {name}")
            bot.send_message(call.message.chat.id, f"✅ تم منح صلاحية مساعد نايف لـ {name}")
            try:
                bot.send_message(
                    target_uid,
                    "🤖 *مساعد نايف*\n\n"
                    "✅ تمت الموافقة على طلبك!\n"
                    "اضغط ⚙️ الإعدادات في القائمة الرئيسية ثم فعّل سويتش مساعد نايف.",
                    parse_mode="Markdown",
                )
            except Exception:
                pass
        else:
            bot.answer_callback_query(call.id, "❌ حدث خطأ")
    else:
        bot.answer_callback_query(call.id, f"❌ تم رفض الطلب لـ {name}")
        bot.send_message(call.message.chat.id, f"❌ تم رفض طلب {name}")
        try:
            bot.send_message(target_uid, "🤖 *مساعد نايف*\n\n❌ نعتذر، تم رفض طلب تفعيل الصلاحية.")
        except Exception:
            pass
