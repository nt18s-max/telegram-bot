import time


class SafeCache:
    def __init__(self, name: str):
        self.name = name
        self.data = None
        self.ts = 0.0

    def get_or_fetch(self, fetch_fn):
        if self.data is not None:
            return self.data
        return self.refresh(fetch_fn)

    def refresh(self, fetch_fn):
        from logging_utils import log_error

        try:
            fresh_data = fetch_fn()
        except Exception as e:
            log_error(
                f"⚠️ فشل تحديث كاش «{self.name}»\n"
                f"تم الاحتفاظ بآخر بيانات معروفة بدون أي حذف.\n"
                f"سبب الفشل: {e}"
            )
            return self.data

        self.data = fresh_data
        self.ts = time.time()
        return self.data

    def is_loaded(self) -> bool:
        return self.data is not None
