from datetime import datetime

from sheets.connection import lectures_sheet
from sheets.data_repo import get_tab_data, refresh_data_cache
from utils.parsing import safe_get, parse_date
from utils.time_parsing import parse_time_range, normalize_time
from logging_utils import log_info, log_error


def _notify_new_lecture(subject, date, time_val, room):
    """
    إشعار النشر التلقائي — بمعزل تام عن نتيجة الحفظ.
    ⚠️ إصلاح خلل تأكّدنا منه بالاختبار: الكود الأصلي كان يستدعي notify_auto_publish
    داخل نفس try/except الخاص بعملية الحفظ، فإذا فشل الإشعار (مثلاً features/broadcast.py
    غير مكتمل بعد، أو أي خطأ عابر بالإرسال) كانت الدالة بأكملها تُرجع False وتُبلّغ
    الأدمن "❌ حدث خطأ" رغم أن الصف كان قد أُضيف/عُدِّل فعلياً بالشيت بنجاح. عزلنا
    الإشعار بدالة مستقلة بـ try/except خاص بها حتى لا يؤثر فشله على نتيجة الحفظ أبداً.
    """
    try:
        from features.broadcast import notify_auto_publish
        title = "🕐 *محاضرة جديدة*"
        message = f"📌 *{subject}*\n📅 {date}\n🕐 {time_val}\n📍 {room}"
        notify_auto_publish(title, message)
    except Exception as e:
        log_error(f"_notify_new_lecture: تعذّر إرسال إشعار النشر التلقائي (الحفظ نفسه تم بنجاح): {e}")


def save_lecture(date, subject, time_val, room, alert=""):
    """يحدّث محاضرة موجودة (نفس التاريخ والمادة) أو يضيف صفاً جديداً."""
    try:
        rows = lectures_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            row_date = parse_date(safe_get(row, 0)) if safe_get(row, 0) else ""
            row_subj = safe_get(row, 1)
            if row_date == date and row_subj == subject:
                lectures_sheet.update_cell(i, 3, time_val)
                lectures_sheet.update_cell(i, 4, room)
                if alert:
                    lectures_sheet.update_cell(i, 5, alert)
                refresh_data_cache("lectures")
                log_info(f"save_lecture: تحديث صف {i} | {subject} | {date}")
                return True

        new_row = [date, subject, time_val, room, alert]
        lectures_sheet.append_row(new_row, value_input_option="USER_ENTERED")
        refresh_data_cache("lectures")
        log_info(f"save_lecture: إضافة جديدة | {subject} | {date} | {time_val} | {room}")
        _notify_new_lecture(subject, date, time_val, room)  # لا يمكن لفشلها إسقاط نجاح الحفظ (راجع تعليق الدالة)
        return True
    except Exception as e:
        log_error(f"save_lecture: {e} | المادة={subject} | التاريخ={date}")
        return False


def save_no_lecture(date):
    """يسجّل تاريخاً كـ 'لا يوجد فيه محاضرات' — بلا تكرار إذا كان مسجَّلاً مسبقاً."""
    try:
        rows = lectures_sheet.get_all_values()
        for row in rows[1:]:
            row_date = parse_date(safe_get(row, 0)) if safe_get(row, 0) else ""
            if row_date == date:
                return True
        new_row = [date, "", "لا يوجد", ""]
        lectures_sheet.append_row(new_row, value_input_option="USER_ENTERED")
        refresh_data_cache("lectures")
        log_info(f"save_no_lecture: تسجيل 'لا يوجد محاضرات' | {date}")
        return True
    except Exception as e:
        log_error(f"save_no_lecture: {e} | التاريخ={date}")
        return False


def save_lecture_time(date, subject, new_time):
    """يحدّث وقت محاضرة موجودة فقط."""
    try:
        rows = lectures_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) and parse_date(safe_get(row, 0)) == date and safe_get(row, 1) == subject:
                lectures_sheet.update_cell(i, 3, new_time)
                refresh_data_cache("lectures")
                return True
        return False
    except Exception as e:
        log_error(f"save_lecture_time: {e} | المادة={subject} | التاريخ={date}")
        return False


def delete_lecture(date, subject):
    """يحذف صف محاضرة كامل."""
    try:
        rows = lectures_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) and parse_date(safe_get(row, 0)) == date and safe_get(row, 1) == subject:
                lectures_sheet.delete_rows(i)
                refresh_data_cache("lectures")
                return True
        return False
    except Exception as e:
        log_error(f"delete_lecture: {e} | المادة={subject} | التاريخ={date}")
        return False


def date_has_lectures(date):
    """هل يوجد أي صف مسجَّل لهذا التاريخ (محاضرة حقيقية أو علامة 'لا يوجد')؟"""
    try:
        rows = lectures_sheet.get_all_values()
        for row in rows[1:]:
            row_date = safe_get(row, 0)
            if row_date and parse_date(row_date) == date:
                return True
        return False
    except Exception as e:
        log_error(f"date_has_lectures: {e}")
        return False


def get_last_lectures_for_subject(subject, n=3):
    """آخر n تاريخ محاضرة لمادة معينة (الأحدث أولاً) — تُستخدم لاقتراح التواريخ."""
    try:
        seen, dates = set(), []
        for r in get_tab_data("lectures"):
            s = safe_get(r, 1)
            d = safe_get(r, 0)
            t = safe_get(r, 2)
            if s == subject and d and t:
                p = parse_date(d)
                if p not in seen:
                    seen.add(p)
                    dates.append(p)
        dates.sort(key=lambda x: datetime.strptime(x, "%d/%m/%Y"), reverse=True)
        return dates[:n]
    except Exception:
        return []


def check_lecture_conflict(date, time_val):
    """يتحقق من تداخل وقت محاضرة جديدة مع محاضرة موجودة بنفس التاريخ. يرجع تفاصيل المتضارِبة أو None."""
    try:
        ns, ne = parse_time_range(time_val)
        if ns is None:
            return None
        for row in get_tab_data("lectures"):
            rd = parse_date(safe_get(row, 0))
            rt = safe_get(row, 2)
            if rd != date or not rt:
                continue
            es2, ee2 = parse_time_range(rt)
            if es2 is None:
                continue
            if ns < ee2 and es2 < ne:
                return {"subject": safe_get(row, 1), "room": safe_get(row, 3), "time": normalize_time(rt)}
    except Exception:
        pass
    return None
