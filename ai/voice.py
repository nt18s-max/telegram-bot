"""
voice.py — تفريغ التسجيلات الصوتية عبر Whisper API (من خلال OpenRouter).
"""

import requests as _requests

import config
from ai.providers import AI_PROVIDERS
from logging_utils import log_error


def transcribe_voice(bot, file_id: str, lang: str = "ar") -> str:
    """تفريغ بصمة صوتية إلى نص باستخدام موديل Whisper على OpenRouter."""
    openrouter_key = None
    for p in AI_PROVIDERS:
        if p.get("provider") == "openrouter":
            openrouter_key = p.get("api_key")
            break

    if not openrouter_key:
        return None

    try:
        file_info = bot.get_file(file_id)
        file_path = file_info.file_path
        file_url = f"https://api.telegram.org/file/bot{config.STUDY_BOT_TOKEN}/{file_path}"
        response = _requests.get(file_url, timeout=30)
        if response.status_code != 200:
            log_error(f"فشل تحميل الملف الصوتي من تيليجرام: {response.status_code}")
            return None

        headers = {"Authorization": f"Bearer {openrouter_key}"}
        files = {
            "file": (file_path, response.content),
            "model": (None, "whisper-1"),
            "language": (None, lang),
        }
        resp = _requests.post(
            "https://openrouter.ai/api/v1/audio/transcriptions",
            headers=headers,
            files=files,
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("text", "").strip()
        else:
            log_error(f"Whisper error: {resp.status_code} {resp.text}")
            return None
    except Exception as e:
        log_error(f"transcribe_voice: {e}")
        return None
