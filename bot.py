"""
bot.py — نقطة الدخول الرئيسية لبوت الدراسة الجامعة.
"""

import logging
import threading
import time

import telebot

import config
from ai.assistant import ask_ai
from ai.providers import AI_PROVIDERS, load_ai_providers
from ai.voice import transcribe_voice
from features.admin_commands import try_execute_admin_command
from features.assignments import get_tasks_for_subject, save_task, delete_task
from features.booklets import get_booklets_for_subject, save_booklet, delete_booklet
from features.broadcast import do_broadcast, notify_auto_publish
from features.browsing import (
    get_subjects,
    get_lecture_subjects,
    get_rooms,
    get_subject_doctor,
)
from features.exams import get_exams_for_subject, save_exam, delete_exam
from features.help_materials import send_help_materials
from features.lectures import (
    save_lecture,
    save_no_lecture,
    delete_lecture,
    date_has_lectures,
    check_lecture_conflict,
)
from features.onboarding import (
    _register_new_visitor,
    calc_secret_code,
    notify_owners_new_request,
    notify_owners_action,
)
from features.settings import (
    handle_settings_callback,
    handle_ai_permission_request,
    handle_ai_grant_deny,
)
from features.summaries import get_summaries_for_subject, save_summary, delete_summary
from features.upload_request import process_user_upload_request
from features.users_admin import (
    _smart_search_user,
    send_user_card,
    update_user_card_in_chat,
    format_all_users_message,
)
from files_io import send_files_with_text, _try_send_file
from http_server import start_internal_server
from keyboards.flow_kb import (
    dates_menu_kb,
    date_suggestions_menu,
    buildings_menu,
    rooms_menu_kb,
    lecture_time_menu,
    manage_users_menu,
    help_audience_menu,
    help_view_menu,
    lang_menu,
    upload_confirm_menu,
    add_data_menu,
    edit_data_menu,
    subjects_menu_kb,
    subject_options_menu,
    back_only_menu,
    back_step_menu,
)
from keyboards.main_kb import main_menu, settings_inline_menu
from logging_utils import log_info, log_error
from sheets.texts_repo import load_bot_texts, bt, BUTTON_TEXTS, _make_inline
from sheets.users_repo import (
    get_users,
    get_user_record,
    get_user_role,
    is_owner_id,
    find_user_row_by_id,
    set_user_role,
    set_ai_allowed,
    refresh_users_cache,
    users_sheet,
)
from state import user_state, pending_files, clear_user_state

logger = logging.getLogger("StudyTestBot")

bot = telebot.TeleBot(config.STUDY_BOT_TOKEN)


# ── مراقبة التغييرات الخارجية على شيت المستخدمين ──
_users_snapshot = {}


def _snapshot_users():
    try:
        if not users_sheet:
            return {}
        rows = users_sheet.get_all_values()[1:]
        snap = {}
        for row in rows:
            if len(row) > 2 and row[2].strip().lstrip("'").isdigit():
                uid = row[2].strip().lstrip("'")
                snap[uid] = {
                    "name": row[0].strip(),
                    "phone": row[1].strip() if len(row) > 1 else "",
                    "allowed": (row[3].strip().upper() if len(row) > 3 else "FALSE") == "TRUE",
                    "admin": (row[4].strip().upper() if len(row) > 4 else "FALSE") == "TRUE",
                    "owner": (row[5].strip().upper() if len(row) > 5 else "FALSE") == "TRUE",
                    "ai": (row[config.AI_ALLOWED_COL].strip().upper() if len(row) > config.AI_ALLOWED_COL else "FALSE") == "TRUE",
                }
        return snap
    except Exception:
        return {}


def _watch_sheet_loop():
    global _users_snapshot
    _users_snapshot = _snapshot_users()
    while True:
        time.sleep(30)
        try:
            new_snap = _snapshot_users()
            for uid_str, new in new_snap.items():
                old = _users_snapshot.get(uid_str)
                if not old:
                    continue
                uid = int(uid_str)
                name = new["name"]
                phone = new["phone"]
                if new["owner"] and not old["owner"]:
                    try:
                        bot.send_message(uid, "👑 تمت ترقيتك إلى مالك!")
                    except Exception:
                        pass
                    notify_owners_action(uid, name, phone, "الشيت", "set_owner")
                elif new["admin"] and not old["admin"]:
                    try:
                        bot.send_message(uid, "⭐ تمت ترقيتك إلى أدمن!")
                    except Exception:
                        pass
                    notify_owners_action(uid, name, phone, "الشيت", "set_admin")
                elif new["allowed"] and not old["allowed"]:
                    try:
                        bot.send_message(uid, bt("رسالة_موافقة", uid))
                    except Exception:
                        pass
                    notify_owners_action(uid, name, phone, "الشيت", "approve")
                elif new["ai"] and not old["ai"]:
                    try:
                        bot.send_message(uid, bt("رسالة_ai_تفعيل", uid))
                    except Exception:
                        pass
                    notify_owners_action(uid, name, phone, "الشيت", "ai_enabled")
                elif not new["ai"] and old["ai"]:
                    try:
                        bot.send_message(uid, bt("رسالة_ai_تعطيل", uid))
                    except Exception:
                        pass
                    notify_owners_action(uid, name, phone, "الشيت", "ai_disabled")
            _users_snapshot = new_snap
        except Exception:
            pass


# ── معالجات التفاعلات والرسائل ──

@bot.message_handler(commands=["start"])
def handle_start(message):
    uid = message.from_user.id
    threading.Thread(target=_register_new_visitor, args=(message,), daemon=True).start()

    role = get_user_role(uid)
    admin = role in ("admin", "owner")
    owner = role == "owner"

    clear_user_state(uid)

    if role in ("user", "admin", "owner"):
        text = f"مرحباً بك *{message.from_user.first_name}* في بوت الجامعة! 🎓"
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=main_menu(uid, admin, owner))
    else:
        # غير مسموح له
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(telebot.types.KeyboardButton("📞 مشاركة رقم الهواتف", request_contact=True))
        markup.add("❌ لا أريد مشاركة رقمي")
        bot.send_message(
            message.chat.id,
            "⚠️ نعتذر، ليس لديك صلاحية استخدام البوت حالياً.\nلمشاركة رقم هاتفك لطلب التفعيل اضغط الزر أدناه:",
            reply_markup=markup,
        )


@bot.message_handler(content_types=["contact"])
def handle_contact(message):
    uid = message.from_user.id
    phone = message.contact.phone_number if message.contact else ""
    name = message.from_user.full_name or "مستخدم"
    notify_owners_new_request(bot, uid, name, phone)
    bot.send_message(
        message.chat.id,
        "✅ تم إرسال طلب الانضمام إلى مالكي البوت. سيتم مراجعة طلبك وإبلاغك فور التفعيل.",
        reply_markup=telebot.types.ReplyKeyboardRemove(),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("settings_"))
def on_settings_callback(call):
    handle_settings_callback(bot, call)


@bot.callback_query_handler(func=lambda call: call.data in ("ai_request_yes", "ai_request_no"))
def on_ai_permission_request(call):
    handle_ai_permission_request(bot, call)


@bot.callback_query_handler(func=lambda call: call.data.startswith("grant_ai_") or call.data.startswith("deny_ai_"))
def on_ai_grant_deny(call):
    handle_ai_grant_deny(bot, call)


@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    uid = message.from_user.id
    text = (message.text or "").strip()
    role = get_user_role(uid)
    admin = role in ("admin", "owner")
    owner = role == "owner"

    if role not in ("user", "admin", "owner"):
        secret = calc_secret_code(uid)
        if text == secret:
            set_user_role(uid, allowed=True, admin=False, owner=False)
            bot.send_message(
                message.chat.id,
                "✅ تم التفعيل السريع بنجاح! مرحباً بك.",
                reply_markup=main_menu(uid, admin=False, owner=False),
            )
            return
        bot.send_message(message.chat.id, "⛔ ليس لديك صلاحية الوصول.")
        return

    # الأزرار الرئيسية
    if text == bt("زر_المواد", uid):
        clear_user_state(uid)
        subjects = get_subjects()
        if not subjects:
            bot.send_message(message.chat.id, "📭 لا توجد مواد مسجلة حالياً.")
            return
        m, _ = subjects_menu_kb(uid)
        user_state[uid] = {"step": "choose_subject"}
        bot.send_message(message.chat.id, "📚 اختر المادة المطلوبة:", reply_markup=m)
        return

    elif text == bt("زر_اعدادات", uid):
        clear_user_state(uid)
        bot.send_message(
            message.chat.id,
            "⚙️ *لوحة الإعدادات*",
            parse_mode="Markdown",
            reply_markup=settings_inline_menu(uid),
        )
        return

    elif text == bt("زر_عوده", uid) or text == "🔙 العودة":
        clear_user_state(uid)
        bot.send_message(message.chat.id, "القائمة الرئيسية:", reply_markup=main_menu(uid, admin, owner))
        return

    # فحص الأوامر الإدارية الحرة (الأدمن/المالك)
    if admin:
        executed, response = try_execute_admin_command(bot, text, uid, role, message.chat.id)
        if executed:
            if response:
                bot.send_message(message.chat.id, response, parse_mode="Markdown")
            return

    # المساعد الذكي (إذا لم يكن في حالة/تدفق فرعي وكان السويتش مفعلاً)
    rec = get_user_record(uid) or {}
    ai_switch = rec.get("ai_switch", False)
    if not user_state.get(uid) and ai_switch and AI_PROVIDERS:
        resp_text, meta = ask_ai(uid, text, role)
        if resp_text:
            bot.send_message(message.chat.id, resp_text, parse_mode="Markdown")
            return

    # النص افتراضياً
    bot.send_message(message.chat.id, "لم أفهم هذا الأمر. استخدم القائمة الرئيسية للوصول للميزات.", reply_markup=main_menu(uid, admin, owner))


def run():
    """بدء تشغيل البوت والخدمات الخلفية."""
    log_info("🚀 جاري بدء تشغيل البوت...")
    load_bot_texts()
    load_ai_providers()
    refresh_users_cache()
    start_internal_server()

    threading.Thread(target=_watch_sheet_loop, daemon=True).start()

    log_info("✅ البوت يعمل الآن وبانتظار الرسائل...")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    run()
