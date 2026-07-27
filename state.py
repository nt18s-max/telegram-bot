"""
state.py — إدارة حالات المستخدمين المؤقتة والتراكمية في الذاكرة.
"""

user_state = {}
pending_files = {}
_temp_admin_actions = {}
_notification_cooldowns = {}


def clear_user_state(uid: int):
    """تصفير حالة المستخدم وتفريغ ملفاته المعلقة."""
    user_state.pop(uid, None)
    pending_files.pop(uid, None)


def get_user_step(uid: int) -> str:
    """إرجاع الخطوة الحالية للمستخدم."""
    st = user_state.get(uid)
    if isinstance(st, dict):
        return st.get("step", "")
    return ""
