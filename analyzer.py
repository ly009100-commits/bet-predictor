from datetime import datetime
"""
analyzer.py —— 分析引擎
  ├── 泊松预测（含战绩修正）
  ├── 期望值计算
  ├── 信心评分 1-10
  └── 风险评估
"""
import numpy as np
from scipy.stats import poisson
from config import *


def predict_poisson(match: dict) -> dict:
    """泊松预测 + 近期战绩修正"""
    if match["has_draw"]:
        # ---- 足球 ----
        o1, oX, o2 = match["o1"], match["oX"], match["o2"]
        imp1, impX, imp2 = 1 / o1, 1 / oX, 1 / o2
        total = imp1 + impX + imp2
        ph = imp1 / total
        pd = impX / total
        pa = imp2 / total

        hxg = LEAGUE_AVG_GOALS * (ph + 0.5 * pd) * HOME_ADVANTAGE
        axg = LEAGUE_AVG_GOALS * (pa + 0.5 * pd) * AWAY_DISCOUNT

        # ---- 战绩修正 ----
        h_stats = match.get("stats_home", {}) or {}
        a_stats = match.get("stats_away", {}) or {}
        h_form = h_stats.get("form", "")
        a_form = a_stats.get("form", "")

        if h_form:
            recent_wins = h_form.count("W")
            hxg *= 1 + (recent_wins - 3) * 0.04      # ±12% 范围
        if a_form:
            recent_wins = a_form.count("W")
            axg *= 1 + (recent_wins - 3) * 0.04

        # 场均进球修正
        if h_stats.get("gf_home"):
            ratio = h_stats["gf_home"] / max(LEAGUE_AVG_GOALS * HOME_ADVANTAGE, 0.1)
            hxg *= 0.7 + 0.3 * ratio
        if a_stats.get("gf_away"):
            ratio = a_stats["gf_away"] / max(LEAGUE_AVG_GOALS * AWAY_DISCOUNT, 0.1)
            axg *= 0.7 + 0.3 * ratio

        hxg = max(0.1, hxg)
        axg = max(0.1, axg)

        hp = np.array([poisson.pmf(i, hxg) for i in range(POISSON_MAX_GOALS)])
        ap = np.array([poisson.pmf(i, axg) for i in range(POISSON_MAX_GOALS)])
        m = np.outer(hp, ap)

        hw = float(np.sum(np.tril(m, -1)))
        dr = float(np.sum(np.diag(m)))
        aw = float(np.sum(np.triu(m, 1)))

        g = np.fromfunction(lambda i, j: i + j,
                            (POISSON_MAX_GOALS, POISSON_MAX_GOALS), dtype=int)
        o25 = float(np.sum(m[g > 2.5]))
        idx = np.unravel_index(np.argmax(m), m.shape)

        fair_home = round(1 / hw, 2) if hw > 0 else 999
        fair_draw = round(1 / dr, 2) if dr > 0 else 999
        fair_away = round(1 / aw, 2) if aw > 0 else 999

        probs = {"主胜": hw, "平局": dr, "客胜": aw}
        best_pick = max(probs, key=probs.get)

        return {
            "prob_home": round(hw * 100, 1),
            "prob_draw": round(dr * 100, 1),
            "prob_away": round(aw * 100, 1),
            "prob_over": round(o25 * 100, 1),
            "pred_score": f"{idx[0]}-{idx[1]}",
            "pred_result": best_pick,
            "fair_home": fair_home, "fair_draw": fair_draw, "fair_away": fair_away,
            "xg_home": round(hxg, 2), "xg_away": round(axg, 2),
            "form_home": h_form, "form_away": a_form,
        }
    else:
        # ---- 篮球 / NFL / 网球 ----
        o1, o2 = match["o1"], match["o2"]
        imp1, imp2 = 1 / o1, 1 / o2
        total = imp1 + imp2
        ph = imp1 / total
        pa = imp2 / total

        # 战绩修正
        h_stats = match.get("stats_home", {}) or {}
        a_stats = match.get("stats_away", {}) or {}
        h_form = h_stats.get("form", "")
        a_form = a_stats.get("form", "")

        if h_form:
            ph *= 1 + (h_form.count("W") - 3) * 0.04
        if a_form:
            pa *= 1 + (a_form.count("W") - 3) * 0.04

        total2 = ph + pa
        ph /= total2
        pa /= total2

        hw = ph
        aw = pa
        fair_home = round(1 / hw, 2) if hw > 0 else 999
        fair_away = round(1 / aw, 2) if aw > 0 else 999
        best_pick = "主胜" if hw > aw else "客胜"

        return {
            "prob_home": round(hw * 100, 1),
            "prob_draw": 0,
            "prob_away": round(aw * 100, 1),
            "prob_over": 0,
            "pred_score": "-",
            "pred_result": best_pick,
            "fair_home": fair_home, "fair_draw": None, "fair_away": fair_away,
            "xg_home": 0, "xg_away": 0,
            "form_home": h_form, "form_away": a_form,
        }


def calc_ev(match: dict, pred: dict) -> float:
    best = -999
    if match["o1"] and pred["prob_home"]:
        best = max(best, (pred["prob_home"] / 100) * match["o1"] - 1)
    if match["o2"] and pred["prob_away"]:
        best = max(best, (pred["prob_away"] / 100) * match["o2"] - 1)
    if match.get("o_over") and pred["prob_over"]:
        best = max(best, (pred["prob_over"] / 100) * match["o_over"] - 1)
    return round(best, 4)


def calc_confidence(match: dict, pred: dict, ev: float) -> int:
    score = 5.0

    if ev > 0.15:   score += 3
    elif ev > 0.08: score += 2
    elif ev > 0.03: score += 1
    elif ev < -0.05: score -= 2
    elif ev < 0:    score -= 1

    best_prob = max(pred["prob_home"], pred["prob_draw"], pred["prob_away"])
    if best_prob > 65:   score += 2
    elif best_prob > 55: score += 1
    elif best_prob < 40: score -= 1

    # 有战绩数据加分
    if pred.get("form_home") or pred.get("form_away"):
        score += 0.5

    return max(1, min(10, round(score)))


def calc_risk(match: dict, pred: dict, ev: float) -> str:
    r = 0
    if ev < 0:              r += 2
    elif ev < 0.03:         r += 1
    best_prob = max(pred["prob_home"], pred["prob_away"])
    if best_prob < 45:      r += 1
    if (match["o1"] or 1) > 3.5 or (match["o2"] or 1) > 3.5:
        r += 1
    if not pred.get("form_home") and not pred.get("form_away"):
        r += 1   # 无战绩数据 → 风险 +1

    if r <= 1:     return "🟢 低"
    elif r <= 2:   return "🟡 中"
    else:          return "🔴 高"


def analyze_single(match: dict) -> dict:
    pred = predict_poisson(match)
    ev   = calc_ev(match, pred)
    conf = calc_confidence(match, pred, ev)
    risk = calc_risk(match, pred, ev)
    return {**match, **pred, "ev": ev, "confidence": conf, "risk": risk}


def analyze_all(matches: list) -> list:
    results = []
    for i, m in enumerate(matches):
        try:
            results.append(analyze_single(m))
        except Exception as e:
            print(f"  ⚠️ [{i}] {m.get('home','?')} vs {m.get('away','?')}: {e}")
    results.sort(key=lambda m: m["time"] or datetime.max)
    return results