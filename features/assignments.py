from sheets.connection import assignments_sheet
from sheets.data_repo import get_tab_data, refresh_data_cache
from utils.parsing import safe_get
from logging_utils import log_error


def get_subjects_with_tasks():
    try:
        seen = []
        for r in get_tab_data("assignments"):
            s = safe_get(r, 0)
            if s and safe_get(r, 1) and s not in seen:
                seen.append(s)
        return seen
    except Exception:
        return []


def get_tasks_for_subject(subject):
    try:
        tasks = []
        for r in get_tab_data("assignments"):
            if safe_get(r, 0) == subject:
                name = safe_get(r, 1)
                if name:
                    fid_cell = safe_get(r, 4)
                    tasks.append({
                        "name": name,
                        "text": safe_get(r, 2),
                        "alert": safe_get(r, 3),
                        "file_ids": [f.strip() for f in fid_cell.split(",") if f.strip()] if fid_cell else [],
                    })
        return tasks
    except Exception as e:
        log_error(f"get_tasks_for_subject: {e}")
        return []


def _notify_new_task(subject, name, text_val):
    """إشعار معزول — فشله لا يجعل save_task تُرجع False رغم نجاح الحفظ فعلياً."""
    try:
        from features.broadcast import notify_auto_publish
        title = "📝 *تكليف جديد*"
        message = f"📌 *{subject}*\n📋 {name}" + (f"\n{text_val}" if text_val else "")
        notify_auto_publish(title, message)
    except Exception as e:
        log_error(f"_notify_new_task: تعذّر إرسال إشعار النشر التلقائي (الحفظ نفسه تم بنجاح): {e}")


def save_task(subject, name, text_val="", file_ids=None, alert=""):
    try:
        file_ids = file_ids or []
        rows = assignments_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) == subject and safe_get(row, 1) == name:
                if text_val:
                    assignments_sheet.update_cell(i, 3, text_val)
                if alert:
                    assignments_sheet.update_cell(i, 4, alert)
                if file_ids:
                    existing_fids = safe_get(row, 4)
                    all_fids = (existing_fids.split(",") if existing_fids else []) + file_ids
                    assignments_sheet.update_cell(i, 5, ",".join(all_fids))
                refresh_data_cache("assignments")
                return True

        new_row = [subject, name, text_val, alert, ",".join(file_ids), "", ""]
        assignments_sheet.append_row(new_row, value_input_option="USER_ENTERED")
        refresh_data_cache("assignments")
        _notify_new_task(subject, name, text_val)
        return True
    except Exception as e:
        log_error(f"save_task: {e} | المادة={subject} | الاسم={name}")
        return False


def replace_task_content(subject, name, text_val, file_ids):
    try:
        rows = assignments_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) == subject and safe_get(row, 1) == name:
                assignments_sheet.update_cell(i, 3, text_val)
                if file_ids:
                    assignments_sheet.update_cell(i, 5, ",".join(file_ids))
                refresh_data_cache("assignments")
                return True
        return False
    except Exception as e:
        log_error(f"replace_task_content: {e}")
        return False


def delete_task(subject, name):
    try:
        rows = assignments_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) == subject and safe_get(row, 1) == name:
                assignments_sheet.delete_rows(i)
                refresh_data_cache("assignments")
                return True
        return False
    except Exception as e:
        log_error(f"delete_task: {e}")
        return False
