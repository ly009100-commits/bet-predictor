"""
🏆 比赛预测系统 - PushPlus 微信推送版
"""
import os, sys
import numpy as np
import pandas as pd
import requests
from datetime import datetime
from pathlib import Path
from scipy.stats import poisson

ODDS_KEY = os.environ["ODDS_API_KEY"]
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN", "")

LEAGUES = {
    "soccer_epl": "🏴 英超",
    "soccer_spain_la_liga": "🇪🇸 西甲",
    "soccer_italy_serie_a": "🇮🇹 意甲",
    "soccer_germany_bundesliga": "🇩🇪 德甲",
    "soccer_france_ligue_one": "🇫🇷 法甲",
    "soccer_uefa_champs_league": "⭐ 欧冠",
}


def fetch_matches():
    all_data = []
    for sport, name in LEAGUES.items():
        try:
            r = requests.get(
                f"https://api.the-odds-api.com/v4/sports/{sport}/odds",
                params={"apiKey": ODDS_KEY, "regions": "eu",
                        "markets": "h2h,totals", "oddsFormat": "decimal"},
                timeout=15,
            )
            if r.status_code != 200:
                continue
            print(f"  {name}: {len(r.json())} 场")

            for g in r.json():
                h2h = {}
                to = tu = None
                for bk in g.get("bookmakers", []):
                    for m in bk.get("markets", []):
                        if m["key"] == "h2h" and not h2h:
                            h2h = {o["name"]: o["price"] for o in m["outcomes"]}
                        if m["key"] == "totals" and to is None:
                            for o in m["outcomes"]:
                                if o.get("point") == 2.5:
                                    if o["name"] == "Over": to = o["price"]
                                    else: tu = o["price"]

                if h2h.get(g["home_team"]) and h2h.get(g["away_team"]):
                    all_data.append({
                        "league": name,
                        "home": g["home_team"],
                        "away": g["away_team"],
                        "time": g["commence_time"][:16],
                        "o1": h2h[g["home_team"]],
                        "oX": h2h.get("Draw"),
                        "o2": h2h[g["away_team"]],
                        "o_over": to, "o_under": tu,
                    })
        except Exception as e:
            print(f"  {name}: {e}")
    return pd.DataFrame(all_data)


def predict(row):
    imp1, impX, imp2 = 1 / row["o1"], 1 / row["oX"], 1 / row["o2"]
    total = imp1 + impX + imp2
    ph, pd_, pa = imp1 / total, impX / total, imp2 / total
    hxg = 1.35 * (ph + 0.5 * pd_) * 1.25
    axg = 1.35 * (pa + 0.5 * pd_) * 0.85

    hp = np.array([poisson.pmf(i, hxg) for i in range(10)])
    ap = np.array([poisson.pmf(i, axg) for i in range(10)])
    m = np.outer(hp, ap)

    hw = float(np.sum(np.tril(m, -1)))
    dr = float(np.sum(np.diag(m)))
    aw = float(np.sum(np.triu(m, 1)))
    g = np.fromfunction(lambda i, j: i + j, (10, 10), dtype=int)
    o25 = float(np.sum(m[g > 2.5]))
    idx = np.unravel_index(np.argmax(m), m.shape)

    return {
        "hw": round(hw * 100, 1), "dr": round(dr * 100, 1), "aw": round(aw * 100, 1),
        "o25": round(o25 * 100, 1),
        "score": f"{idx[0]}-{idx[1]}",
        "pick": "主胜" if hw > aw and hw > dr else ("客胜" if aw > hw else "平局"),
    }


def kelly(prob, odds, frac=0.25):
    b = odds - 1
    p = prob / 100
    full = (b * p - (1 - p)) / b
    return round(full * frac * 100, 2) if full > 0 else None


def push_wechat(title, content):
    """PushPlus 微信推送"""
    if not PUSHPLUS_TOKEN:
        print("[PushPlus] 未配置 Token，跳过推送")
        return
    try:
        r = requests.post(
            "http://www.pushplus.plus/send",
            json={"token": PUSHPLUS_TOKEN, "title": title, "content": content,
                  "template": "html"},
            timeout=10,
        )
        result = r.json()
        if result.get("code") == 200:
            print(f"[PushPlus] ✅ 微信推送成功")
        else:
            print(f"[PushPlus] ❌ {result}")
    except Exception as e:
        print(f"[PushPlus] ❌ {e}")


def build_html(pred_df, bets_df):
    """生成 HTML 格式报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = f"""
    <h2>📊 比赛预测报告</h2>
    <p style='color:#888'>{now}</p>
    <hr>
    """

    if not bets_df.empty:
        html += "<h3>💰 价值投注推荐</h3><ul>"
        for _, r in bets_df.head(5).iterrows():
            html += (
                f"<li><b>{r['home']} vs {r['away']}</b><br>"
                f"{r['bet']} @{r['odds']:.2f} | "
                f"胜率 {r['prob']:.1f}% | EV +{r['ev']*100:.1f}% | "
                f"凯利 {r['kelly']:.1f}%</li>"
            )
        html += "</ul><hr>"

    html += "<h3>⚽ 今日所有预测</h3><ul>"
    for _, r in pred_df.iterrows():
        html += (
            f"<li><b>{r['home']}</b> vs <b>{r['away']}</b> "
            f"<span style='color:#888'>({r['league']})</span><br>"
            f"预测: {r['pick']} | 比分: {r['score']}<br>"
            f"主{r['hw']}% / 平{r['dr']}% / 客{r['aw']}% | "
            f"大2.5: {r['o25']}%<br>"
            f"赔率: {r['o1']}/{r['oX']}/{r['o2']}</li>"
    )
    html += "</ul>"

    html += "<p style='color:#999;font-size:12px'>⚠️ 仅供研究参考，不构成投注建议</p>"
    return html


def main():
    print(f"\n{'='*60}")
    print(f"🏆 比赛预测 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    # 1. 采集
    print("📥 [1/3] 拉取赔率数据...")
    df = fetch_matches()
    if df.empty:
        print("❌ 无数据")
        push_wechat("❌ 比赛预测失败", "<p>今日无比赛数据</p>")
        return
    print(f"✅ 共 {len(df)} 场\n")

    # 2. 预测
    print("🧠 [2/3] 泊松模型预测...")
    results = []
    for _, r in df.iterrows():
        try:
            results.append({**r.to_dict(), **predict(r)})
        except:
            pass
    pred = pd.DataFrame(results)
    print(f"✅ {len(pred)} 场预测完成\n")

    # 3. 凯利筛选
    print("💰 [3/3] 凯利公式筛选...")
    bets = []
    for _, r in pred.iterrows():
        for t, o, p in [("主胜", r.get("o1"), r.get("hw")),
                         ("客胜", r.get("o2"), r.get("aw")),
                         ("大2.5", r.get("o_over"), r.get("o25"))]:
            if o and p:
                k = kelly(p, o)
                ev = (p / 100) * o - 1
                if k and ev > 0.02:
                    bets.append({**r, "bet": t, "odds": o, "prob": p, "ev": ev, "kelly": k})
    bets_df = pd.DataFrame(bets)
    if not bets_df.empty:
        bets_df = bets_df.sort_values("ev", ascending=False)
    print(f"✅ 发现 {len(bets_df)} 个价值机会\n")

    # 终端输出
    for _, r in pred.iterrows():
        print(f"  {r['home']} vs {r['away']} → {r['pick']} {r['score']}")
    if not bets_df.empty:
        print(f"\n💎 价值投注:")
        for _, r in bets_df.head(5).iterrows():
            print(f"  {r['bet']} @{r['odds']:.2f} EV+{r['ev']*100:.1f}%")

    # 微信推送
    html = build_html(pred, bets_df)
    push_wechat("📊 今日比赛预测", html)

    # 保存 CSV
    Path("results").mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    pred.to_csv(f"results/pred_{ts}.csv", index=False)
    print(f"\n✅ 完成！")


if __name__ == "__main__":
    main()