import logging

import telebot

from sheets.connection import bot_texts_sheet, keyboard_buttons_sheet, inline_buttons_sheet
from sheets.users_repo import get_user_record

logger = logging.getLogger("StudyTestBot")

_VALID_STYLES = {"danger", "success", "primary"}

DEFAULT_BOT_TEXTS = {
    "رسالة_الترحيب_ar": "",
    "رسالة_الترحيب_en": "",
    "رسالة_الرفض_ar": "",
    "رسالة_الرفض_en": "",
    "رسالة_انتظار_ar": "",
    "رسالة_انتظار_en": "",
    "رسالة_موافقة_ar": "",
    "رسالة_موافقة_en": "",
    "رسالة_رفض_طلب_ar": "",
    "رسالة_رفض_طلب_en": "",
    "زر_المواد_ar": "",
    "زر_المواد_en": "",
    "زر_التكاليف_ar": "",
    "زر_التكاليف_en": "",
    "زر_الجدول_ar": "",
    "زر_الجدول_en": "",
    "زر_الملازم_ar": "",
    "زر_الملازم_en": "",
    "خيار_الملزمه_ar": "",
    "خيار_الملزمه_en": "",
    "زر_اضافة_ملزمه_ar": "",
    "زر_اضافة_ملزمه_en": "",
    "زر_تعديل_ملزمه_ar": "",
    "زر_تعديل_ملزمه_en": "",
    "زر_نماذج_الاختبارات_ar": "🧾 نماذج الاختبارات",
    "زر_نماذج_الاختبارات_en": "🧾 Exam Templates",
    "خيار_نماذج_الاختبارات_ar": "🧾 نماذج الاختبارات",
    "خيار_نماذج_الاختبارات_en": "🧾 Exam Templates",
    "زر_اضافة_نموذج_ar": "🧾 إضافة نموذج",
    "زر_اضافة_نموذج_en": "🧾 Add Exam Template",
    "زر_تعديل_نموذج_ar": "🧾 تعديل/حذف نموذج",
    "زر_تعديل_نموذج_en": "🧾 Edit/Delete Exam Template",
    "زر_تنبيه_اضافي_ar": "⚠️ تنبيه",
    "زر_تنبيه_اضافي_en": "⚠️ Alert",
    "زر_حفظ_ar": "✅ حفظ",
    "زر_حفظ_en": "✅ Save",
    "زر_اضافة_طالب_ar": "➕ إضافة طالب",
    "زر_اضافة_طالب_en": "➕ Add Student",
    "زر_استبدال_ar": "✅ استبدال",
    "زر_استبدال_en": "✅ Replace",
    "زر_الغاء_ar": "❌ إلغاء",
    "زر_الغاء_en": "❌ Cancel",
    "زر_اضافة_سعر_ملزمة_ar": "💰 إضافة سعر",
    "زر_اضافة_سعر_ملزمة_en": "💰 Add Price",
    "زر_الملخصات_ar": "",
    "زر_الملخصات_en": "",
    "زر_طلب_رفع_ar": "",
    "زر_طلب_رفع_en": "",
    "زر_رفع_تعليمات_ar": "",
    "زر_رفع_تعليمات_en": "",
    "زر_اعدادات_ar": "⚙️ الإعدادات",
    "زر_اعدادات_en": "⚙️ Settings",
    "زر_اشعار_ar": "",
    "زر_اشعار_en": "",
    "زر_اضافة_ar": "",
    "زر_اضافة_en": "",
    "زر_تعديل_ar": "",
    "زر_تعديل_en": "",
    "زر_المستخدمين_ar": "",
    "زر_المستخدمين_en": "",
    "زر_عوده_ar": "",
    "زر_عوده_en": "",
    "زر_تحديد_الكل_ar": "",
    "زر_تحديد_الكل_en": "",
    "زر_تم_التحديد_ar": "",
    "زر_تم_التحديد_en": "",
    "زر_اضافة_محاضره_ar": "",
    "زر_اضافة_محاضره_en": "",
    "زر_اضافة_تكليف_ar": "",
    "زر_اضافة_تكليف_en": "",
    "زر_اضافة_ملخص_ar": "",
    "زر_اضافة_ملخص_en": "",
    "زر_تعديل_محاضره_ar": "",
    "زر_تعديل_محاضره_en": "",
    "زر_تعديل_تكليف_ar": "",
    "زر_تعديل_تكليف_en": "",
    "زر_تعديل_ملخص_ar": "",
    "زر_تعديل_ملخص_en": "",
    "زر_تعديل_زرار_ar": "",
    "زر_تعديل_زرار_en": "",
    "زر_حذف_زرار_ar": "",
    "زر_حذف_زرار_en": "",
    "خيار_الجدول_ar": "",
    "خيار_الجدول_en": "",
    "خيار_التكاليف_ar": "",
    "خيار_التكاليف_en": "",
    "خيار_الملخص_ar": "",
    "خيار_الملخص_en": "",
    "رسالة_لا_بيانات_ar": "",
    "رسالة_لا_بيانات_en": "",
    "رسالة_خطأ_ar": "",
    "رسالة_خطأ_en": "",
    "رسالة_تم_الحفظ_ar": "",
    "رسالة_تم_الحفظ_en": "",
    "رسالة_تم_الحذف_ar": "",
    "رسالة_تم_الحذف_en": "",
    "رسالة_تم_التعديل_ar": "",
    "رسالة_تم_التعديل_en": "",
    "رسالة_ادمن_فقط_ar": "",
    "رسالة_ادمن_فقط_en": "",
    "رسالة_نايف_يكتب_ar": "",
    "رسالة_نايف_يكتب_en": "",
    "رسالة_ai_غير_مفعل_ar": "",
    "رسالة_ai_غير_مفعل_en": "",
    "رسالة_ai_غير_مسموح_ar": "",
    "رسالة_ai_غير_مسموح_en": "",
    "رسالة_ai_اشتراك_ar": "",
    "رسالة_ai_اشتراك_en": "",
    "رسالة_ai_فشل_ar": "",
    "رسالة_ai_فشل_en": "",
    "رسالة_ai_تم_الغاء_ar": "",
    "رسالة_ai_تم_الغاء_en": "",
    "رسالة_ai_تفعيل_ar": "",
    "رسالة_ai_تفعيل_en": "",
    "رسالة_ai_تعطيل_ar": "",
    "رسالة_ai_تعطيل_en": "",
    "رسالة_ai_ترحيب_ar": "",
    "رسالة_ai_ترحيب_en": "",
    "رسالة_تغيير_اللغة_ar": "",
    "رسالة_تغيير_اللغة_en": "",
    "رسالة_تم_تغيير_اللغة_ar": "",
    "رسالة_تم_تغيير_اللغة_en": "",
    "رسالة_طلب_جهة_اتصال_ar": "",
    "رسالة_طلب_جهة_اتصال_en": "",
    "رسالة_شكر_اتصال_ar": "",
    "رسالة_شكر_اتصال_en": "",
    "رسالة_غير_مسموح_ar": "",
    "رسالة_غير_مسموح_en": "",
    "زر_مشاركة_رقم_ar": "",
    "زر_مشاركة_رقم_en": "",
    "زر_لا_اريد_ar": "",
    "زر_لا_اريد_en": "",
    "رسالة_مشاركة_ar": "",
    "رسالة_مشاركة_en": "",
    "زر_مشاركة_كيبورد_ar": "",
    "زر_مشاركة_كيبورد_en": "",
    "زر_عوده_مشاركه_ar": "",
    "رسالة_كيبورد_مشاركة_ar": "",
    "رسالة_كيبورد_مشاركة_en": "",
    "زر_عوده_مشاركه_en": "",
    "رسالة_لا_اريد_ar": "",
    "رسالة_لا_اريد_en": "",
    "زر_بوت_تواصل_ar": "",
    "زر_بوت_تواصل_en": "",
    "رابط_بوت_تواصل_ar": "",
    "رابط_بوت_تواصل_en": "",
    "رسالة_جاري_الحذف_ar": "",
    "رسالة_جاري_الحذف_en": "",
    "زر_confirm_multi_ar": "✅ إرسال", "زر_confirm_multi_en": "✅ Send",
    "زر_edit_multi_ar": "✏️ تعديل", "زر_edit_multi_en": "✏️ Edit",
    "زر_reject_multi_ar": "❌ رفض", "زر_reject_multi_en": "❌ Reject",
    "زر_approve_admin_ar": "⭐ أدمن", "زر_approve_admin_en": "⭐ Admin",
    "زر_approve_user_ar": "👤 مستخدم", "زر_approve_user_en": "👤 User",
    "زر_approve_rename_ar": "✏️ تغيير الاسم", "زر_approve_rename_en": "✏️ Rename",
    "زر_approve_ai_ar": "🤖 تفعيل AI", "زر_approve_ai_en": "🤖 Enable AI",
    "زر_reject_ar": "❌ رفض", "زر_reject_en": "❌ Reject",
    "زر_file_approve_ar": "✅ قبول", "زر_file_approve_en": "✅ Approve",
    "زر_file_reject_ar": "❌ رفض", "زر_file_reject_en": "❌ Reject",
    "زر_ai_request_yes_ar": "✅ نعم", "زر_ai_request_yes_en": "✅ Yes",
    "زر_ai_request_no_ar": "❌ لا", "زر_ai_request_no_en": "❌ No",
    "زر_grant_ai_ar": "✅ منح الصلاحية", "زر_grant_ai_en": "✅ Grant Access",
    "زر_deny_ai_ar": "❌ رفض", "زر_deny_ai_en": "❌ Reject",
    "زر_مساعد_نايف_تفعيل_ar": "🟢 🤖 مساعد نايف", "زر_مساعد_نايف_تفعيل_en": "🟢 🤖 Naif Assistant",
    "زر_مساعد_نايف_تعطيل_ar": "🔴 🤖 مساعد نايف", "زر_مساعد_نايف_تعطيل_en": "🔴 🤖 Naif Assistant",
    "زر_نشر_تلقائي_تفعيل_ar": "📢 النشر التلقائي", "زر_نشر_تلقائي_تفعيل_en": "📢 Auto Publish",
    "زر_نشر_تلقائي_تعطيل_ar": "🔕 النشر التلقائي", "زر_نشر_تلقائي_تعطيل_en": "🔕 Auto Publish",
}

BOT_TEXTS = dict(DEFAULT_BOT_TEXTS)

BUTTON_STYLES: dict = {}
BUTTON_POSITIONS: dict = {}
_keyboards_cache: dict = {}
_allowed_texts_cache: dict = {}
BUTTON_TEXTS: set = set()


def _read_bot_texts_sheet():
    bilingual = {}
    try:
        rows = bot_texts_sheet.get_all_values()
    except Exception as e:
        logger.warning(f"bot_texts sheet error: {e}")
        return bilingual
    for row in rows:
        if not row or not row[0].strip():
            continue
        key = row[0].strip()
        ar_text = row[1].strip() if len(row) > 1 else ""
        en_text = row[2].strip() if len(row) > 2 else ""
        if not ar_text and not en_text:
            continue
        bilingual[key] = (ar_text, en_text)
    return bilingual


def _read_buttons_sheet(ws, with_positions=True):
    bilingual = {}
    styles = {}
    positions = {}
    try:
        rows = ws.get_all_values()
    except Exception as e:
        logger.warning(f"buttons sheet error: {e}")
        return bilingual, styles, positions
    for row in rows:
        if not row or not row[0].strip():
            continue
        key = row[0].strip()
        ar_text = row[1].strip() if len(row) > 1 else ""
        en_text = row[2].strip() if len(row) > 2 else ""
        if not ar_text and not en_text:
            continue
        style = row[3].strip().lower() if len(row) > 3 else ""
        bilingual[key] = (ar_text, en_text)
        if style in _VALID_STYLES:
            styles[key] = style
        if with_positions:
            pos_u = row[4].strip().upper() if len(row) > 4 else ""
            pos_a = row[5].strip().upper() if len(row) > 5 else ""
            pos_o = row[6].strip().upper() if len(row) > 6 else ""
            if pos_u or pos_a or pos_o:
                positions[key] = {"user": pos_u, "admin": pos_a, "owner": pos_o}
    return bilingual, styles, positions


def _parse_pos(pos: str):
    pos = pos.strip().upper()
    if not pos or len(pos) < 2:
        return None
    col_char = pos[0]
    row_str = pos[1:]
    if not row_str.isdigit():
        return None
    col = ord(col_char) - ord('A')
    row = int(row_str) - 1
    return (row, col)


def _build_keyboards_cache():
    global _keyboards_cache, _allowed_texts_cache

    roles = ["user", "admin", "owner"]
    grids = {r: {} for r in roles}

    for key, pos_dict in BUTTON_POSITIONS.items():
        for role in roles:
            pos = pos_dict.get(role, "")
            if not pos:
                continue
            parsed = _parse_pos(pos)
            if parsed is None:
                continue
            grids[role][parsed] = key

    new_kbs = {}
    new_allowed = {}

    for role in roles:
        grid = grids[role]
        if not grid:
            new_kbs[role] = None
            new_allowed[role] = set()
            continue

        sorted_keys = sorted(grid.items(), key=lambda x: (x[0][0], x[0][1]))
        rows_dict: dict = {}
        for (r, c), key in sorted_keys:
            rows_dict.setdefault(r, []).append((c, key))

        m = telebot.types.ReplyKeyboardMarkup(row_width=4, resize_keyboard=True)
        allowed = set()

        for r in sorted(rows_dict.keys()):
            row_btns = sorted(rows_dict[r], key=lambda x: x[0])
            buttons = []
            for _, key in row_btns:
                btn_text = BOT_TEXTS.get(f"{key}_ar", key)
                allowed.add(btn_text)
                style = BUTTON_STYLES.get(key, "")
                if style in _VALID_STYLES:
                    try:
                        buttons.append(telebot.types.KeyboardButton(btn_text, style=style))
                    except Exception:
                        buttons.append(telebot.types.KeyboardButton(btn_text))
                else:
                    buttons.append(telebot.types.KeyboardButton(btn_text))
            if buttons:
                m.row(*buttons)

        new_kbs[role] = m
        new_allowed[role] = allowed

    _keyboards_cache = new_kbs
    _allowed_texts_cache = new_allowed
    logger.info("✅ keyboards cache built")


def load_bot_texts():
    global BOT_TEXTS, BUTTON_STYLES, BUTTON_POSITIONS
    try:
        merged_bilingual = {}
        merged_styles = {}

        txt_bilingual = _read_bot_texts_sheet()
        merged_bilingual.update(txt_bilingual)

        kb_bilingual, kb_styles, kb_positions = _read_buttons_sheet(keyboard_buttons_sheet, with_positions=True)
        merged_bilingual.update(kb_bilingual)
        merged_styles.update(kb_styles)

        inl_bilingual, inl_styles, _inl_positions = _read_buttons_sheet(inline_buttons_sheet, with_positions=True)
        merged_bilingual.update(inl_bilingual)
        merged_styles.update(inl_styles)

        for key, (ar_text, en_text) in merged_bilingual.items():
            BOT_TEXTS[f"{key}_ar"] = ar_text or DEFAULT_BOT_TEXTS.get(f"{key}_ar", key)
            BOT_TEXTS[f"{key}_en"] = en_text or DEFAULT_BOT_TEXTS.get(f"{key}_en", key)

        BUTTON_STYLES = merged_styles
        BUTTON_POSITIONS = kb_positions

        _build_keyboards_cache()

        n_pos = sum(1 for p in BUTTON_POSITIONS.values() if any(p.values()))
        logger.info(
            f"✅ نصوص محمّلة: {len(txt_bilingual)} نص عادي، "
            f"{len(kb_bilingual)} زر كيبورد، {len(inl_bilingual)} زر inline، "
            f"{len(merged_styles)} لون، {n_pos} موضع كيبورد"
        )
    except Exception as e:
        logger.warning(f"load_bot_texts error: {e}")


def bt(key, uid=None):
    lang = "ar"
    if uid:
        rec = get_user_record(uid)
        if rec:
            lang = rec.get("lang", "ar")
    text_key = f"{key}_{lang}"
    if text_key in BOT_TEXTS:
        return BOT_TEXTS[text_key]
    fallback_key = f"{key}_ar"
    if fallback_key in BOT_TEXTS:
        return BOT_TEXTS[fallback_key]
    return DEFAULT_BOT_TEXTS.get(f"{key}_ar", key)


def _make_btn(key, uid=None):
    label = bt(key, uid)
    style = BUTTON_STYLES.get(key, "")
    if style in _VALID_STYLES:
        try:
            return telebot.types.KeyboardButton(label, style=style)
        except Exception:
            pass
    return telebot.types.KeyboardButton(label)


def _make_inline(key, label, callback_data):
    style = BUTTON_STYLES.get(key, "")
    if style in _VALID_STYLES:
        try:
            return telebot.types.InlineKeyboardButton(label, callback_data=callback_data, style=style)
        except Exception:
            pass
    return telebot.types.InlineKeyboardButton(label, callback_data=callback_data)


def load_button_texts():
    global BUTTON_TEXTS
    BUTTON_TEXTS = set()

    button_keys = [
        "زر_المواد", "زر_التكاليف", "زر_الجدول",
        "زر_الملخصات", "زر_طلب_رفع", "زر_رفع_تعليمات", "زر_الملازم", "زر_اضافة_محاضره",
        "زر_نماذج_الاختبارات", "زر_اعدادات",
        "زر_اشعار", "زر_اضافة", "زر_تعديل", "زر_المستخدمين", "زر_عوده",
        "زر_تحديد_الكل", "زر_تم_التحديد",
        "زر_اضافة_محاضره", "زر_اضافة_تكليف", "زر_اضافة_ملخص",
        "زر_اضافة_ملزمه", "زر_اضافة_نموذج", "زر_تعديل_محاضره", "زر_تعديل_تكليف",
        "زر_تعديل_ملخص", "زر_تعديل_ملزمه", "زر_تعديل_نموذج", "زر_تعديل_زرار", "زر_حذف_زرار",
        "خيار_نماذج_الاختبارات",
        "زر_تنبيه_اضافي", "زر_حفظ", "زر_اضافة_طالب", "زر_استبدال", "زر_اضافة_سعر_ملزمة", "زر_الغاء"
    ]
    for key in button_keys:
        BUTTON_TEXTS.add(bt(key))

    for role_texts in _allowed_texts_cache.values():
        BUTTON_TEXTS.update(role_texts)

    BUTTON_TEXTS.update([
        "↩️ رجوع خطوة",
        "🤖 مساعد نايف", "🟢 🤖 مساعد نايف", "🔴 🤖 مساعد نايف",
        "📢 النشر التلقائي", "🔕 النشر التلقائي",
        "📤 إرسال الآن", "✅ إرسال", "➕ إضافة محاضرة أخرى",
        "🚫 لا يوجد", "⏭️ تخطي", "🔄 استبدال", "✏️ بجانبه", "🔄 بدله",
        "✅ نعم، احذف", "📤 إرسال بدون نص", "👤 للمستخدمين",
        "👑 للأدمن", "👤 تعليمات المستخدم", "👑 تعليمات الأدمن",
        "🔍 بحث عن مستخدم",
        "🇾🇪 العربية", "🇬🇧 English", "📋 عرض جميع المستخدمين", "📋 آخر 3 مستخدمين"
    ])
