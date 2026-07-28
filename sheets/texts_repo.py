import logging

import telebot

from sheets.connection import bot_texts_sheet, keyboard_buttons_sheet, inline_buttons_sheet
from sheets.users_repo import get_user_record

logger = logging.getLogger("StudyTestBot")

_VALID_STYLES = {"danger", "success", "primary"}

DEFAULT_BOT_TEXTS = {
    "رسالة_الترحيب_ar": "مرحباً بك في بوت الدراسة الجامعة!",
    "رسالة_الترحيب_en": "Welcome to University Study Bot!",
    "رسالة_الرفض_ar": "⛔ ليس لديك صلاحية الوصول.",
    "رسالة_الرفض_en": "⛔ Access denied.",
    "رسالة_انتظار_ar": "⏳ طلبك قيد المراجعة.",
    "رسالة_انتظار_en": "⏳ Your request is under review.",
    "رسالة_موافقة_ar": "✅ تمت الموافقة على طلبك وتفعيل حسابك!",
    "رسالة_موافقة_en": "✅ Your request has been approved!",
    "رسالة_رفض_طلب_ar": "❌ نعتذر، تم رفض طلب التفعيل.",
    "رسالة_رفض_طلب_en": "❌ Sorry, your activation request was rejected.",
    "زر_المواد_ar": "📚 المواد",
    "زر_المواد_en": "📚 Subjects",
    "زر_التكاليف_ar": "📝 التكاليف",
    "زر_التكاليف_en": "📝 Assignments",
    "زر_الجدول_ar": "🕐 أوقات المحاضرات",
    "زر_الجدول_en": "🕐 Schedule",
    "زر_الملازم_ar": "📋 الملازم",
    "زر_الملازم_en": "📋 Booklets",
    "خيار_الملزمه_ar": "📋 الملازم",
    "خيار_الملزمه_en": "📋 Booklets",
    "زر_اضافة_ملزمه_ar": "📋 إضافة ملزمة",
    "زر_اضافة_ملزمه_en": "📋 Add Booklet",
    "زر_تعديل_ملزمه_ar": "📋 تعديل/حذف ملزمة",
    "زر_تعديل_ملزمه_en": "📋 Edit/Delete Booklet",
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
    "زر_الملخصات_ar": "📖 الملخصات",
    "زر_الملخصات_en": "📖 Summaries",
    "زر_طلب_رفع_ar": "📤 طلب رفع ملف",
    "زر_طلب_رفع_en": "📤 Request Upload",
    "زر_رفع_تعليمات_ar": "📹 رفع التعليمات",
    "زر_رفع_تعليمات_en": "📹 Upload Instructions",
    "زر_اعدادات_ar": "⚙️ الإعدادات",
    "زر_اعدادات_en": "⚙️ Settings",
    "زر_اشعار_ar": "📢 إرسال إشعار",
    "زر_اشعار_en": "📢 Send Notification",
    "زر_اضافة_ar": "➕ إضافة",
    "زر_اضافة_en": "➕ Add",
    "زر_تعديل_ar": "✏️ تعديل",
    "زر_تعديل_en": "✏️ Edit",
    "زر_المستخدمين_ar": "👥 إدارة المستخدمين",
    "زر_المستخدمين_en": "👥 Users Management",
    "زر_عوده_ar": "🔙 العودة",
    "زر_عوده_en": "🔙 Back",
    "زر_تحديد_الكل_ar": "✅ تحديد الكل",
    "زر_تحديد_الكل_en": "✅ Select All",
    "زر_تم_التحديد_ar": "✅ تم التحديد",
    "زر_تم_التحديد_en": "✅ Done",
    "زر_اضافة_محاضره_ar": "🕐 إضافة محاضرة",
    "زر_اضافة_محاضره_en": "🕐 Add Lecture",
    "زر_اضافة_تكليف_ar": "📝 إضافة تكليف",
    "زر_اضافة_تكليف_en": "📝 Add Assignment",
    "زر_اضافة_ملخص_ar": "📖 إضافة ملخص",
    "زر_اضافة_ملخص_en": "📖 Add Summary",
    "زر_تعديل_محاضره_ar": "🕐 تعديل محاضرة",
    "زر_تعديل_محاضره_en": "🕐 Edit Lecture",
    "زر_تعديل_تكليف_ar": "📝 تعديل تكليف",
    "زر_تعديل_تكليف_en": "📝 Edit Assignment",
    "زر_تعديل_ملخص_ar": "📖 تعديل ملخص",
    "زر_تعديل_ملخص_en": "📖 Edit Summary",
    "زر_تعديل_زرار_ar": "✏️ تعديل زر",
    "زر_تعديل_زرار_en": "✏️ Edit Button",
    "زر_حذف_زرار_ar": "🗑 حذف زر",
    "زر_حذف_زرار_en": "🗑 Delete Button",
    "خيار_الجدول_ar": "🕐 أوقات المحاضرات",
    "خيار_الجدول_en": "🕐 Schedule",
    "خيار_التكاليف_ar": "📝 التكاليف",
    "خيار_التكاليف_en": "📝 Assignments",
    "خيار_الملخص_ar": "📖 الملخصات",
    "خيار_الملخص_en": "📖 Summaries",
    "رسالة_لا_بيانات_ar": "📭 لا توجد بيانات مسجلة حالياً.",
    "رسالة_لا_بيانات_en": "📭 No data recorded currently.",
    "رسالة_خطأ_ar": "❌ حدث خطأ غير متوقع، يرجى المحاولة لاحقاً.",
    "رسالة_خطأ_en": "❌ An unexpected error occurred, please try again later.",
    "رسالة_تم_الحفظ_ar": "✅ تم الحفظ بنجاح!",
    "رسالة_تم_الحفظ_en": "✅ Saved successfully!",
    "رسالة_تم_الحذف_ar": "🗑 تم الحذف بنجاح!",
    "رسالة_تم_الحذف_en": "🗑 Deleted successfully!",
    "رسالة_تم_التعديل_ar": "✏️ تم التعديل بنجاح!",
    "رسالة_تم_التعديل_en": "✏️ Updated successfully!",
    "رسالة_ادمن_فقط_ar": "⛔ هذا الخيار متاح للأدمن والمالك فقط.",
    "رسالة_ادمن_فقط_en": "⛔ This feature is only available for admins/owners.",
    "رسالة_نايف_يكتب_ar": "✍️ نايف يكتب...",
    "رسالة_نايف_يكتب_en": "✍️ Naif is typing...",
    "رسالة_ai_غير_مفعل_ar": "🤖 مساعد نايف غير مفعل حالياً.",
    "رسالة_ai_غير_مفعل_en": "🤖 Naif Assistant is currently disabled.",
    "رسالة_ai_غير_مسموح_ar": "⛔ ليس لديك صلاحية استخدام المساعد الذكي.",
    "رسالة_ai_غير_مسموح_en": "⛔ You do not have permission to use AI Assistant.",
    "رسالة_ai_اشتراك_ar": "ℹ️ يمكنك طلب تفعيل خدمة AI من المالك عبر الإعدادات.",
    "رسالة_ai_اشتراك_en": "ℹ️ You can request AI access from the owner via settings.",
    "رسالة_ai_فشل_ar": "⚠️ تعذر المعالجة عبر الذكاء الاصطناعي حالياً.",
    "رسالة_ai_فشل_en": "⚠️ AI processing failed currently.",
    "رسالة_ai_تم_الغاء_ar": "❌ تم إلغاء تفعيل الذكاء الاصطناعي.",
    "رسالة_ai_تم_الغاء_en": "❌ AI Assistant access cancelled.",
    "رسالة_ai_تفعيل_ar": "🤖 تم تفعيل المساعد الذكي لحسابك!",
    "رسالة_ai_تفعيل_en": "🤖 AI Assistant enabled for your account!",
    "رسالة_ai_تعطيل_ar": "🔴 تم تعطيل المساعد الذكي لحسابك.",
    "رسالة_ai_تعطيل_en": "🔴 AI Assistant disabled for your account.",
    "رسالة_ai_ترحيب_ar": "🤖 مرحباً بك في المساعد الذكي!",
    "رسالة_ai_ترحيب_en": "🤖 Welcome to AI Assistant!",
    "رسالة_تغيير_اللغة_ar": "🌐 اختر اللغة المفضلة:",
    "رسالة_تغيير_اللغة_en": "🌐 Select your preferred language:",
    "رسالة_تم_تغيير_اللغة_ar": "✅ تم تغيير اللغة إلى العربية.",
    "رسالة_تم_تغيير_اللغة_en": "✅ Language changed to English.",
    "رسالة_طلب_جهة_اتصال_ar": "📱 يرجى مشاركة رقم هاتفك عبر الزر أدناه لطلب التفعيل:",
    "رسالة_طلب_جهة_اتصال_en": "📱 Please share your phone number below for activation:",
    "رسالة_شكر_اتصال_ar": "✅ شكراً لك، تم استلام رقم هاتفك وسيتم مراجعته.",
    "رسالة_شكر_اتصال_en": "✅ Thank you, phone number received for review.",
    "رسالة_غير_مسموح_ar": "⛔ حسابك غير مصرح له باستخدام البوت حالياً.",
    "رسالة_غير_مسموح_en": "⛔ Your account is not authorized to use the bot currently.",
    "زر_مشاركة_رقم_ar": "📞 مشاركة رقم الهاتف",
    "زر_مشاركة_رقم_en": "📞 Share Phone Number",
    "زر_لا_اريد_ar": "❌ لا أريد مشاركة رقمي",
    "زر_لا_اريد_en": "❌ I do not wish to share my number",
    "رسالة_مشاركة_ar": "📱 اضغط على الزر أدناه لمشاركة رقمك:",
    "رسالة_مشاركة_en": "📱 Press the button below to share your number:",
    "زر_مشاركة_كيبورد_ar": "📞 مشاركة رقم الهاتف",
    "زر_مشاركة_كيبورد_en": "📞 Share Phone Number",
    "زر_عوده_مشاركه_ar": "🔙 العودة",
    "زر_عوده_مشاركه_en": "🔙 Back",
    "رسالة_كيبورد_مشاركة_ar": "📱 شارك رقمك للتفعيل:",
    "رسالة_كيبورد_مشاركة_en": "📱 Share your number for activation:",
    "زر_عوده_مشاركه_en": "🔙 Back",
    "رسالة_لا_اريد_ar": "تم إلغاء الطلب.",
    "رسالة_لا_اريد_en": "Request cancelled.",
    "زر_بوت_تواصل_ar": "💬 بوت التواصل",
    "زر_بوت_تواصل_en": "💬 Contact Bot",
    "رابط_بوت_تواصل_ar": "https://t.me/",
    "رابط_بوت_تواصل_en": "https://t.me/",
    "رسالة_جاري_الحذف_ar": "⏳ جاري الحذف...",
    "رسالة_جاري_الحذف_en": "⏳ Deleting...",
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
