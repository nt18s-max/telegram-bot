from sheets.cache_utils import SafeCache
from sheets.connection import rooms_sheet
from logging_utils import log_error

_cache = SafeCache("القاعات والمواد")


def _fetch_rooms_raw():
    if not rooms_sheet:
        return []
    return rooms_sheet.get_all_values()[1:]


def _load():
    return _cache.get_or_fetch(_fetch_rooms_raw)


def refresh_rooms_cache():
    return _cache.refresh(_fetch_rooms_raw)


def get_rooms(building):
    try:
        rows = _load()
        if not rows:
            return []
        return [r[1].strip() for r in rows if len(r) > 1 and r[0].strip() == building and r[1].strip()]
    except Exception as e:
        log_error(f"get_rooms: {e}")
        return []


def get_subject_doctor(subject):
    try:
        rows = _load()
        if not rows:
            return ""
        for r in rows:
            if len(r) > 3 and r[3].strip() == subject and r[2].strip():
                return r[2].strip()
        return ""
    except Exception as e:
        log_error(f"get_subject_doctor: {e}")
        return ""


def get_subjects_from_rooms():
    try:
        rows = _load()
        if not rows:
            return []
        seen, result = set(), []
        for r in rows:
            s = r[3].strip() if len(r) > 3 else ""
            if s and s not in seen:
                seen.add(s)
                result.append(s)
        return result
    except Exception as e:
        log_error(f"get_subjects_from_rooms: {e}")
        return []
