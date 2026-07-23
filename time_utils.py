"""
time_utils.py —— 时间窗口计算（北京时间 UTC+8）
"""
from datetime import datetime, timedelta
from config import BEIJING_TZ


def calculate_time_window():
    """
    返回 24 小时窗口
    非整点取下一个整点
    """
    now = datetime.now(BEIJING_TZ)

    if now.minute == 0 and now.second == 0:
        start = now
    else:
        start = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    end = start + timedelta(hours=24)

    window_str = (
        f"{start.strftime('%m/%d %H:00')} → "
        f"{end.strftime('%m/%d %H:00')} (北京时间)"
    )
    return start, end, window_str