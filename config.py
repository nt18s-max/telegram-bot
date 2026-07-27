import os
import pytz
from dotenv import load_dotenv

load_dotenv()

YEMEN_TZ = pytz.timezone("Asia/Aden")

STUDY_BOT_TOKEN = os.environ.get("STUDY_TEST_TOKEN", "")
SHEET_KEY       = os.environ.get("SHEET_KEY", "")
BOT_USERNAME    = os.environ.get("BOT_USERNAME", "")

LOG_BOT_TOKEN = os.environ.get("STUDY_BOT_LOG_TOKEN", "")

INTERNAL_PORT     = int(os.environ.get("INTERNAL_PORT", 10001))
INTERNAL_SECRET   = os.environ.get("INTERNAL_SECRET", "study_bot_secret_2025")

COL_NAME         = 0
COL_PHONE        = 1
COL_ID           = 2
COL_ALLOWED      = 3
COL_ADMIN        = 4
COL_OWNER        = 5
COL_LANG_EN      = 6
COL_LOG          = 7
COL_BOT2         = 8
AI_ALLOWED_COL   = 9
AUTO_PUBLISH_COL = 10
AI_SWITCH_COL    = 11
