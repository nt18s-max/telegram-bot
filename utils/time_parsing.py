import re


def _time12_to_24(t):
    if not t:
        return t
    t = str(t).strip()
    t = t.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    t = re.sub(r'من\s*الساعة|من\s+|الساعة\s*|إلى\s*|الى\s*|حتى\s*|\b(am|pm|ص|م)\b',
               ' ', t, flags=re.IGNORECASE)
    t = re.sub(r'[–—]', '-', t)
    t = t.strip()

    nums = re.findall(r'\d{1,2}(?:[.:]\d{2})?', t)

    def _h24(s):
        s = str(s).replace(':', '.').replace(',', '.')
        if '.' in s:
            h, m = int(s.split('.')[0]), int(s.split('.')[1])
        else:
            h, m = int(s), 0
        if 1 <= h <= 7:
            h += 12
        return h, m

    try:
        if len(nums) >= 2:
            h1, m1 = _h24(nums[0])
            h2, m2 = _h24(nums[1])
            return f"{h1:02d}:{m1:02d} - {h2:02d}:{m2:02d}"
        elif len(nums) == 1:
            h1, m1 = _h24(nums[0])
            return f"{h1:02d}:{m1:02d}"
        else:
            return t
    except Exception:
        return t


def normalize_time(t):
    return _time12_to_24(t)


def parse_time_range(t):
    t = normalize_time(t)
    parts = re.split(r'\s*-\s*', t)
    if len(parts) != 2:
        return None, None

    def mins(s):
        s = s.strip()
        h, mm = s.split(":") if ":" in s else (s, "0")
        return int(h) * 60 + int(mm)

    try:
        return mins(parts[0]), mins(parts[1])
    except Exception:
        return None, None
