import config
from sheets.cache_utils import SafeCache
from sheets.connection import users_sheet

_cache = SafeCache("المستخدمين")


def _fetch_users_raw():
    rows = users_sheet.get_all_values()[1:]
    by_id = {}
    open_all = False
    admin_all = False
    empty_streak = 0

    for i, row in enumerate(rows, start=2):
        if not row or not any(c.strip() for c in row):
            empty_streak += 1
            if empty_streak >= 5:
                break
            continue
        empty_streak = 0

        name = row[config.COL_NAME].strip() if len(row) > config.COL_NAME else ""
        uid_str = row[config.COL_ID].strip().lstrip("'") if len(row) > config.COL_ID else ""

        def _flag(col):
            return (row[col].strip().upper() if len(row) > col else "FALSE") == "TRUE"

        if name == "الكل":
            if _flag(config.COL_ALLOWED):
                open_all = True
            if _flag(config.COL_ADMIN):
                admin_all = True
            continue

        if not uid_str.isdigit():
            continue

        uid = int(uid_str)
        by_id[uid] = {
            "row": i,
            "name": name,
            "phone": row[config.COL_PHONE].strip() if len(row) > config.COL_PHONE else "",
            "allowed": _flag(config.COL_ALLOWED),
            "admin": _flag(config.COL_ADMIN),
            "owner": _flag(config.COL_OWNER),
            "lang": "en" if _flag(config.COL_LANG_EN) else "ar",
            "log": _flag(config.COL_LOG),
            "ai_allowed": _flag(config.AI_ALLOWED_COL),
            "auto_publish": _flag(config.AUTO_PUBLISH_COL),
            "ai_switch": _flag(config.AI_SWITCH_COL),
        }

    return {"by_id": by_id, "open_all": open_all, "admin_all": admin_all}


def _load():
    return _cache.get_or_fetch(_fetch_users_raw)


def refresh_users_cache():
    return _cache.refresh(_fetch_users_raw)


def get_users():
    data = _load()
    if not data:
        return [], [], [], False, False, [], [], []

    by_id = data["by_id"]
    allowed = [u for u, r in by_id.items() if r["allowed"]]
    admins = [u for u, r in by_id.items() if r["admin"]]
    owners = [u for u, r in by_id.items() if r["owner"]]
    log_ids = [u for u, r in by_id.items() if r["log"]]
    ai_allowed = [u for u, r in by_id.items() if r["ai_allowed"]]
    auto_publish_uids = [u for u, r in by_id.items() if r["auto_publish"]]
    return allowed, admins, owners, data["open_all"], data["admin_all"], log_ids, ai_allowed, auto_publish_uids


def get_user_record(uid: int):
    data = _load()
    if not data:
        return None
    return data["by_id"].get(int(uid))


def _by_id() -> dict:
    data = _load()
    return data["by_id"] if data else {}


def get_owner_ids():
    return [u for u, r in _by_id().items() if r["owner"]]


def is_owner_id(uid) -> bool:
    rec = _by_id().get(int(uid))
    return bool(rec and rec["owner"])


def get_user_role(uid) -> str:
    rec = get_user_record(uid)
    data = _load()
    admin_all = data["admin_all"] if data else False
    if rec and rec["owner"]:
        return "owner"
    if admin_all or (rec and rec["admin"]):
        return "admin"
    return "user"


def get_ai_allowed_users():
    return [u for u, r in _by_id().items() if r["ai_allowed"]]


def is_ai_allowed(uid) -> bool:
    rec = _by_id().get(int(uid))
    return bool(rec and rec["ai_allowed"])


def get_all_registered_uids():
    data = _load()
    if not data:
        return []
    return list(data["by_id"].keys())


def get_log_user_ids() -> list:
    return [u for u, r in _by_id().items() if r["log"]]


def find_user_row_by_id(search_id):
    try:
        sid = str(search_id).strip()
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows, start=1):
            if len(row) > config.COL_ID and row[config.COL_ID].strip().lstrip("'") == sid:
                return i, row
        return None, None
    except Exception:
        return None, None


def find_user_row_by_phone(phone):
    import re
    try:
        pc = re.sub(r"[\s\-\+]", "", phone.strip())
        rows = users_sheet.get_all_values()
        for i, row in enumerate(rows, start=1):
            rp = re.sub(r"[\s\-\+]", "", row[config.COL_PHONE].strip() if len(row) > config.COL_PHONE else "")
            if not rp:
                continue
            if rp == pc or rp.endswith(pc) or pc.endswith(rp):
                return i, row
        return None, None
    except Exception:
        return None, None


def add_user_to_sheet(name, uid, auto=False, allowed=True) -> bool:
    try:
        display = f"🆕 {name}" if auto else name
        users_sheet.append_row(
            [display, "", uid, allowed, False, False, False, False, False, False, False, False],
            value_input_option="USER_ENTERED",
        )
        refresh_users_cache()
        return True
    except Exception:
        return False


def set_ai_allowed(uid, allowed: bool) -> bool:
    i, row = find_user_row_by_id(uid)
    if not row:
        return False
    users_sheet.update_cell(i, config.AI_ALLOWED_COL + 1, allowed)
    refresh_users_cache()
    return True


def set_user_auto_publish(uid, enabled: bool) -> bool:
    i, row = find_user_row_by_id(uid)
    if not row:
        return False
    users_sheet.update_cell(i, config.AUTO_PUBLISH_COL + 1, enabled)
    refresh_users_cache()
    return True


def set_user_ai_switch(uid, enabled: bool) -> bool:
    i, row = find_user_row_by_id(uid)
    if not row:
        return False
    users_sheet.update_cell(i, config.AI_SWITCH_COL + 1, enabled)
    refresh_users_cache()
    return True


def save_user_lang(uid, lang: str) -> bool:
    i, row = find_user_row_by_id(uid)
    if not row:
        return False
    users_sheet.update_cell(i, config.COL_LANG_EN + 1, lang == "en")
    refresh_users_cache()
    return True


def set_user_role(uid, allowed: bool, admin: bool, owner: bool) -> bool:
    i, row = find_user_row_by_id(uid)
    if not row:
        return False
    users_sheet.update(f"D{i}:F{i}", [[allowed, admin, owner]])
    refresh_users_cache()
    return True
