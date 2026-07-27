from sheets.data_repo import get_tab_data
from sheets.users_repo import get_user_record, get_users, get_all_registered_uids
from utils.parsing import safe_get
from logging_utils import log_error

from ai.providers import AI_PROVIDERS, call_gemini, call_openrouter

AI_SYSTEM_PROMPT_BASE = (
    "أنت مساعد ذكي لطلاب الجامعة اسمك 'مساعد نايف'. أجب دائماً باللغة العربية ما لم يطلب المستخدم غير ذلك. "
    "إجاباتك مختصرة وواضحة ومناسبة للطلاب. لا تستخدم markdown بشكل مبالغ فيه.\n\n"
    "**تعليمات مهمة جداً عند الإجابة عن كيفية استخدام البوت:**\n"
    "- إذا سأل المستخدم 'كيف' يفعل شيئاً في البوت، اشرح له المسار بالأسهم مثل:\n"
    "  📚 المواد ← رياضيات ← 📝 التكاليف ← اختر التاريخ\n"
    "- اذكر اسم الزر كما يظهر في البوت بالضبط.\n"
    "- إذا كان هناك أكثر من طريقة، اذكرهم جميعاً.\n"
    "- كن محدداً ومختصراً."
)

_ai_histories: dict = {}
_AI_MAX_HISTORY = 20


def get_data_summary_for_ai(uid, user_role):
    lines = []

    rec = get_user_record(uid)
    if rec:
        role_label = "مالك" if rec["owner"] else ("أدمن" if rec["admin"] else ("مستخدم" if rec["allowed"] else "غير مصرح"))
        lines.append(
            f"### معلومات المستخدم ###\nالاسم: {rec['name']}\nالهاتف: {rec['phone'] or 'غير مسجل'}\n"
            f"الرتبة: {role_label}\nصلاحية AI: {'مفعلة' if rec['ai_allowed'] else 'معطلة'}\n"
        )
    else:
        lines.append("### معلومات المستخدم ###\nلم يتم العثور على معلوماتك.\n")

    if user_role == "owner":
        try:
            allowed, admins, owners, _open_all, _admin_all, _log_ids, ai_allowed, _auto = get_users()
            total_users = len(get_all_registered_uids())
            lines.append("### إحصائيات المستخدمين ###")
            lines.append(f"إجمالي المسجلين: {total_users}")
            lines.append(f"المصرح لهم: {len(allowed)}")
            lines.append(f"الأدمن: {len(admins)}")
            lines.append(f"المالكين: {len(owners)}")
            lines.append(f"المصرح لهم بـ AI: {len(ai_allowed)}\n")
        except Exception as e:
            log_error(f"إحصائيات المستخدمين: {e}")

    tabs = {
        "lectures": get_tab_data("lectures"),
        "assignments": get_tab_data("assignments"),
        "summaries": get_tab_data("summaries"),
        "booklets": get_tab_data("booklets"),
        "exams": get_tab_data("exams"),
    }
    if not any(tabs.values()):
        lines.append("لا توجد بيانات في قاعدة البيانات.")
        return "\n".join(lines)

    subjects = {}

    def _ensure(subj):
        if subj not in subjects:
            subjects[subj] = {"lectures": [], "tasks": [], "summaries": [], "booklets": [], "exams": []}

    for row in tabs["lectures"]:
        subject = safe_get(row, 1)
        lect = safe_get(row, 2)
        if not subject or not lect:
            continue
        _ensure(subject)
        subjects[subject]["lectures"].append((safe_get(row, 0), lect))

    for row in tabs["assignments"]:
        subject = safe_get(row, 0)
        name = safe_get(row, 1)
        if not subject or not name:
            continue
        _ensure(subject)
        txt = safe_get(row, 2)
        has_file = bool(safe_get(row, 4))
        subjects[subject]["tasks"].append(f"{name}" + (f": {txt}" if txt else "") + (" 📎" if has_file else ""))

    for row in tabs["summaries"]:
        subject = safe_get(row, 0)
        label = safe_get(row, 2)
        if not subject or not label:
            continue
        _ensure(subject)
        student = safe_get(row, 1)
        subjects[subject]["summaries"].append(f"{label}" + (f" — ✍️ {student}" if student else ""))

    for row in tabs["booklets"]:
        subject = safe_get(row, 0)
        name = safe_get(row, 2)
        if not subject or not name:
            continue
        _ensure(subject)
        price = safe_get(row, 1)
        has_file = bool(safe_get(row, 3))
        subjects[subject]["booklets"].append(f"{name}" + (f" — 💰 {price}" if price else "") + (" 📎" if has_file else ""))

    for row in tabs["exams"]:
        subject = safe_get(row, 0)
        name = safe_get(row, 1)
        if not subject or not name:
            continue
        _ensure(subject)
        subjects[subject]["exams"].append(name)

    lines.append("### قاعدة البيانات ###")
    for subj in sorted(subjects.keys()):
        details = subjects[subj]
        lines.append(f"\n**المادة: {subj}**")
        if details["lectures"]:
            lines.append("🕐 **المحاضرات** (التاريخ - الوقت):")
            for date, time_str in details["lectures"]:
                lines.append(f"   • {date} : {time_str}")
        if details["tasks"]:
            lines.append("📝 **التكاليف** (الاسم):")
            for desc in details["tasks"]:
                lines.append(f"   • {desc[:220]}")
        if details["summaries"]:
            lines.append("📖 **الملخصات**:")
            for desc in details["summaries"]:
                lines.append(f"   • {desc[:220]}")
        if details["booklets"]:
            lines.append("📋 **الملازم**:")
            for desc in details["booklets"]:
                lines.append(f"   • {desc[:220]}")
        if details["exams"]:
            lines.append("🧾 **نماذج الاختبارات**:")
            for desc in details["exams"]:
                lines.append(f"   • {desc[:220]}")

    lines.append(f"\n📚 المواد المتاحة: {', '.join(sorted(subjects.keys()))}")

    if user_role in ("admin", "owner"):
        lines.append("\n### الأوامر الإدارية المتاحة عبر المحادثة ###")
        lines.append("- `أرسل إشعار للجميع: [النص]` - إرسال إشعار لجميع المستخدمين")
        lines.append("- `بلغ المستخدم [ID] يقول له: [النص]` - إرسال إشعار لمستخدم محدد")
        lines.append("- `فعّل AI للمستخدم [ID]` / `عطّل AI للمستخدم [ID]` (للمالك فقط)")
        lines.append("- `اجعل [ID] أدمن/مستخدم` - تغيير رتبة مستخدم (للمالك فقط)")

    return "\n".join(lines)


def get_bot_code_summary(uid):
    from sheets.texts_repo import bt
    from features.browsing import get_subjects, get_subjects_with_doctors

    lines = []
    lines.append("### معلومات عامة عن البوت ###")
    lines.append("- بوت دراسي لطلاب الجامعة: محاضرات، تكاليف، ملخصات، تنبيهات، أسعار ملازم.")
    lines.append("- قاعدة البيانات: Google Sheets. يدعم العربية والإنجليزية.")
    lines.append("- الأزرار في لوحة المفاتيح أسفل الشاشة.")

    lines.append("\n### الرتب ###")
    lines.append("- مستخدم: عرض البيانات، طلب رفع ملف، مساعد نايف (بإذن المالك).")
    lines.append("- أدمن: إضافة/تعديل/حذف، رفع ملفات، إرسال إشعارات.")
    lines.append("- مالك: كل الصلاحيات + إدارة المستخدمين.")

    B = {k: bt(v, uid) for k, v in {
        "مواد": "زر_المواد", "تكاليف": "زر_التكاليف", "جدول": "زر_الجدول",
        "ملخصات": "زر_الملخصات", "طلب_رفع": "زر_طلب_رفع", "رفع_تعليمات": "زر_رفع_تعليمات",
        "اشعار": "زر_اشعار", "اضافة": "زر_اضافة", "تعديل": "زر_تعديل",
        "مستخدمين": "زر_المستخدمين", "عوده": "زر_عوده",
        "خيار_جدول": "خيار_الجدول", "خيار_تكاليف": "خيار_التكاليف", "خيار_ملخص": "خيار_الملخص",
        "اضافة_محاضره": "زر_اضافة_محاضره", "اضافة_تكليف": "زر_اضافة_تكليف", "اضافة_ملخص": "زر_اضافة_ملخص",
        "تعديل_محاضره": "زر_تعديل_محاضره", "تعديل_تكليف": "زر_تعديل_تكليف", "تعديل_ملخص": "زر_تعديل_ملخص",
        "اضافة_ملزمه": "زر_اضافة_ملزمه", "تعديل_ملزمه": "زر_تعديل_ملزمه",
        "نماذج": "زر_نماذج_الاختبارات", "اضافة_نموذج": "زر_اضافة_نموذج", "تعديل_نموذج": "زر_تعديل_نموذج",
    }.items()}

    try:
        subjects = get_subjects()
        subjects_with_docs = get_subjects_with_doctors()
        if subjects_with_docs:
            subjects_str = " | ".join(
                f"{s} ({', '.join(docs)})" if docs else s for s, docs in subjects_with_docs.items()
            )
        elif subjects:
            subjects_str = " / ".join(subjects)
        else:
            subjects_str = "لا توجد مواد بعد"
    except Exception:
        subjects = []
        subjects_str = "غير متاح"
    lines.append(f"\nالمواد المتاحة حالياً: {subjects_str}")

    lines.append("\n### كيفية استخدام كل ميزة ###")
    lines.append(f"\n## التكاليف ##")
    lines.append(f"طريقة 1 (مادة معينة): {B['مواد']} ← اسم المادة ← {B['خيار_تكاليف']} ← اختر التاريخ")
    lines.append(f"طريقة 2 (آخر تكليف): {B['تكاليف']}")

    lines.append(f"\n## جدول المحاضرات ##")
    lines.append(f"طريقة 1 (آخر يوم): {B['جدول']}")
    lines.append(f"طريقة 2 (مادة معينة): {B['مواد']} ← اسم المادة ← {B['خيار_جدول']} ← اختر التاريخ")

    lines.append(f"\n## الملخصات ##")
    lines.append(f"طريقة 1 (مادة معينة): {B['مواد']} ← اسم المادة ← {B['خيار_ملخص']} ← اختر التاريخ")
    lines.append(f"طريقة 2 (آخر ملخص): {B['ملخصات']}")

    lines.append(f"\n## طلب رفع ملف (مستخدم عادي) ##")
    lines.append(f"{B['طلب_رفع']} ← اسم المادة ← {B['اضافة_تكليف']} أو {B['اضافة_ملخص']} ← التاريخ ← أرسل الملف ← ✅ إرسال")
    lines.append("يصل الطلب للأدمن ليوافق أو يرفضه ويُضاف تلقائياً.")

    lines.append(f"\n## الإعدادات (مساعد نايف / النشر التلقائي / اللغة) ##")
    lines.append(f"اضغط زر '{bt('زر_اعدادات', uid)}' من القائمة الرئيسية ← تظهر أزرار Inline.")

    lines.append("\n### ميزات الأدمن والمالك ###")
    lines.append(f"\n## إضافة بيانات ##")
    lines.append(f"{B['اضافة']} ← اختر النوع:")
    lines.append(f"• {B['اضافة_محاضره']}: التاريخ ← المبنى ← القاعة ← المادة ← الوقت")
    lines.append(f"• {B['اضافة_تكليف']}: المادة ← اسم التكليف ← نص و/أو ملفات ← حفظ")
    lines.append(f"• {B['اضافة_ملخص']}: المادة ← أرسل ملف الملخص ← اختر اسم الطالب")
    lines.append(f"• {B['اضافة_ملزمه']}: المادة ← اسم الملزمة ← أرسل الملف ← حفظ أو إضافة سعر")
    lines.append(f"• {B['اضافة_نموذج']}: المادة ← نوع النموذج ← أرسل الملف")

    lines.append(f"\n## تعديل أو حذف ##")
    lines.append(f"{B['تعديل']} ← اختر النوع ← المادة ← تعديل أو حذف")

    lines.append(f"\n## إرسال إشعار ##")
    lines.append(f"{B['اشعار']} ← اكتب النص ← أرسل ملف (اختياري) ← 📤 إرسال الآن")

    lines.append(f"\n## إدارة المستخدمين (مالك) ##")
    lines.append(f"{B['مستخدمين']} ← بحث بالاسم/الرقم/ID أو عرض الكل")

    lines.append("\n## الأوامر النصية (أدمن/مالك عبر مساعد نايف) ##")
    lines.append("• أرسل إشعار للجميع: تذكير بالاختبار غداً")
    lines.append("• بلغ المستخدم 123456789 يقول له: أهلاً")
    lines.append("• فعّل AI للمستخدم 123456789")
    lines.append("• اجعل 123456789 أدمن")

    return "\n".join(lines)


def ask_ai(uid, user_text, user_role="user"):
    if not AI_PROVIDERS:
        return None, None

    if uid not in _ai_histories:
        _ai_histories[uid] = []
    _ai_histories[uid].append({"role": "user", "content": user_text})
    if len(_ai_histories[uid]) > _AI_MAX_HISTORY:
        _ai_histories[uid] = _ai_histories[uid][-_AI_MAX_HISTORY:]

    data_summary = get_data_summary_for_ai(uid, user_role)
    bot_summary = get_bot_code_summary(uid)

    if user_role == "owner":
        role_desc = (
            "أنت مالك البوت. لديك صلاحيات كاملة: إدارة المستخدمين، تغيير الرتب، "
            "تفعيل/تعطيل صلاحية AI، بالإضافة إلى كل صلاحيات الأدمن."
        )
    elif user_role == "admin":
        role_desc = "أنت أدمن في البوت. لديك صلاحيات الإضافة والتعديل والحذف على جميع البيانات، ويمكنك إرسال إشعارات ورفع ملفات مباشرة."
    else:
        role_desc = "أنت مستخدم عادي. يمكنك فقط عرض البيانات. لا يمكنك رفع ملفات مباشرة، لكن يمكنك طلب رفع ملف عبر الزر المخصص."

    admin_note = ""
    if user_role in ("admin", "owner"):
        admin_note = (
            "\n\n**ملاحظة للمستخدم (أدمن/مالك):**\n"
            "يمكنك إصدار أوامر نصية حرة لثلاثة أشياء فقط:\n"
            "- إرسال إشعار (فردي أو للجميع)\n"
            "- تفعيل/تعطيل AI لمستخدم\n"
            "- تغيير رتبة مستخدم\n"
            "أي طلب إضافة/تعديل/حذف محاضرة أو تكليف أو ملخص أو ملزمة أو نموذج **لا يتم عبر النص** —"
            " وجّه المستخدم لاستخدام الأزرار المخصصة بدلاً من ذلك."
        )

    system_prompt = (
        AI_SYSTEM_PROMPT_BASE + "\n\n" + role_desc + "\n\n"
        f"### قاعدة البيانات ###\n{data_summary}\n\n"
        f"### شرح البوت ###\n{bot_summary}\n\n"
        + admin_note +
        "\n**تعليمات مهمة:**\n"
        "1. إذا طلب المستخدم عدداً معيناً من العناصر، أعطه بالضبط العدد الذي طلبه.\n"
        "2. إذا طلب بدون تحديد عدد، أعطه آخر عنصر (أو آخر 2-3 إذا كان ذلك مناسباً).\n"
        "3. استخدم البيانات المتاحة فقط للإجابة.\n"
        "4. لا تقدم معلومات عن المستخدمين الآخرين للمستخدم العادي أو الأدمن.\n"
        "5. كن دقيقاً ومباشراً."
    )

    for provider in AI_PROVIDERS:
        if provider["provider"] == "gemini":
            response, model_info = call_gemini(provider, uid, user_text, system_prompt)
        elif provider["provider"] == "openrouter":
            response, model_info = call_openrouter(provider, uid, _ai_histories[uid], system_prompt)
        else:
            continue

        if response:
            _ai_histories[uid].append({"role": "assistant", "content": response})
            if len(_ai_histories[uid]) > _AI_MAX_HISTORY:
                _ai_histories[uid] = _ai_histories[uid][-_AI_MAX_HISTORY:]
            return response, model_info

    return None, None
