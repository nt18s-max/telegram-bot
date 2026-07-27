"""
exams.py — بيانات وتدفق نماذج الاختبارات.
"""

from sheets.connection import exams_sheet
from sheets.data_repo import get_tab_data, refresh_data_cache
from utils.parsing import safe_get
from logging_utils import log_error


def _notify_new_exam(subject, name):
    """إشعار النشر التلقائي بمعزل تام عن عملية الحفظ."""
    try:
        from features.broadcast import notify_auto_publish
        title = "🧾 *نموذج اختبار جديد*"
        message = f"📌 *{subject}*\n🧾 {name}"
        notify_auto_publish(title, message)
    except Exception as e:
        log_error(f"_notify_new_exam: تعذّر إرسال إشعار النشر التلقائي (الحفظ تم بنجاح): {e}")


def get_exams_for_subject(subject):
    try:
        items = []
        for r in get_tab_data("exams"):
            s = safe_get(r, 0)
            name = safe_get(r, 1)
            fid_cell = safe_get(r, 2)
            if s == subject and name:
                items.append({
                    "name": name,
                    "file_ids": [f.strip() for f in fid_cell.split(",") if f.strip()] if fid_cell else [],
                })
        return items
    except Exception as e:
        log_error(f"get_exams_for_subject: {e}")
        return []


def save_exam(subject, name, file_ids=None):
    """يضيف صف نموذج اختبار جديد لصفحة 'نماذج الاختبارات'."""
    try:
        file_ids = file_ids or []
        new_row = [subject, name, ",".join(file_ids), "", ""]
        exams_sheet.append_row(new_row, value_input_option="USER_ENTERED")
        refresh_data_cache("exams")
        _notify_new_exam(subject, name)
        return True
    except Exception as e:
        log_error(f"save_exam: {e} | المادة={subject} | الاسم={name}")
        return False


def delete_exam(subject, name):
    try:
        rows = exams_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) == subject and safe_get(row, 1) == name:
                exams_sheet.delete_rows(i)
                refresh_data_cache("exams")
                return True
        return False
    except Exception as e:
        log_error(f"delete_exam: {e}")
        return False


def replace_exam_content(subject, old_name, new_name, file_ids):
    """يستبدل اسم و/أو ملف نموذج اختبار موجود."""
    try:
        rows = exams_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) == subject and safe_get(row, 1) == old_name:
                exams_sheet.update_cell(i, 2, new_name)
                if file_ids:
                    exams_sheet.update_cell(i, 3, ",".join(file_ids))
                refresh_data_cache("exams")
                return True
        return False
    except Exception as e:
        log_error(f"replace_exam_content: {e}")
        return False
