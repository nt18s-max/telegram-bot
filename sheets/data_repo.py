from sheets.cache_utils import SafeCache
from sheets.connection import (
    lectures_sheet, booklets_sheet, summaries_sheet,
    assignments_sheet, exams_sheet, targets_sheet,
)

TAB_SHEETS = {
    "lectures":    lectures_sheet,
    "booklets":    booklets_sheet,
    "summaries":   summaries_sheet,
    "assignments": assignments_sheet,
    "exams":       exams_sheet,
    "targets":     targets_sheet,
}

_caches = {key: SafeCache(key) for key in TAB_SHEETS}


def _fetch_tab(tab_key: str):
    ws = TAB_SHEETS[tab_key]
    rows = ws.get_all_values()[1:]
    return [r for r in rows if any(c.strip() for c in r if c)]


def get_tab_data(tab_key: str) -> list:
    cache = _caches.get(tab_key)
    if cache is None:
        return []
    result = cache.get_or_fetch(lambda: _fetch_tab(tab_key))
    return result or []


def refresh_data_cache(tab_key: str = None):
    keys = [tab_key] if tab_key else list(_caches.keys())
    for k in keys:
        if k in _caches:
            _caches[k].refresh(lambda kk=k: _fetch_tab(kk))
