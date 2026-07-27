"""
files_io.py — دوال إرسال الملفات بالنص والوسائط المترابطة عبر Telegram Bot API.
"""

from logging_utils import log_error


def _try_send_file(bot, chat_id, fid, caption=None, parse_mode=None, reply_markup=None):
    """يحاول إرسال الملف (صورة، فيديو، صوت، بصمة صوتية، أو مستند)."""
    for sender in [
        bot.send_photo,
        bot.send_video,
        bot.send_audio,
        bot.send_voice,
        bot.send_document,
    ]:
        try:
            sender(chat_id, fid, caption=caption, parse_mode=parse_mode, reply_markup=reply_markup)
            return True
        except Exception:
            continue
    return False


def send_files_with_text(bot, chat_id, text, fids, reply_markup=None):
    """إرسال النص مع قائمة الملفات (ملف واحد مع شرح، أو عدة ملفات يليها النص)."""
    if not fids:
        if text:
            bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=reply_markup)
        return

    cap = text[:1024] if text else None
    parse = "Markdown" if cap else None

    if len(fids) == 1:
        ok = _try_send_file(bot, chat_id, fids[0], caption=cap, parse_mode=parse, reply_markup=reply_markup)
        if not ok and text:
            bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=reply_markup)
        return

    for fid in fids:
        _try_send_file(bot, chat_id, fid)

    if text:
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=reply_markup)
