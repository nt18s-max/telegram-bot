from datetime import datetime, timedelta

import config

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def safe_get(row, idx):
    v = row[idx].strip() if len(row) > idx else ""
    return v.lstrip("'").strip() if v else ""


def normalize_digits(text: str) -> str:
    return text.translate(ARABIC_DIGITS)


def parse_date(d: str) -> str:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(d.strip(), fmt).strftime("%d/%m/%Y")
        except Exception:
            continue
    return d.strip()


def is_valid_date(d: str) -> bool:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            datetime.strptime(d.strip(), fmt)
            return True
        except Exception:
            continue
    return False


def smart_date_from_day(day: int) -> str:
    now = datetime.now(config.YEMEN_TZ)
    if day <= now.day:
        try:
            return now.replace(day=day).strftime("%d/%m/%Y")
        except Exception:
            return now.strftime("%d/%m/%Y")
    first = now.replace(day=1)
    last_month = first - timedelta(days=1)
    try:
        return last_month.replace(day=day).strftime("%d/%m/%Y")
    except Exception:
        return now.strftime("%d/%m/%Y")


def parse_smart_date(raw: str):
    text = normalize_digits(raw.strip())
    if is_valid_date(text):
        return parse_date(text)
    if text.isdigit():
        d = int(text)
        if 1 <= d <= 31:
            return smart_date_from_day(d)
    return None
