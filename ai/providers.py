import logging

import requests as _requests

from logging_utils import log_error

logger = logging.getLogger("StudyTestBot")

AI_PROVIDERS: list = []


def load_ai_providers():
    from sheets.connection import spreadsheet
    global AI_PROVIDERS
    AI_PROVIDERS = []
    try:
        sheet_providers = spreadsheet.worksheet("ai_providers")
        rows = sheet_providers.get_all_values()
        if not rows:
            logger.info("⚠️ لا توجد صفحة ai_providers أو فارغة.")
            return
        for row in rows[1:]:
            if len(row) < 5:
                continue
            order = row[0].strip()
            provider = row[1].strip().lower()
            api_key = row[2].strip()
            model = row[3].strip().lower()
            enabled = row[4].strip().upper() == "TRUE"
            if not enabled or not api_key:
                continue
            if provider not in ("gemini", "openrouter"):
                continue

            if model == "auto":
                if provider == "gemini":
                    model = "gemini-2.0-flash"
                elif provider == "openrouter":
                    model = "openrouter/free"

            if provider == "gemini":
                AI_PROVIDERS.append({
                    "order": int(order) if order.isdigit() else 999,
                    "provider": "gemini",
                    "api_key": api_key,
                    "model": model,
                    "name": f"Gemini {model}",
                    "icon": "✨",
                })
            elif provider == "openrouter":
                AI_PROVIDERS.append({
                    "order": int(order) if order.isdigit() else 999,
                    "provider": "openrouter",
                    "api_key": api_key,
                    "model": model,
                    "name": "OpenRouter Auto" if model == "openrouter/free" else model.split('/')[-1].replace(':free', ''),
                    "icon": "🎯",
                })
        AI_PROVIDERS.sort(key=lambda x: x["order"])
        logger.info(f"✅ تم تحميل {len(AI_PROVIDERS)} مزود AI")
        for p in AI_PROVIDERS:
            logger.info(f"   {p['order']}: {p['provider']} - {p['model']}")
    except Exception as e:
        logger.warning(f"لم يتم العثور على صفحة ai_providers أو خطأ: {e}")
        AI_PROVIDERS = []


def call_gemini(provider, uid, user_text, system_prompt):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{provider['model']}:generateContent?key={provider['api_key']}"
        payload = {
            "contents": [{"parts": [{"text": system_prompt + "\n\n" + user_text}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
        }
        resp = _requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return text, {"id": provider["model"], "name": provider["name"], "icon": provider["icon"]}
        else:
            log_error(f"Gemini error {resp.status_code}: {resp.text[:200]}", uid)
            return None, None
    except Exception as e:
        log_error(f"Gemini exception: {e}", uid)
        return None, None


def call_openrouter(provider, uid, messages, system_prompt):
    headers = {
        "Authorization": f"Bearer {provider['api_key']}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/study_bot",
        "X-Title": "Study Bot",
    }
    payload = {
        "model": provider["model"],
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "max_tokens": 1024,
        "temperature": 0.7,
    }
    try:
        resp = _requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=payload, timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            return content, {"id": provider["model"], "name": provider["name"], "icon": provider["icon"]}
        else:
            log_error(f"OpenRouter {resp.status_code} {resp.text[:200]} on {provider['model']}", uid)
            return None, None
    except Exception as e:
        log_error(f"OpenRouter exception: {e}", uid)
        return None, None


def ai_reset_model():
    load_ai_providers()
