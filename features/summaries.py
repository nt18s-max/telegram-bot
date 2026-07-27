from sheets.connection import summaries_sheet
from sheets.data_repo import get_tab_data, refresh_data_cache
from utils.parsing import safe_get
from logging_utils import log_error


def get_subjects_with_summaries():
    try:
        seen = []
        for r in get_tab_data("summaries"):
            s = safe_get(r, 0)
            if s and safe_get(r, 2) and s not in seen:
                seen.append(s)
        return seen
    except Exception:
        return []


def get_summaries_for_subject(subject):
    try:
        items = []
        for r in get_tab_data("summaries"):
            if safe_get(r, 0) == subject:
                label = safe_get(r, 2)
                if label:
                    fid_cell = safe_get(r, 3)
                    items.append({
                        "label": label,
                        "student": safe_get(r, 1),
                        "file_ids": [f.strip() for f in fid_cell.split(",") if f.strip()] if fid_cell else [],
                    })
        return items
    except Exception as e:
        log_error(f"get_summaries_for_subject: {e}")
        return []


def get_known_students():
    try:
        seen = []
        for r in get_tab_data("summaries"):
            s = safe_get(r, 1)
            if s and s not in seen:
                seen.append(s)
        return seen
    except Exception:
        return []


def _notify_new_summary(subject, student, label):
    """إشعار معزول — فشله لا يجعل save_summary تُرجع False رغم نجاح الحفظ فعلياً."""
    try:
        from features.broadcast import notify_auto_publish
        title = "📖 *ملخص جديد*"
        message = f"📌 *{subject}*\n📖 {label}\n✍️ {student}"
        notify_auto_publish(title, message)
    except Exception as e:
        log_error(f"_notify_new_summary: تعذّر إرسال إشعار النشر التلقائي (الحفظ نفسه تم بنجاح): {e}")


def save_summary(subject, student, label, file_ids=None):
    try:
        file_ids = file_ids or []
        new_row = [subject, student, label, ",".join(file_ids), "", ""]
        summaries_sheet.append_row(new_row, value_input_option="USER_ENTERED")
        refresh_data_cache("summaries")
        _notify_new_summary(subject, student, label)
        return True
    except Exception as e:
        log_error(f"save_summary: {e} | المادة={subject} | الطالب={student}")
        return False


def replace_summary_content(subject, old_label, new_label, file_ids):
    try:
        rows = summaries_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) == subject and safe_get(row, 2) == old_label:
                summaries_sheet.update_cell(i, 3, new_label)
                if file_ids:
                    summaries_sheet.update_cell(i, 4, ",".join(file_ids))
                refresh_data_cache("summaries")
                return True
        return False
    except Exception as e:
        log_error(f"replace_summary_content: {e}")
        return False


def delete_summary(subject, label):
    try:
        rows = summaries_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) == subject and safe_get(row, 2) == label:
                summaries_sheet.delete_rows(i)
                refresh_data_cache("summaries")
                return True
        return False
    except Exception as e:
        log_error(f"delete_summary: {e}")
        return False
