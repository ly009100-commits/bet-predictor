"""
reporter.py —— 报告生成 + PushPlus 微信推送
"""
import requests
from datetime import datetime


def _build_html(analyzed: list, window_str: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = f"""
    <h2>📊 比赛预测报告</h2>
    <p>窗口：{window_str}</p>
    <p style='color:#888'>生成：{now}</p>
    <hr>
    """

    # ---- 汇总表 ----
    html += """
    <h3>📋 预测汇总</h3>
    <table border='1' cellpadding='5' cellspacing='0'
           style='border-collapse:collapse;width:100%;font-size:12px'>
    <tr style='background:#2c3e50;color:#fff'>
      <th>时间</th><th>赛事</th><th>对阵</th>
      <th>市场赔率</th><th>公平赔率</th>
      <th>信心</th><th>风险</th>
    </tr>
    """
    for m in analyzed:
        t = m["time"].strftime("%m/%d %H:%M") if m["time"] else "?"
        league = m.get("league", "?")
        matchup = f"{m['home']} vs {m['away']}"

        if m["has_draw"]:
            base = f"{m['o1']:.2f}/{m['oX']:.2f}/{m['o2']:.2f}"
            fair = f"{m['fair_home']:.2f}/{m['fair_draw']:.2f}/{m['fair_away']:.2f}" if m.get("fair_draw") else "-"
        else:
            base = f"{m['o1']:.2f}/{m['o2']:.2f}"
            fair = f"{m['fair_home']:.2f}/{m['fair_away']:.2f}"

        conf_stars = "⭐" * m["confidence"]
        ev_tag = ""
        if m["ev"] > 0.05:
            ev_tag = f" 🔥EV+{m['ev']*100:.0f}%"

        html += f"""
        <tr>
          <td>{t}</td><td>{league}</td><td>{matchup}</td>
          <td>{base}</td><td>{fair}</td>
          <td>{conf_stars} {m['confidence']}{ev_tag}</td>
          <td>{m['risk']}</td>
        </tr>"""
    html += "</table><hr>"

    # ---- 逐场详细分析 ----
    html += "<h3>🔍 逐场分析</h3>"
    for m in analyzed:
        t = m["time"].strftime("%m/%d %H:%M") if m["time"] else "?"
        league = m.get("league", "?")

        html += f"<p><b>{t} | {league}</b><br>"
        html += f"<b>{m['home']}</b> vs <b>{m['away']}</b><br>"

        html += f"预测: <b>{m['pred_result']}</b> | 比分: {m['pred_score']}<br>"
        if m["has_draw"]:
            html += f"胜率: 主{m['prob_home']}% / 平{m['prob_draw']}% / 客{m['prob_away']}%<br>"
            html += f"大