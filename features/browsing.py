from sheets.connection import rooms_sheet
from sheets.data_repo import get_tab_data
from utils.parsing import safe_get
from logging_utils import log_error


def get_subjects():
    try:
        seen, result = set(), []
        if rooms_sheet:
            try:
                for row in rooms_sheet.get_all_values()[1:]:
                    s = row[3].strip() if len(row) > 3 else ""
                    if s and s not in seen:
                        seen.add(s)
                        result.append(s)
            except Exception:
                pass
        for tab_key, subj_col in (("lectures", 1), ("assignments", 0), ("summaries", 0), ("booklets", 0), ("exams", 0)):
            for row in get_tab_data(tab_key):
                s = safe_get(row, subj_col)
                if s and s not in seen:
                    seen.add(s)
                    result.append(s)
        return result
    except Exception as e:
        log_error(f"get_subjects: {e}")
        return []


def get_lecture_subjects():
    try:
        seen, result = set(), []
        for r in get_tab_data("lectures"):
            s = safe_get(r, 1)
            if s and s not in seen:
                seen.add(s)
                result.append(s)
        return result
    except Exception:
        return []


def get_rooms(building):
    try:
        if not rooms_sheet:
            return []
        rows = rooms_sheet.get_all_values()[1:]
        return [r[1].strip() for r in rows if len(r) > 1 and r[0].strip() == building and r[1].strip()]
    except Exception:
        return []


def get_subject_doctor(subject):
    try:
        if not rooms_sheet:
            return ""
        rows = rooms_sheet.get_all_values()[1:]
        for r in rows:
            if len(r) > 3 and r[3].strip() == subject and r[2].strip():
                return r[2].strip()
        return ""
    except Exception:
        return ""


def get_subjects_with_doctors():
    try:
        if not rooms_sheet:
            return {}
        result = {}
        rows = rooms_sheet.get_all_values()[1:]
        for r in rows:
            doctor = r[2].strip() if len(r) > 2 else ""
            subject = r[3].strip() if len(r) > 3 else ""
            if subject:
                if subject not in result:
                    result[subject] = []
                if doctor and doctor not in result[subject]:
                    result[subject].append(doctor)
        return result
    except Exception:
        return {}
