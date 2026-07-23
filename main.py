"""
main.py —— 比赛预测系统入口
"""
import os, sys
from datetime import datetime
from pathlib import Path

from config import *
from time_utils import calculate_time_window
from data_fetcher import fetch_all
from analyzer import analyze_all
from reporter import push_report


def main():
    print(f"\n{'='*50}")
    print(f"🏆 比赛预测 {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    # 读取 API Keys
    odds_key   = os.environ.get("ODDS_API_KEY", "")
    foot_key   = os.environ.get("API_FOOTBALL_KEY", "")
    basket_key = os.environ.get("API_BASKETBALL_KEY", foot_key)   # 同账号
    nfl_key    = os.environ.get("API_NFL_KEY", foot_key)          # 同账号

    if not odds_key:
        print("❌ 未设置 ODDS_API_KEY")
        sys.exit(1)

    # 时间窗口
    start, end, window_str = calculate_time_window()
    print(f"⏰ 预测窗口: {window_str}\n")

    # 数据采集
    matches = fetch_all(odds_key, foot_key, basket_key, nfl_key, start, end)
    if not matches:
        msg = "今日无比赛数据"
        print(msg)
        push_report(None, window_str, os.environ.get("PUSHPLUS_TOKEN", ""))
        return

    # 分析
    print(f"🧠 开始分析 {len(matches)} 场比赛...")
    analyzed = analyze_all(matches)
    print(f"✅ {len(analyzed)} 场分析完成\n")

    # 推送
    push_report(analyzed, window_str, os.environ.get("PUSHPLUS_TOKEN", ""))


if __name__ == "__main__":
    main()