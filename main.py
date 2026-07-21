"""
🏆 每日比赛预测系统 - 手动触发版
"""
import os, json, sys
import numpy as np
import pandas as pd
import requests
from datetime import datetime
from pathlib import Path
from scipy.stats import poisson

# ===== 配置 =====
ODDS_KEY = os.environ["ODDS_API_KEY"]
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")

LEAGUES = {
    "soccer_epl": "🏴 英超",
    "soccer_spain_la_liga": "🇪🇸 西甲",
    "soccer_italy_serie_a": "🇮🇹 意甲",
    "soccer_germany_bundesliga": "🇩🇪 德甲",
    "soccer_france_ligue_one": "🇫🇷 法甲",
    "soccer_uefa_champs_league": "⭐ 欧冠",
}


def fetch_matches():
    """拉取赔率数据"""
    all_data = []
    for sport, name in LEAGUES.items():
        try:
            r = requests.get(
                f"https://api.the-odds-api.com/v4/sports/{sport}/odds",
                params={
                    "apiKey": ODDS_KEY,
                    "regions": "eu",
                    "markets": "h2h,totals",
                    "oddsFormat": "decimal",
                },
                timeout=15,
            )
            if r.status_code != 200:
                continue
            print(f"  {name}: {len(r.json())} 场 (剩余 {r.headers.get('x-requests-remaining','?')})")

            for g in r.json():
                h2h = {}
                totals_over = totals_under = None
                for bk in g.get("bookmakers", []):
                    for m in bk.get("markets", []):
                        if m["key"] == "h2h" and not h2h:
                            h2h = {o["name"]: o["price"] for o in m["outcomes"]}
                        if m["key"] == "totals" and totals_over is None:
                            for o in m["outcomes"]:
                                if o.get("point") == 2.5:
                                    if o["name"] == "Over":
                                        totals_over = o["price"]
                                    else:
                                        totals_under = o["price"]

                if h2h.get(g["home_team"]) and h2h.get(g["away_team"]):
                    all_data.append({
                        "league": name,
                        "home": g["home_team"],
                        "away": g["away_team"],
                        "time": g["commence_time"][:16],
                        "o1": h2h[g["home_team"]],
                        "oX": h2h.get("Draw"),
                        "o2": h2h[g["away_team"]],
                        "o_over": totals_over,
                        "o_under": totals_under,
                    })
        except Exception as e:
            print(f"  {name}: {e}")
    return pd.DataFrame(all_data)


def predict(row):
    """泊松预测"""
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
        "pick": "🏠主胜" if hw > aw and hw > dr else ("🚌客胜" if aw > hw else "🤝平局"),
        "hxg": round(hxg, 2), "axg": round(axg, 2),
    }


def kelly(prob, odds, frac=0.25):
    b = odds - 1
    p = prob / 100
    q = 1 - p
    full = (b * p - q) / b
    return round(full * frac * 100, 2) if full > 0 else None


def find_bets(df):
    bets = []
    for _, r in df.iterrows():
        for t, o, p in [("主胜", r.get("o1"), r.get("hw")),
                         ("客胜", r.get("o2"), r.get("aw")),
                         ("大2.5", r.get("o_over"), r.get("o25"))]:
            if o and p:
                k = kelly(p, o)
                ev = (p / 100) * o - 1
                if k and ev > 0.02:
                    bets.append({**r, "bet": t, "odds": o, "prob": p, "ev": ev, "kelly": k})
    out = pd.DataFrame(bets)
    return out.sort_values("ev", ascending=False) if not out.empty else out


def send_tg(text):
    if not TG_TOKEN or not TG_CHAT:
        print("[TG] 未配置")
        return
    r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": TG_CHAT, "text": text, "parse_mode": "HTML"}, timeout=10)
    print(f"[TG] {'✅' if r.ok else '❌'}")


def build_msg(pred_df, bets_df):
    now = datetime.now().strftime("%m-%d %H:%M")
    lines = [f"<b>📊 每日比赛预测</b> ({now})\n"]

    if not bets_df.empty:
        lines.append("<b>💰 价值投注</b>")
        for _, r in bets_df.head(5).iterrows():
            lines.append(
                f"• {r['home']} vs {r['away']}\n"
                f"  <b>{r['bet']}</b> @{r['odds']:.2f}  "
                f"胜率{r['prob']:.1f}% EV+{r['ev']*100:.1f}%"
            )
        lines.append("")

    lines.append("<b>⚽ 今日预测</b>")
    for _, r in pred_df.iterrows():
        lines.append(
            f"<b>{r['home']}</b> vs <b>{r['away']}</b>\n"
            f"  {r['pick']} ({r['score']})  "
            f"主{r['hw']}% 平{r['dr']}% 客{r['aw']}%  "
            f"大2.5:{r['o25']}%"
        )

    lines.append("\n<i>⚠️ 仅供研究，非投注建议</i>")
    return "\n".join(lines)


def main():
    print(f"\n{'='*50}")
    print(f"🏆 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    print("📥 [1/3] 拉取赔率...")
    df = fetch_matches()
    if df.empty:
        print("❌ 无数据"); return
    print(f"✅ {len(df)} 场\n")

    print("🧠 [2/3] 泊松预测...")
    results = []
    for _, r in df.iterrows():
        try:
            results.append({**r.to_dict(), **predict(r)})
        except:
            pass
    pred = pd.DataFrame(results)
    print(f"✅ {len(pred)} 场\n")

    print("💰 [3/3] 凯利筛选...")
    bets = find_bets(pred)
    print(f"✅ {len(bets)} 个机会\n")

    # 输出
    for _, r in pred.iterrows():
        print(f"  {r['home']} vs {r['away']} → {r['pick']} {r['score']} | 大2.5:{r['o25']}%")
    if not bets.empty:
        print(f"\n💎 价值投注 Top 3:")
        for _, r in bets.head(3).iterrows():
            print(f"  {r['bet']} @{r['odds']:.2f} 胜率{r['prob']:.1f}% EV+{r['ev']*100:.1f}%")

    msg = build_msg(pred, bets)
    send_tg(msg)

    # 保存
    Path("results").mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    pred.to_csv(f"results/pred_{ts}.csv", index=False)
    if not bets.empty:
        bets.to_csv(f"results/bets_{ts}.csv", index=False)

    print("\n✅ 完成!")


if __name__ == "__main__":
    main()
