"""
time_utils.py —— 时间窗口计算（北京时间 UTC+8）
窗口长度可通过环境变量 WINDOW_HOURS 配置，默认 24
"""
import os
from datetime import datetime, timedelta
from config import BEIJING_TZ


def calculate_time_window():
    """返回 24 小时窗口（可通过 WINDOW_HOURS 扩大）"""
    window_hours = int(os.environ.get("WINDOW_HOURS", "24"))

    now = datetime.now(BEIJING_TZ)

    if now.minute == 0 and now.second == 0:
        start = now
    else:
        start = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    end = start + timedelta(hours=window_hours)

    start_naive = start.replace(tzinfo=None)
    end_naive   = end.replace(tzinfo=None)

    window_str = (
        f"{start.strftime('%m/%d %H:00')} → "
        f"{end.strftime('%m/%d %H:00')} "
        f"(北京时间, {window_hours}h窗口)"
    )
    return start_naive, end_naive, window_str