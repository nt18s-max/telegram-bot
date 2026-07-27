"""
help_materials.py — عرض ورفع التعليمات (تعليمات المستخدم / تعليمات الأدمن).
"""

from files_io import send_files_with_text
from sheets.help_repo import get_help_materials, save_help_material


def send_help_materials(bot, chat_id, uid, audience_filter):
    """عرض التعليمات المحفوظة حسب الفئة المستهدفة ('user' أو 'admin')."""
    mats = get_help_materials()
    mats = [m for m in mats if m.get("audience") == audience_filter]
    if not mats:
        bot.send_message(chat_id, "📭 لا توجد تعليمات حالياً.")
        return

    title = "📖 تعليمات المستخدم" if audience_filter == "user" else "📖 تعليمات الأدمن"
    bot.send_message(chat_id, f"*{title}*", parse_mode="Markdown")
    for m in mats:
        send_files_with_text(bot, chat_id, m.get("note") or None, [m["file_id"]] if m.get("file_id") else [])
