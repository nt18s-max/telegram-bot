import json
import logging

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import config

logger = logging.getLogger("StudyTestBot")

_SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


try:
    import os
    _gcreds_raw = os.environ.get("GOOGLE_CREDENTIALS")
    _creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(_gcreds_raw), _SCOPE)
    client = gspread.authorize(_creds)
    spreadsheet = client.open_by_key(config.SHEET_KEY)

    users_sheet             = spreadsheet.worksheet("المستخدمين")
    help_sheet               = spreadsheet.worksheet("المساعدة")
    bot_texts_sheet           = spreadsheet.worksheet("bot_texts")
    keyboard_buttons_sheet     = spreadsheet.worksheet("keyboard_buttons")
    inline_buttons_sheet        = spreadsheet.worksheet("inline_buttons")
    ai_providers_sheet           = spreadsheet.worksheet("ai_providers")

    lectures_sheet     = spreadsheet.worksheet("المحاضرات")
    booklets_sheet       = spreadsheet.worksheet("الملازم")
    summaries_sheet        = spreadsheet.worksheet("الملخصات")
    assignments_sheet         = spreadsheet.worksheet("التكاليف")
    exams_sheet                  = spreadsheet.worksheet("نماذج الاختبارات")
    targets_sheet                   = spreadsheet.worksheet("Targets")

    try:
        rooms_sheet = spreadsheet.worksheet("القاعات والمواد")
    except Exception:
        try:
            rooms_sheet = spreadsheet.worksheet("القاعات")
        except Exception:
            rooms_sheet = None

    CONNECTED = True
    logger.info("✅ Google Sheets متصل — كل الصفحات فُتحت بنجاح")

except Exception as _e:
    logger.critical(f"❌ فشل الاتصال الأولي بـ Google Sheets: {_e}")
    CONNECTED = False
    client = spreadsheet = None
    users_sheet = help_sheet = bot_texts_sheet = None
    keyboard_buttons_sheet = inline_buttons_sheet = ai_providers_sheet = None
    lectures_sheet = booklets_sheet = summaries_sheet = None
    assignments_sheet = exams_sheet = targets_sheet = None
    rooms_sheet = None
