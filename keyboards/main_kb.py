import telebot

from sheets.texts_repo import bt, _make_btn, _make_inline
from sheets.users_repo import get_user_record


def main_menu(uid, admin=False, owner=False):
    m = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    if admin or owner:
        m.row(_make_btn("زر_المواد", uid), _make_btn("زر_الجدول", uid))
        m.row(_make_btn("زر_الملخصات", uid), _make_btn("زر_التكاليف", uid))
        m.row(_make_btn("زر_نماذج_الاختبارات", uid), _make_btn("زر_الملازم", uid))
        m.row(_make_btn("زر_اضافة", uid), _make_btn("زر_تعديل", uid))
        m.row(_make_btn("زر_اشعار", uid))
        if owner:
            m.add(_make_btn("زر_المستخدمين", uid))
    else:
        m.row(_make_btn("زر_المواد", uid), _make_btn("زر_الجدول", uid))
        m.row(_make_btn("زر_الملخصات", uid), _make_btn("زر_التكاليف", uid))
        m.row(_make_btn("زر_نماذج_الاختبارات", uid), _make_btn("زر_الملازم", uid))
        m.row(_make_btn("زر_طلب_رفع", uid))

    m.row(_make_btn("زر_اعدادات", uid))
    return m


def settings_inline_menu(uid):
    from ai.providers import AI_PROVIDERS

    rec = get_user_record(uid) or {}
    ai_enabled = rec.get("ai_switch", False)
    auto_publish = rec.get("auto_publish", False)
    cur_lang = rec.get("lang", "ar")

    m = telebot.types.InlineKeyboardMarkup()
    if AI_PROVIDERS:
        ai_key = "زر_مساعد_نايف_تفعيل" if ai_enabled else "زر_مساعد_نايف_تعطيل"
        m.row(_make_inline(ai_key, bt(ai_key, uid), "settings_toggle_ai"))

    pub_key = "زر_نشر_تلقائي_تفعيل" if auto_publish else "زر_نشر_تلقائي_تعطيل"
    m.row(_make_inline(pub_key, bt(pub_key, uid), "settings_toggle_publish"))

    lbl_ar = "🇾🇪 العربية ✅" if cur_lang == "ar" else "🇾🇪 العربية"
    lbl_en = "🇬🇧 English ✅" if cur_lang == "en" else "🇬🇧 English"
    m.row(
        telebot.types.InlineKeyboardButton(lbl_ar, callback_data="settings_lang_ar"),
        telebot.types.InlineKeyboardButton(lbl_en, callback_data="settings_lang_en"),
    )
    return m
