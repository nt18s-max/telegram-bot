from datetime import datetime, timedelta

import telebot

import config
from sheets.texts_repo import bt, _make_btn


def back_only_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add(_make_btn("زر_عوده", uid))
    return m


def back_step_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row("↩️ رجوع خطوة", _make_btn("زر_عوده", uid))
    return m


def back_skip_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row("⏭️ تخطي", _make_btn("زر_عوده", uid))
    return m


def back_with_noexist(uid, show_noexist=True):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    if show_noexist:
        m.add("لا يوجد", _make_btn("زر_عوده", uid))
    else:
        m.add(_make_btn("زر_عوده", uid))
    return m


def subjects_menu_kb(uid):
    from features.browsing import get_subjects
    subjects = get_subjects()
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for s in subjects:
        m.add(s)
    m.add(_make_btn("زر_عوده", uid))
    return m, subjects


def lecture_subjects_kb(uid):
    from features.browsing import get_lecture_subjects
    subjects = get_lecture_subjects()
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for s in subjects:
        m.add(s)
    m.add(_make_btn("زر_عوده", uid))
    return m, subjects


def subjects_with_noexist_kb(uid):
    from features.browsing import get_subjects
    subjects = get_subjects()
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for s in subjects:
        m.add(s)
    m.add(_make_btn("زر_عوده", uid))
    return m, subjects


def subject_options_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for k in ["خيار_الجدول", "خيار_التكاليف", "خيار_الملخص", "خيار_الملزمه", "خيار_نماذج_الاختبارات"]:
        m.add(_make_btn(k, uid))
    m.add(_make_btn("زر_عوده", uid))
    return m


def dates_menu_kb(dates, uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for d in dates:
        m.add(d)
    m.add(_make_btn("زر_عوده", uid))
    return m


def date_suggestions_menu(subject=None, for_lecture=False, for_alert=False, uid=None):
    from features.lectures import get_last_lectures_for_subject

    now = datetime.now(config.YEMEN_TZ)
    yesterday = (now - timedelta(days=1)).strftime("%d/%m/%Y")
    today = now.strftime("%d/%m/%Y")
    tmrw = (now + timedelta(days=1)).strftime("%d/%m/%Y")

    if for_lecture or for_alert:
        dates = [tmrw, today, yesterday]
    else:
        dates = [today, yesterday]
        if subject:
            try:
                for d in get_last_lectures_for_subject(subject, 3):
                    if d not in dates:
                        dates.append(d)
            except Exception:
                pass
        dates = dates[:4]

    m = telebot.types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    for d in dates:
        m.add(d)
    back = _make_btn("زر_عوده", uid) if uid else "🔙 العودة"
    m.add(back)
    return m


def file_type_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(_make_btn("زر_اضافة_تكليف", uid), _make_btn("زر_اضافة_ملخص", uid))
    m.add(_make_btn("زر_عوده", uid))
    return m


def add_data_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row(_make_btn("زر_اضافة_محاضره", uid), _make_btn("زر_رفع_تعليمات", uid))
    m.row(_make_btn("زر_اضافة_تكليف", uid), _make_btn("زر_اضافة_ملخص", uid))
    m.row(_make_btn("زر_اضافة_ملزمه", uid), _make_btn("زر_اضافة_نموذج", uid))
    m.add(_make_btn("زر_عوده", uid))
    return m


def edit_data_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row(_make_btn("زر_تعديل_محاضره", uid), _make_btn("زر_تعديل_تكليف", uid))
    m.row(_make_btn("زر_تعديل_ملخص", uid), _make_btn("زر_تعديل_ملزمه", uid))
    m.add(_make_btn("زر_تعديل_نموذج", uid))
    m.add(_make_btn("زر_عوده", uid))
    return m


def edit_action_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(_make_btn("زر_تعديل_زرار", uid), _make_btn("زر_حذف_زرار", uid))
    m.row("↩️ رجوع خطوة", _make_btn("زر_عوده", uid))
    return m


def buildings_menu(uid, show_noexist=True):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("🏛 القديم", "🏫 الاداب")
    if show_noexist:
        m.add("لا يوجد")
    m.row("↩️ رجوع خطوة", _make_btn("زر_عوده", uid))
    return m


def rooms_menu_kb(building, uid):
    from features.browsing import get_rooms
    rooms = get_rooms(building)
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for r in rooms:
        m.add(r)
    m.add(_make_btn("زر_عوده", uid))
    return m, rooms


def lecture_time_menu(uid, show_noexist=True):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("🕐 08:00 - 10:00", "🕐 10:00 - 12:00")
    m.add("🕐 12:00 - 14:00", "⏰ توقيت آخر")
    if show_noexist:
        m.add("لا يوجد")
    m.row("↩️ رجوع خطوة", _make_btn("زر_عوده", uid))
    return m


def manage_users_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row("🔍 بحث عن مستخدم", "📋 آخر 3 مستخدمين")
    m.row("📋 عرض جميع المستخدمين", "🔙 العودة")
    return m


def help_audience_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("👤 للمستخدمين", "👑 للأدمن")
    m.add(_make_btn("زر_عوده", uid))
    return m


def help_view_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("👤 تعليمات المستخدم", "👑 تعليمات الأدمن")
    m.add(_make_btn("زر_عوده", uid))
    return m


def lang_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("🇾🇪 العربية", "🇬🇧 English")
    return m


def upload_confirm_menu(uid):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.row("✅ إرسال", _make_btn("زر_عوده", uid))
    return m
