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

    # ---- 汇总表（加了预测列）----
    html += """
    <h3>📋 预测汇总</h3>
    <table border='1' cellpadding='5' cellspacing='0'
           style='border-collapse:collapse;width:100%;font-size:12px'>
    <tr style='background:#2c3e50;color:#fff'>
      <th>时间</th><th>赛事</th><th>对阵</th>
      <th>预测</th><th>比分</th>
      <th>市场赔率</th><th>公平赔率</th>
      <th>信心</th><th>风险</th>
    </tr>
    """
    for m in analyzed:
        t = m["time"].strftime("%m/%d %H:%M") if m["time"] else "?"
        league = m.get("league", "?")
        matchup = f"{m['home']} vs {m['away']}"
        pred_result = m["pred_result"]
        pred_score = m.get("pred_score", "-")

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

        # 预测结果加色
        if "主胜" in pred_result:
            pred_color = "#27ae60"
        elif "客胜" in pred_result:
            pred_color = "#e74c3c"
        else:
            pred_color = "#f39c12"

        html += f"""
        <tr>
          <td>{t}</td><td>{league}</td><td>{matchup}</td>
          <td style='color:{pred_color};font-weight:bold'>{pred_result}</td>
          <td>{pred_score}</td>
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
            html += f"大2.5: {m['prob_over']}%<br>"
        else:
            html += f"胜率: 主{m['prob_home']}% / 客{m['prob_away']}%<br>"

        if m.get("form_home") or m.get("form_away"):
            hf = m.get("form_home", "-")
            af = m.get("form_away", "-")
            html += f"近期: {m['home']} {hf} | {m['away']} {af}<br>"
        else:
            html += f"近期: 无战绩数据<br>"

        html += f"信心: {'⭐'*m['confidence']} {m['confidence']}/10 | 风险: {m['risk']}"
        if m["ev"] > 0.03:
            html += f" | EV+{m['ev']*100:.1f}%"
        html += "</p><hr>"

    html += "<p style='color:#999;font-size:12px'>⚠️ 仅供研究参考，不构成投注建议</p>"
    return html


def _empty_html(window_str: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""
    <h2>📊 比赛预测报告</h2>
    <p>窗口：{window_str}</p>
    <p style='color:#888'>生成：{now}</p>
    <hr>
    <p>❌ 今日无比赛数据</p>
    """


def push_report(analyzed: list | None, window_str: str, pushplus_token: str):
    if not pushplus_token:
        print("[PushPlus] 未配置 Token")
        return

    if analyzed is None:
        html = _empty_html(window_str)
    else:
        html = _build_html(analyzed, window_str)

    try:
        r = requests.post(
            "http://www.pushplus.plus/send",
            json={
                "token": pushplus_token,
                "title": "📊 今日比赛预测",
                "content": html,
                "template": "html",
            },
            timeout=10,
        )
        result = r.json()
        if result.get("code") == 200:
            print("[PushPlus] ✅ 微信推送成功")
        else:
            print(f"[PushPlus] ❌ {result}")
    except Exception as e:
        print(f"[PushPlus] ❌ {e}")