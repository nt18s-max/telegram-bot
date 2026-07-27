from sheets.connection import booklets_sheet
from sheets.data_repo import get_tab_data, refresh_data_cache
from utils.parsing import safe_get
from logging_utils import log_error


def get_subjects_with_booklets():
    try:
        seen = []
        for r in get_tab_data("booklets"):
            s = safe_get(r, 0)
            if s and safe_get(r, 2) and s not in seen:
                seen.append(s)
        return seen
    except Exception:
        return []


def get_booklets_for_subject(subject):
    try:
        items = []
        for r in get_tab_data("booklets"):
            if safe_get(r, 0) == subject:
                name = safe_get(r, 2)
                if name:
                    fid_cell = safe_get(r, 3)
                    items.append({
                        "name": name,
                        "price": safe_get(r, 1),
                        "file_ids": [f.strip() for f in fid_cell.split(",") if f.strip()] if fid_cell else [],
                    })
        return items
    except Exception as e:
        log_error(f"get_booklets_for_subject: {e}")
        return []


def _notify_new_booklet(subject, name, price):
    """إشعار معزول — فشله لا يجعل save_booklet تُرجع False رغم نجاح الحفظ فعلياً."""
    try:
        from features.broadcast import notify_auto_publish
        title = "📋 *ملزمة جديدة*"
        message = f"📌 *{subject}*\n📋 {name}" + (f"\n💰 {price}" if price else "")
        notify_auto_publish(title, message)
    except Exception as e:
        log_error(f"_notify_new_booklet: تعذّر إرسال إشعار النشر التلقائي (الحفظ نفسه تم بنجاح): {e}")


def save_booklet(subject, name, file_ids=None, price=""):
    try:
        file_ids = file_ids or []
        new_row = [subject, price, name, ",".join(file_ids), "", ""]
        booklets_sheet.append_row(new_row, value_input_option="USER_ENTERED")
        refresh_data_cache("booklets")
        _notify_new_booklet(subject, name, price)
        return True
    except Exception as e:
        log_error(f"save_booklet: {e} | المادة={subject} | الاسم={name}")
        return False


def replace_booklet_content(subject, old_name, new_name, file_ids, price=None):
    try:
        rows = booklets_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) == subject and safe_get(row, 2) == old_name:
                booklets_sheet.update_cell(i, 3, new_name)
                if file_ids:
                    booklets_sheet.update_cell(i, 4, ",".join(file_ids))
                if price is not None:
                    booklets_sheet.update_cell(i, 2, price)
                refresh_data_cache("booklets")
                return True
        return False
    except Exception as e:
        log_error(f"replace_booklet_content: {e}")
        return False


def delete_booklet(subject, name):
    try:
        rows = booklets_sheet.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if safe_get(row, 0) == subject and safe_get(row, 2) == name:
                booklets_sheet.delete_rows(i)
                refresh_data_cache("booklets")
                return True
        return False
    except Exception as e:
        log_error(f"delete_booklet: {e}")
        return False
