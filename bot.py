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
from features.assignments import (
    get_tasks_for_subject,
    save_task,
    delete_task,
    replace_task_content,
    get_subjects_with_tasks,
)
from features.booklets import (
    get_booklets_for_subject,
    save_booklet,
    delete_booklet,
    replace_booklet_content,
    get_subjects_with_booklets,
)
from features.broadcast import do_broadcast, notify_auto_publish
from features.browsing import (
    get_subjects,
    get_lecture_subjects,
    get_rooms,
    get_subject_doctor,
)
from features.exams import (
    get_exams_for_subject,
    save_exam,
    delete_exam,
    replace_exam_content,
)
from features.help_materials import send_help_materials, save_help_material
from features.lectures import (
    save_lecture,
    save_no_lecture,
    delete_lecture,
    date_has_lectures,
    check_lecture_conflict,
    save_lecture_time,
)
from features.onboarding import (
    _register_new_visitor,
    calc_secret_code,
    notify_owners_new_request,
    notify_owners_action,
    handle_onboarding_callback,
)
from features.settings import (
    handle_settings_callback,
    handle_ai_permission_request,
    handle_ai_grant_deny,
)
from features.summaries import (
    get_summaries_for_subject,
    save_summary,
    delete_summary,
    replace_summary_content,
    get_subjects_with_summaries,
    get_known_students,
)
from features.upload_request import process_user_upload_request, handle_upload_request_callback
from features.users_admin import (
    _smart_search_user,
    send_user_card,
    update_user_card_in_chat,
    format_all_users_message,
    handle_users_admin_callback,
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

    text_parts = (message.text or "").split()
    if len(text_parts) > 1:
        param = text_parts[1].strip()
        if param == "refresh" and owner:
            refresh_users_cache()
            load_bot_texts()
            load_ai_providers()
            from sheets.data_repo import refresh_data_cache
            for t in ["lectures", "assignments", "summaries", "booklets", "exams", "rooms"]:
                refresh_data_cache(t)
            bot.send_message(message.chat.id, "✅ تم تحديث كاش البيانات والنصوص والذكاء الاصطناعي بنجاح!")
            return
        elif param.startswith("show_user_") and (admin or owner):
            target_id_str = param.replace("show_user_", "")
            if target_id_str.isdigit():
                res, _ = _smart_search_user(target_id_str)
                if res and isinstance(res, list):
                    send_user_card(bot, message.chat.id, res[0])
                    return
                elif res and isinstance(res, dict):
                    send_user_card(bot, message.chat.id, res)
                    return

    if role in ("user", "admin", "owner"):
        text = f"مرحباً بك *{message.from_user.first_name}* في بوت الجامعة! 🎓"
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=main_menu(uid, admin, owner))
    else:
        # غير مسموح له — تحقق من تسجيل رقم الهاتف في شيت المستخدمين
        rows = users_sheet.get_all_values()[1:] if users_sheet else []
        phone_found = False
        user_phone = ""
        for row in rows:
            if len(row) > 2 and row[2].strip().lstrip("'") == str(uid):
                if len(row) > 1 and row[1].strip():
                    phone_found = True
                    user_phone = row[1].strip()
                break

        if phone_found:
            notify_owners_new_request(bot, uid, message.from_user.full_name or "مستخدم", user_phone)
            bot.send_message(
                message.chat.id,
                "⏳ طلب الانضمام الخاص بك قيد المراجعة لدى المالكين. سيتم إبلاغك فور التفعيل.",
                reply_markup=telebot.types.ReplyKeyboardRemove(),
            )
        else:
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(telebot.types.KeyboardButton("📞 مشاركة رقم الهاتف", request_contact=True))
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


@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_role_admin_", "approve_role_user_", "approve_rename_", "approve_ai_on_", "reject_")))
def on_onboarding_callback(call):
    handle_onboarding_callback(bot, call)


@bot.callback_query_handler(func=lambda call: call.data.startswith(("role_admin_", "role_user_", "ai_on_", "ai_off_", "rename_")))
def on_users_admin_callback(call):
    handle_users_admin_callback(bot, call)


@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_upload_", "reject_upload_")))
def on_upload_request_callback(call):
    handle_upload_request_callback(bot, call)


@bot.message_handler(content_types=["voice"])
def handle_voice_message(message):
    uid = message.from_user.id
    role = get_user_role(uid)
    if role not in ("user", "admin", "owner"):
        return

    rec = get_user_record(uid) or {}
    ai_switch = rec.get("ai_switch", False)
    ai_allowed = rec.get("ai_allowed", False)

    if not user_state.get(uid) and ai_switch and ai_allowed and AI_PROVIDERS:
        text = transcribe_voice(bot, message.voice.file_id, lang=rec.get("lang", "ar"))
        if text:
            resp_text, meta = ask_ai(uid, text, role)
            if resp_text:
                bot.send_message(message.chat.id, f"🎙️ *سؤالك الصوتي:* {text}\n\n{resp_text}", parse_mode="Markdown")


@bot.message_handler(content_types=["document", "photo", "video", "audio"])
def handle_media_messages(message):
    uid = message.from_user.id
    st = user_state.get(uid)
    if not st or not isinstance(st, dict):
        return

    fid = None
    file_type = "document"
    if message.document:
        fid = message.document.file_id
        file_type = "document"
    elif message.photo:
        fid = message.photo[-1].file_id
        file_type = "photo"
    elif message.video:
        fid = message.video.file_id
        file_type = "video"
    elif message.audio:
        fid = message.audio.file_id
        file_type = "audio"

    if not fid:
        return

    step = st.get("step")
    caption = message.caption or ""

    if uid not in pending_files:
        pending_files[uid] = []

    pending_files[uid].append({"file_id": fid, "file_type": file_type, "caption": caption})
    count = len(pending_files[uid])

    if step == "add_task_content":
        m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        m.row("💾 حفظ", "⚠️ تنبيه")
        m.add("↩️ رجوع خطوة")
        bot.send_message(message.chat.id, f"✅ تم استلام الملف ({count}). اضغط 💾 حفظ للإنهاء أو أرسل ملفات/نصوص أخرى:", reply_markup=m)

    elif step == "add_summary_files":
        m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        m.row("💾 حفظ", "↩️ رجوع خطوة")
        bot.send_message(message.chat.id, f"✅ تم استلام الملف ({count}). اضغط 💾 حفظ لاختيار اسم الطالب:", reply_markup=m)

    elif step == "add_booklet_file":
        m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        m.row("💾 حفظ", "💰 إضافة سعر")
        m.add("↩️ رجوع خطوة")
        bot.send_message(message.chat.id, "✅ تم استلام ملف الملزمة. اختر الحفظ أو إضافة سعر:", reply_markup=m)

    elif step == "add_exam_file":
        # [Decision 4.8 / [16]] Save button shows up after receiving exam file!
        m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        m.row("💾 حفظ", "↩️ رجوع خطوة")
        bot.send_message(message.chat.id, "✅ تم استلام ملف النموذج. اضغط 💾 حفظ لإتمام الإضافة:", reply_markup=m)

    elif step == "help_content":
        m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        m.row("💾 حفظ", "↩️ رجوع خطوة")
        bot.send_message(message.chat.id, f"✅ تم استلام الملف ({count}). اضغط 💾 حفظ للنشر:", reply_markup=m)

    elif step == "upload_req_content":
        m = upload_confirm_menu(uid)
        bot.send_message(message.chat.id, f"✅ تم إرفاق الملف ({count}). اضغط ✅ إرسال عند الانتهاء:", reply_markup=m)

    elif step == "broadcast_enter_content":
        m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        m.row("✅ إرسال", "🔙 العودة")
        bot.send_message(message.chat.id, f"✅ تم استلام الملف ({count}). اضغط ✅ إرسال لبث الإشعار:", reply_markup=m)

    elif step == "enter_replace_content":
        m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        m.row("💾 حفظ", "↩️ رجوع خطوة")
        bot.send_message(message.chat.id, f"✅ تم استلام المحتوى الجديد. اضغط 💾 حفظ للحفظ:", reply_markup=m)


def _show_subject_tasks(bot, chat_id, subject):
    tasks = get_tasks_for_subject(subject)
    if not tasks:
        bot.send_message(chat_id, f"📭 لا توجد تكاليف مسجلة لمادة *{subject}* حالياً.", parse_mode="Markdown")
        return
    for task in tasks:
        msg = f"📝 *تكليف: {task['name']}*\n📌 المادة: {subject}"
        if task.get("text"):
            msg += f"\n\n{task['text']}"
        if task.get("alert"):
            msg += f"\n\n⚠️ *تنبيه:* {task['alert']}"
        send_files_with_text(bot, chat_id, msg, task.get("file_ids", []))


def _show_subject_summaries(bot, chat_id, subject):
    items = get_summaries_for_subject(subject)
    if not items:
        bot.send_message(chat_id, f"📭 لا توجد ملخصات مسجلة لمادة *{subject}* حالياً.", parse_mode="Markdown")
        return
    for item in items:
        msg = f"📖 *ملخص: {item['label']}*\n📌 المادة: {subject}"
        if item.get("student"):
            msg += f"\n✍️ إعداد الطالب: {item['student']}"
        send_files_with_text(bot, chat_id, msg, item.get("file_ids", []))


def _show_subject_booklets(bot, chat_id, subject):
    items = get_booklets_for_subject(subject)
    if not items:
        bot.send_message(chat_id, f"📭 لا توجد ملازم مسجلة لمادة *{subject}* حالياً.", parse_mode="Markdown")
        return
    for b in items:
        msg = f"📋 *ملزمة: {b['name']}*\n📌 المادة: {subject}"
        if b.get("price"):
            msg += f"\n💰 السعر: {b['price']}"
        send_files_with_text(bot, chat_id, msg, b.get("file_ids", []))


def _show_subject_exams(bot, chat_id, subject):
    items = get_exams_for_subject(subject)
    if not items:
        bot.send_message(chat_id, f"📭 لا توجد نماذج اختبارات لمادة *{subject}* حالياً.", parse_mode="Markdown")
        return
    for ex in items:
        msg = f"🧾 *نموذج اختبار: {ex['name']}*\n📌 المادة: {subject}"
        send_files_with_text(bot, chat_id, msg, ex.get("file_ids", []))


def _show_subject_lectures(bot, chat_id, subject):
    from sheets.data_repo import get_tab_data
    from utils.parsing import safe_get
    lectures = []
    for r in get_tab_data("lectures"):
        if safe_get(r, 1) == subject:
            lectures.append({
                "date": safe_get(r, 0),
                "time": safe_get(r, 2),
                "room": safe_get(r, 3),
                "alert": safe_get(r, 4),
            })
    if not lectures:
        bot.send_message(chat_id, f"📭 لا توجد محاضرات مسجلة لمادة *{subject}* حالياً.", parse_mode="Markdown")
        return
    lines = [f"🕐 *جدول محاضرات مادة {subject}:*"]
    for l in lectures:
        t_str = f" 🕐 {l['time']}" if l.get('time') else ""
        r_str = f" 📍 {l['room']}" if l.get('room') else ""
        a_str = f"\n⚠️ {l['alert']}" if l.get('alert') else ""
        lines.append(f"📅 *{l['date']}*{t_str}{r_str}{a_str}")
    bot.send_message(chat_id, "\n\n".join(lines), parse_mode="Markdown")


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

    # ── الأزرار الرئيسية المباشرة ──

    if text == bt("زر_المواد", uid) or text in ("📚 المواد", "المواد"):
        clear_user_state(uid)
        subjects = get_subjects()
        if not subjects:
            bot.send_message(message.chat.id, "📭 لا توجد مواد مسجلة حالياً.")
            return
        m, _ = subjects_menu_kb(uid)
        user_state[uid] = {"step": "choose_subject"}
        bot.send_message(message.chat.id, "📚 اختر المادة المطلوبة:", reply_markup=m)
        return

    elif text == bt("زر_التكاليف", uid) or text in ("📝 التكاليف", "التكاليف"):
        clear_user_state(uid)
        m, subjects = subjects_menu_kb(uid)
        if not subjects:
            bot.send_message(message.chat.id, "📭 لا توجد مواد مسجلة حالياً.")
            return
        user_state[uid] = {"step": "choose_shortcut_subject", "target": "assignments"}
        bot.send_message(message.chat.id, "📝 اختر المادة لطلب تكاليفها:", reply_markup=m)
        return

    elif text == bt("زر_الجدول", uid) or text in ("🕐 أوقات المحاضرات", "الجدول"):
        clear_user_state(uid)
        m, subjects = subjects_menu_kb(uid)
        if not subjects:
            bot.send_message(message.chat.id, "📭 لا توجد مواد مسجلة حالياً.")
            return
        user_state[uid] = {"step": "choose_shortcut_subject", "target": "lectures"}
        bot.send_message(message.chat.id, "🕐 اختر المادة لعرض جدول محاضراتها:", reply_markup=m)
        return

    elif text == bt("زر_الملخصات", uid) or text in ("📖 الملخصات", "الملخصات"):
        clear_user_state(uid)
        m, subjects = subjects_menu_kb(uid)
        if not subjects:
            bot.send_message(message.chat.id, "📭 لا توجد مواد مسجلة حالياً.")
            return
        user_state[uid] = {"step": "choose_shortcut_subject", "target": "summaries"}
        bot.send_message(message.chat.id, "📖 اختر المادة لعرض ملخصاتها:", reply_markup=m)
        return

    elif text == bt("زر_الملازم", uid) or text in ("📋 الملازم", "الملازم"):
        clear_user_state(uid)
        m, subjects = subjects_menu_kb(uid)
        if not subjects:
            bot.send_message(message.chat.id, "📭 لا توجد مواد مسجلة حالياً.")
            return
        user_state[uid] = {"step": "choose_shortcut_subject", "target": "booklets"}
        bot.send_message(message.chat.id, "📋 اختر المادة لعرض ملازمها:", reply_markup=m)
        return

    elif text == bt("زر_نماذج_الاختبارات", uid) or text in ("🧾 نماذج الاختبارات", "نماذج الاختبارات"):
        clear_user_state(uid)
        m, subjects = subjects_menu_kb(uid)
        if not subjects:
            bot.send_message(message.chat.id, "📭 لا توجد مواد مسجلة حالياً.")
            return
        user_state[uid] = {"step": "choose_shortcut_subject", "target": "exams"}
        bot.send_message(message.chat.id, "🧾 اختر المادة لعرض نماذج اختباراتها:", reply_markup=m)
        return

    elif text == bt("زر_طلب_رفع", uid) or text in ("📤 طلب رفع ملف", "طلب رفع"):
        clear_user_state(uid)
        user_state[uid] = {"step": "upload_req_type"}
        markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.row("📝 تكليف", "📖 ملخص")
        markup.add("🔙 العودة")
        bot.send_message(message.chat.id, "📤 اختر نوع المحتوى المراد طلب رفعه:", reply_markup=markup)
        return

    elif text == bt("زر_اعدادات", uid) or text in ("⚙️ الإعدادات", "الإعدادات"):
        clear_user_state(uid)
        bot.send_message(
            message.chat.id,
            "⚙️ *لوحة الإعدادات*",
            parse_mode="Markdown",
            reply_markup=settings_inline_menu(uid),
        )
        return

    elif text == bt("زر_عوده", uid) or text in ("🔙 العودة", "↩️ رجوع خطوة"):
        clear_user_state(uid)
        bot.send_message(message.chat.id, "القائمة الرئيسية:", reply_markup=main_menu(uid, admin, owner))
        return

    # ── أزرار الأدمن والمالك ──

    elif (admin or owner) and (text == bt("زر_اضافة", uid) or text in ("➕ إضافة", "إضافة")):
        clear_user_state(uid)
        bot.send_message(message.chat.id, "➕ *قائمة إضافة البيانات:*\nاختر المحتوى المراد إضافته:", parse_mode="Markdown", reply_markup=add_data_menu(uid))
        return

    elif (admin or owner) and (text == bt("زر_تعديل", uid) or text in ("✏️ تعديل", "تعديل")):
        clear_user_state(uid)
        bot.send_message(message.chat.id, "✏️ *قائمة تعديل البيانات:*\nاختر المحتوى المراد تعديله أو حذفه:", parse_mode="Markdown", reply_markup=edit_data_menu(uid))
        return

    elif (admin or owner) and (text == bt("زر_اشعار", uid) or text in ("📢 إرسال إشعار", "إرسال إشعار")):
        clear_user_state(uid)
        user_state[uid] = {"step": "broadcast_enter_content", "text": "", "files": []}
        pending_files[uid] = []
        markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.row("✅ إرسال", "🔙 العودة")
        bot.send_message(message.chat.id, "📢 *إرسال إشعار عام*\n\nأرسل نص الإشعار و/أو ارفق الملفات الآن، ثم اضغط على زر ✅ إرسال:", parse_mode="Markdown", reply_markup=markup)
        return

    elif owner and (text == bt("زر_المستخدمين", uid) or text in ("👥 إدارة المستخدمين", "إدارة المستخدمين")):
        clear_user_state(uid)
        bot.send_message(message.chat.id, "👥 *لوحة إدارة المستخدمين*", parse_mode="Markdown", reply_markup=manage_users_menu(uid))
        return

    # ── التفاعل مع خطوات الحالات الفعّالة (user_state) ──

    st = user_state.get(uid)
    if isinstance(st, dict):
        step = st.get("step")

        # 1. التصفح العام
        if step == "choose_subject":
            subjects = get_subjects()
            if text in subjects:
                user_state[uid] = {"step": "subject_options", "subject": text}
                bot.send_message(
                    message.chat.id,
                    f"📚 مادة *{text}*\nاختر القسم الذي تريد عرضه:",
                    parse_mode="Markdown",
                    reply_markup=subject_options_menu(uid),
                )
                return

        elif step == "subject_options":
            subj = st.get("subject")
            if text in (bt("خيار_الجدول", uid), "🕐 أوقات المحاضرات", "أوقات المحاضرات"):
                _show_subject_lectures(bot, message.chat.id, subj)
                return
            elif text in (bt("خيار_التكاليف", uid), "📝 التكاليف", "التكاليف"):
                _show_subject_tasks(bot, message.chat.id, subj)
                return
            elif text in (bt("خيار_الملخص", uid), "📖 الملخصات", "الملخصات"):
                _show_subject_summaries(bot, message.chat.id, subj)
                return
            elif text in (bt("خيار_الملزمه", uid), "📋 الملازم", "الملازم"):
                _show_subject_booklets(bot, message.chat.id, subj)
                return
            elif text in (bt("خيار_نماذج_الاختبارات", uid), "🧾 نماذج الاختبارات", "نماذج الاختبارات"):
                _show_subject_exams(bot, message.chat.id, subj)
                return

        elif step == "choose_shortcut_subject":
            target = st.get("target")
            subjects = get_subjects()
            if text in subjects:
                if target == "lectures":
                    _show_subject_lectures(bot, message.chat.id, text)
                elif target == "assignments":
                    _show_subject_tasks(bot, message.chat.id, text)
                elif target == "summaries":
                    _show_subject_summaries(bot, message.chat.id, text)
                elif target == "booklets":
                    _show_subject_booklets(bot, message.chat.id, text)
                elif target == "exams":
                    _show_subject_exams(bot, message.chat.id, text)
                user_state[uid] = {"step": "subject_options", "subject": text}
                return

        # 2. طلب رفع ملف (مستخدم عادي)
        elif step == "upload_req_type":
            req_type = "assignment" if "تكليف" in text else "summary"
            user_state[uid] = {"step": "upload_req_subject", "req_type": req_type}
            m, _ = subjects_menu_kb(uid)
            bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=m)
            return

        elif step == "upload_req_subject":
            user_state[uid]["subject"] = text
            user_state[uid]["step"] = "upload_req_title"
            bot.send_message(message.chat.id, "📝 أرسل عنوان المحتوى (مثلاً: ملخص الفصل الأول):", reply_markup=back_only_menu(uid))
            return

        elif step == "upload_req_title":
            user_state[uid]["title"] = text
            user_state[uid]["step"] = "upload_req_content"
            pending_files[uid] = []
            bot.send_message(
                message.chat.id,
                "📜 أرسل تفاصيل الطلب و/أو الملفات، ثم اضغط على زر ✅ إرسال عند الانتهاء:",
                reply_markup=upload_confirm_menu(uid),
            )
            return

        elif step == "upload_req_content":
            if text == "✅ إرسال":
                req_type = st.get("req_type", "assignment")
                subject = st.get("subject", "")
                title = st.get("title", "")
                files = pending_files.get(uid, [])
                process_user_upload_request(bot, message.chat.id, uid, subject, req_type, title, text="", pending_files=files)
                clear_user_state(uid)
                pending_files.pop(uid, None)
                return

        # 3. إضافة محاضرة (أدمن/مالك)
        elif step == "add_lecture_date":
            user_state[uid]["date"] = text
            user_state[uid]["step"] = "add_lecture_building"
            bot.send_message(message.chat.id, "🏛 اختر المبنى:", reply_markup=buildings_menu(uid))
            return

        elif step == "add_lecture_building":
            user_state[uid]["building"] = text
            user_state[uid]["step"] = "add_lecture_room"
            m, _ = rooms_menu_kb(text, uid)
            bot.send_message(message.chat.id, "🏫 اختر القاعة:", reply_markup=m)
            return

        elif step == "add_lecture_room":
            user_state[uid]["room"] = text
            user_state[uid]["step"] = "add_lecture_subject"
            m, _ = subjects_menu_kb(uid)
            bot.send_message(message.chat.id, "📚 اختر المادة:", reply_markup=m)
            return

        elif step == "add_lecture_subject":
            user_state[uid]["subject"] = text
            user_state[uid]["step"] = "add_lecture_time"
            bot.send_message(message.chat.id, "🕐 اختر وقت المحاضرة أو أرسل توقيتاً حراً:", reply_markup=lecture_time_menu(uid))
            return

        elif step == "add_lecture_time":
            time_val = text.replace("🕐 ", "").strip()
            user_state[uid]["time_val"] = time_val
            conflict = check_lecture_conflict(st.get("date"), time_val)
            if conflict:
                bot.send_message(
                    message.chat.id,
                    f"⚠️ *تنبيه تعارض:* يوجد محاضرة مسجلة بالفعل بنفس الوقت:\n📌 {conflict['subject']} ({conflict['room']})\n\nهل تريد الاستبدال أو الاستمرار؟",
                    parse_mode="Markdown",
                )
            user_state[uid]["step"] = "add_lecture_alert"
            markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            markup.row("💾 حفظ", "⚠️ تنبيه")
            markup.add("↩️ رجوع خطوة")
            bot.send_message(message.chat.id, "خطوة اختيارية: هل تريد إضافة تنبيه للمحاضرة؟", reply_markup=markup)
            return

        elif step == "add_lecture_alert":
            if text == "⚠️ تنبيه":
                user_state[uid]["step"] = "add_lecture_enter_alert"
                bot.send_message(message.chat.id, "⚠️ أرسل نص التنبيه الآن:", reply_markup=back_only_menu(uid))
                return
            else:
                d, s, t, r = st.get("date"), st.get("subject"), st.get("time_val"), st.get("room")
                ok = save_lecture(d, s, t, r, alert="")
                if ok:
                    bot.send_message(message.chat.id, "✅ تم حفظ المحاضرة بنجاح!", reply_markup=main_menu(uid, admin, owner))
                else:
                    bot.send_message(message.chat.id, "❌ حدث خطأ أثناء حفظ المحاضرة.", reply_markup=main_menu(uid, admin, owner))
                clear_user_state(uid)
                return

        elif step == "add_lecture_enter_alert":
            d, s, t, r = st.get("date"), st.get("subject"), st.get("time_val"), st.get("room")
            ok = save_lecture(d, s, t, r, alert=text)
            if ok:
                bot.send_message(message.chat.id, "✅ تم حفظ المحاضرة مع التنبيه بنجاح!", reply_markup=main_menu(uid, admin, owner))
            else:
                bot.send_message(message.chat.id, "❌ حدث خطأ أثناء حفظ المحاضرة.", reply_markup=main_menu(uid, admin, owner))
            clear_user_state(uid)
            return

        # 4. إضافة تكليف (أدمن/مالك)
        elif step == "add_task_subject":
            user_state[uid]["subject"] = text
            user_state[uid]["step"] = "add_task_name"
            bot.send_message(message.chat.id, "📝 أرسل اسم التكليف:", reply_markup=back_only_menu(uid))
            return

        elif step == "add_task_name":
            user_state[uid]["name"] = text
            user_state[uid]["step"] = "add_task_content"
            user_state[uid]["text_val"] = ""
            pending_files[uid] = []
            markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            markup.row("💾 حفظ", "⚠️ تنبيه")
            markup.add("↩️ رجوع خطوة")
            bot.send_message(message.chat.id, "📜 أرسل نص التكليف و/أو الملفات، ثم اضغط 💾 حفظ:", reply_markup=markup)
            return

        elif step == "add_task_content":
            if text == "⚠️ تنبيه":
                user_state[uid]["step"] = "add_task_alert"
                bot.send_message(message.chat.id, "⚠️ أرسل نص التنبيه للتكليف:", reply_markup=back_only_menu(uid))
                return
            elif text == "💾 حفظ":
                s, n = st.get("subject"), st.get("name")
                t_val = st.get("text_val", "")
                fids = [f["file_id"] for f in pending_files.get(uid, [])]
                ok = save_task(s, n, text_val=t_val, file_ids=fids, alert="")
                if ok:
                    bot.send_message(message.chat.id, "✅ تم حفظ التكليف بنجاح!", reply_markup=main_menu(uid, admin, owner))
                else:
                    bot.send_message(message.chat.id, "❌ حدث خطأ أثناء حفظ التكليف.", reply_markup=main_menu(uid, admin, owner))
                clear_user_state(uid)
                pending_files.pop(uid, None)
                return
            else:
                user_state[uid]["text_val"] = text
                m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                m.row("💾 حفظ", "⚠️ تنبيه")
                m.add("↩️ رجوع خطوة")
                bot.send_message(message.chat.id, "✅ تم استلام النص. اضغط 💾 حفظ أو أرفق ملفات أخرى:", reply_markup=m)
                return

        elif step == "add_task_alert":
            s, n = st.get("subject"), st.get("name")
            t_val = st.get("text_val", "")
            fids = [f["file_id"] for f in pending_files.get(uid, [])]
            ok = save_task(s, n, text_val=t_val, file_ids=fids, alert=text)
            if ok:
                bot.send_message(message.chat.id, "✅ تم حفظ التكليف والتنبيه بنجاح!", reply_markup=main_menu(uid, admin, owner))
            else:
                bot.send_message(message.chat.id, "❌ حدث خطأ أثناء حفظ التكليف.", reply_markup=main_menu(uid, admin, owner))
            clear_user_state(uid)
            pending_files.pop(uid, None)
            return

        # 5. إضافة ملخص (أدمن/مالك)
        elif step == "add_summary_subject":
            user_state[uid]["subject"] = text
            user_state[uid]["step"] = "add_summary_files"
            pending_files[uid] = []
            markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            markup.row("💾 حفظ", "↩️ رجوع خطوة")
            bot.send_message(message.chat.id, "📖 أرسل ملف/ملخصات، ثم اضغط 💾 حفظ:", reply_markup=markup)
            return

        elif step == "add_summary_files":
            if text == "💾 حفظ":
                user_state[uid]["step"] = "add_summary_student"
                students = get_known_students()
                markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                for stud in students:
                    markup.add(stud)
                markup.add("➕ إضافة طالب")
                markup.add("↩️ رجوع خطوة")
                bot.send_message(message.chat.id, "✍️ اختر اسم الطالب صانع الملخص:", reply_markup=markup)
                return

        elif step == "add_summary_student":
            if text == "➕ إضافة طالب":
                user_state[uid]["step"] = "add_summary_new_student"
                bot.send_message(message.chat.id, "✍️ أدخل اسم الطالب الجديد:", reply_markup=back_only_menu(uid))
                return
            else:
                s = st.get("subject")
                fids = [f["file_id"] for f in pending_files.get(uid, [])]
                label = f"ملخص {s}"
                ok = save_summary(s, text, label, file_ids=fids)
                if ok:
                    bot.send_message(message.chat.id, "✅ تم حفظ الملخص بنجاح!", reply_markup=main_menu(uid, admin, owner))
                else:
                    bot.send_message(message.chat.id, "❌ حدث خطأ أثناء حفظ الملخص.", reply_markup=main_menu(uid, admin, owner))
                clear_user_state(uid)
                pending_files.pop(uid, None)
                return

        elif step == "add_summary_new_student":
            s = st.get("subject")
            fids = [f["file_id"] for f in pending_files.get(uid, [])]
            label = f"ملخص {s}"
            ok = save_summary(s, text, label, file_ids=fids)
            if ok:
                bot.send_message(message.chat.id, f"✅ تم حفظ الملخص للطالب '{text}' بنجاح!", reply_markup=main_menu(uid, admin, owner))
            else:
                bot.send_message(message.chat.id, "❌ حدث خطأ أثناء حفظ الملخص.", reply_markup=main_menu(uid, admin, owner))
            clear_user_state(uid)
            pending_files.pop(uid, None)
            return

        # 6. إضافة ملزمة (أدمن/مالك)
        elif step == "add_booklet_subject":
            user_state[uid]["subject"] = text
            user_state[uid]["step"] = "add_booklet_name"
            bot.send_message(message.chat.id, "📋 أرسل اسم الملزمة:", reply_markup=back_only_menu(uid))
            return

        elif step == "add_booklet_name":
            user_state[uid]["name"] = text
            user_state[uid]["step"] = "add_booklet_file"
            pending_files[uid] = []
            markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            markup.row("💾 حفظ", "💰 إضافة سعر")
            markup.add("↩️ رجوع خطوة")
            bot.send_message(message.chat.id, "📋 أرسل ملف الملزمة الآن:", reply_markup=markup)
            return

        elif step == "add_booklet_file":
            if text == "💰 إضافة سعر":
                user_state[uid]["step"] = "add_booklet_price"
                bot.send_message(message.chat.id, "💰 أرسل سعر الملزمة (مثلاً: 1500 ريال):", reply_markup=back_only_menu(uid))
                return
            elif text == "💾 حفظ":
                s, n = st.get("subject"), st.get("name")
                fids = [f["file_id"] for f in pending_files.get(uid, [])]
                ok = save_booklet(s, n, file_ids=fids, price="")
                if ok:
                    bot.send_message(message.chat.id, "✅ تم حفظ الملزمة بنجاح!", reply_markup=main_menu(uid, admin, owner))
                else:
                    bot.send_message(message.chat.id, "❌ حدث خطأ أثناء حفظ الملزمة.", reply_markup=main_menu(uid, admin, owner))
                clear_user_state(uid)
                pending_files.pop(uid, None)
                return

        elif step == "add_booklet_price":
            s, n = st.get("subject"), st.get("name")
            fids = [f["file_id"] for f in pending_files.get(uid, [])]
            ok = save_booklet(s, n, file_ids=fids, price=text)
            if ok:
                bot.send_message(message.chat.id, "✅ تم حفظ الملزمة والسعر بنجاح!", reply_markup=main_menu(uid, admin, owner))
            else:
                bot.send_message(message.chat.id, "❌ حدث خطأ أثناء حفظ الملزمة.", reply_markup=main_menu(uid, admin, owner))
            clear_user_state(uid)
            pending_files.pop(uid, None)
            return

        # 7. إضافة نموذج اختبار (أدمن/مالك) — [Decision 4.8 / [16]]
        elif step == "add_exam_subject":
            user_state[uid]["subject"] = text
            user_state[uid]["step"] = "add_exam_name"
            bot.send_message(message.chat.id, "🧾 أرسل اسم أو نوع النموذج (مثلاً: فاينل 2025):", reply_markup=back_only_menu(uid))
            return

        elif step == "add_exam_name":
            user_state[uid]["name"] = text
            user_state[uid]["step"] = "add_exam_file"
            pending_files[uid] = []
            bot.send_message(message.chat.id, "🧾 أرسل ملف نموذج الاختبار الآن:", reply_markup=back_only_menu(uid))
            return

        elif step == "add_exam_file":
            if text == "💾 حفظ":
                s, n = st.get("subject"), st.get("name")
                fids = [f["file_id"] for f in pending_files.get(uid, [])]
                ok = save_exam(s, n, file_ids=fids)
                if ok:
                    bot.send_message(message.chat.id, "✅ تم حفظ نموذج الاختبار بنجاح!", reply_markup=main_menu(uid, admin, owner))
                else:
                    bot.send_message(message.chat.id, "❌ حدث خطأ أثناء حفظ نموذج الاختبار.", reply_markup=main_menu(uid, admin, owner))
                clear_user_state(uid)
                pending_files.pop(uid, None)
                return

        # 8. رفع التعليمات
        elif step == "help_audience":
            aud = "user" if "المستخدمين" in text else "admin"
            user_state[uid] = {"step": "help_content", "audience": aud}
            pending_files[uid] = []
            markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            markup.row("💾 حفظ", "↩️ رجوع خطوة")
            bot.send_message(message.chat.id, "📹 أرسل النص التوضيحي و/أو الملفات، ثم اضغط 💾 حفظ:", reply_markup=markup)
            return

        elif step == "help_content":
            if text == "💾 حفظ":
                aud = st.get("audience", "user")
                files = pending_files.get(uid, [])
                note = st.get("note", "")
                ok = save_help_material(files, audience=aud, note=note)
                if ok:
                    bot.send_message(message.chat.id, "✅ تم رفع التعليمات بنجاح!", reply_markup=main_menu(uid, admin, owner))
                else:
                    bot.send_message(message.chat.id, "❌ حدث خطأ أثناء حفظ التعليمات.", reply_markup=main_menu(uid, admin, owner))
                clear_user_state(uid)
                pending_files.pop(uid, None)
                return
            else:
                user_state[uid]["note"] = text
                m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                m.row("💾 حفظ", "↩️ رجوع خطوة")
                bot.send_message(message.chat.id, "✅ تم استلام النص. اضغط 💾 حفظ أو أرفق ملفات إضافية:", reply_markup=m)
                return

        # 9. بث الإشعارات (أدمن/مالك)
        elif step == "broadcast_enter_content":
            if text == "✅ إرسال":
                b_text = st.get("text", "")
                files = pending_files.get(uid, [])
                do_broadcast(bot, message.chat.id, uid, admin, owner, b_text, files)
                clear_user_state(uid)
                pending_files.pop(uid, None)
                return
            else:
                user_state[uid]["text"] = text
                markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                markup.row("✅ إرسال", "🔙 العودة")
                bot.send_message(message.chat.id, "✅ تم استلام النص. اضغط ✅ إرسال لبث الإشعار الآن:", reply_markup=markup)
                return

        # 10. إدارة المستخدمين والبحث (مالك)
        elif step == "search_user":
            res, _ = _smart_search_user(text)
            if not res:
                bot.send_message(message.chat.id, f"❌ لم يتم العثور على أي مستخدم يطابق '{text}'.", reply_markup=manage_users_menu(uid))
            elif isinstance(res, list):
                for row in res[:5]:
                    send_user_card(bot, message.chat.id, row)
            elif isinstance(res, dict):
                send_user_card(bot, message.chat.id, res)
            clear_user_state(uid)
            return

        elif step in ("awaiting_rename_for_approval", "awaiting_user_card_rename"):
            target_id = st.get("target_id")
            if target_id:
                i, row = find_user_row_by_id(target_id)
                if row:
                    users_sheet.update_cell(i, config.COL_NAME + 1, text)
                    refresh_users_cache()
                    bot.send_message(message.chat.id, f"✅ تم تغيير اسم المستخدم {target_id} إلى '{text}'.")
                    update_user_card_in_chat(bot, target_id)
                    clear_user_state(uid)
                    return

    # ── الأزرار الفرعية لقائمة ➕ إضافة و ✏️ تعديل و 👥 إدارة المستخدمين ──

    if (admin or owner) and text in (bt("زر_اضافة_محاضره", uid), "🕐 إضافة محاضرة"):
        clear_user_state(uid)
        user_state[uid] = {"step": "add_lecture_date"}
        bot.send_message(message.chat.id, "📅 اختر تاريخ المحاضرة أو أرسله يدوياً (dd/mm/yyyy):", reply_markup=date_suggestions_menu(uid=uid, for_lecture=True))
        return

    elif (admin or owner) and text in (bt("زر_اضافة_تكليف", uid), "📝 إضافة تكليف"):
        clear_user_state(uid)
        m, _ = subjects_menu_kb(uid)
        user_state[uid] = {"step": "add_task_subject"}
        bot.send_message(message.chat.id, "📌 اختر المادة لإضافة تكليف لها:", reply_markup=m)
        return

    elif (admin or owner) and text in (bt("زر_اضافة_ملخص", uid), "📖 إضافة ملخص"):
        clear_user_state(uid)
        m, _ = subjects_menu_kb(uid)
        user_state[uid] = {"step": "add_summary_subject"}
        bot.send_message(message.chat.id, "📌 اختر المادة لإضافة ملخص لها:", reply_markup=m)
        return

    elif (admin or owner) and text in (bt("زر_اضافة_ملزمه", uid), "📋 إضافة ملزمة"):
        clear_user_state(uid)
        m, _ = subjects_menu_kb(uid)
        user_state[uid] = {"step": "add_booklet_subject"}
        bot.send_message(message.chat.id, "📌 اختر المادة لإضافة ملزمة لها:", reply_markup=m)
        return

    elif (admin or owner) and text in (bt("زر_اضافة_نموذج", uid), "🧾 إضافة نموذج"):
        clear_user_state(uid)
        m, _ = subjects_menu_kb(uid)
        user_state[uid] = {"step": "add_exam_subject"}
        bot.send_message(message.chat.id, "📌 اختر المادة لإضافة نموذج اختبار لها:", reply_markup=m)
        return

    elif (admin or owner) and text in (bt("زر_رفع_تعليمات", uid), "📹 رفع التعليمات"):
        clear_user_state(uid)
        user_state[uid] = {"step": "help_audience"}
        bot.send_message(message.chat.id, "👥 اختر الفئة المستهدفة للتعليمات:", reply_markup=help_audience_menu(uid))
        return

    elif owner and text == "🔍 بحث عن مستخدم":
        user_state[uid] = {"step": "search_user"}
        bot.send_message(message.chat.id, "🔍 أرسل ID المستخدم، رقم الهاتف، أو اسمه للبحث:", reply_markup=back_only_menu(uid))
        return

    elif owner and text == "📋 عرض جميع المستخدمين":
        msg = format_all_users_message()
        bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=manage_users_menu(uid))
        return

    elif owner and text == "📋 آخر 3 مستخدمين":
        rows = users_sheet.get_all_values()[1:] if users_sheet else []
        valid_rows = [r for r in rows if len(r) > config.COL_ID and r[config.COL_ID].strip().lstrip("'").isdigit()]
        for r in valid_rows[-3:]:
            send_user_card(bot, message.chat.id, r)
        return

    # ── فحص الأوامر الإدارية النصية الحرة (الأدمن/المالك) ──
    if admin:
        executed, response = try_execute_admin_command(bot, text, uid, role, message.chat.id)
        if executed:
            if response:
                bot.send_message(message.chat.id, response, parse_mode="Markdown")
            return

    # ── المساعد الذكي ──
    rec = get_user_record(uid) or {}
    ai_switch = rec.get("ai_switch", False)
    ai_allowed = rec.get("ai_allowed", False)
    if not user_state.get(uid) and ai_switch and ai_allowed and AI_PROVIDERS:
        resp_text, meta = ask_ai(uid, text, role)
        if resp_text:
            bot.send_message(message.chat.id, resp_text, parse_mode="Markdown")
            return

    # ── النص الافتراضي ──
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
