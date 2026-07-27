from sheets.cache_utils import SafeCache
from sheets.connection import help_sheet
from logging_utils import log_error

_cache = SafeCache("المساعدة")


def _fetch_help_raw():
    if not help_sheet:
        return []
    return help_sheet.get_all_values()


def _load():
    return _cache.get_or_fetch(_fetch_help_raw)


def refresh_help_cache():
    return _cache.refresh(_fetch_help_raw)


def get_help_file_id(key, file_type="photo"):
    """استرجاع file_id من صفحة المساعدة حسب المفتاح"""
    try:
        rows = _load()
        if not rows:
            return None
        for row in rows:
            if len(row) >= 3 and row[0].strip() == key and row[2].strip() == file_type:
                return row[1].strip()
        return None
    except Exception as e:
        log_error(f"get_help_file_id: {e}")
        return None


def get_help_materials():
    try:
        rows = _load()
        if not rows:
            return []
        mats = []
        for row in rows:
            if not row or not any(r.strip() for r in row if r):
                continue
            fid = row[1].strip() if len(row) > 1 else ""
            ftype = row[2].strip() if len(row) > 2 else ""
            aud = row[3].strip() if len(row) > 3 else "user"
            note = row[4].strip() if len(row) > 4 else ""
            if fid or note:
                mats.append({"file_id": fid, "file_type": ftype, "audience": aud, "note": note})
        return mats
    except Exception as e:
        log_error(f"get_help_materials: {e}")
        return []


def save_help_material(files_data, audience, note=""):
    try:
        if not help_sheet:
            return False
        rows = help_sheet.get_all_values()
        nrow = len(rows) + 1
        if note:
            help_sheet.update([[f"note_{nrow}", "", "", audience, note]], f"A{nrow}:E{nrow}")
            nrow += 1
        for fd in files_data:
            help_sheet.update([[f"file_{nrow}", fd["file_id"], fd["file_type"], audience, ""]], f"A{nrow}:E{nrow}")
            nrow += 1
        refresh_help_cache()
        return True
    except Exception as e:
        log_error(f"save_help_material: {e}")
        return False
