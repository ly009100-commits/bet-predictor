"""
data_fetcher.py —— 双 API 数据采集
  ├── The Odds API   → 所有赔率
  └── API-Sports 家族 → 足球/篮球/NFL 近期战绩
"""
import os
import requests
from datetime import datetime
from config import *


# ==========================================================
# 内部工具
# ==========================================================

def _call_odds_api(sport_key: str, api_key: str) -> list:
    url = f"{ODDS_API_BASE}/{sport_key}/odds"
    params = {
        "apiKey": api_key,
        "regions": ODDS_REGIONS,
        "markets": ODDS_MARKETS,
        "oddsFormat": ODDS_FORMAT,
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []


def _extract_odds(game: dict, has_draw: bool) -> dict | None:
    home = game.get("home_team", "")
    away = game.get("away_team", "")

    commence = game.get("commence_time", "")
    try:
        match_time = datetime.fromisoformat(commence.replace("Z", "+00:00"))
        match_time = match_time.astimezone(BEIJING_TZ).replace(tzinfo=None)
    except:
        match_time = None

    h2h = {}
    over = under = None

    for bk in game.get("bookmakers", []):
        for m in bk.get("markets", []):
            if m["key"] == "h2h" and not h2h:
                h2h = {o["name"]: o["price"] for o in m["outcomes"]}
            if m["key"] == "totals" and over is None:
                for o in m["outcomes"]:
                    if o.get("point") and abs(o["point"] - 2.5) < 0.1:
                        if o["name"] == "Over":
                            over = o["price"]
                        else:
                            under = o["price"]

    if has_draw:
        if not (h2h.get(home) and h2h.get("Draw") and h2h.get(away)):
            return None
        return {"home": home, "away": away, "time": match_time,
                "o1": h2h[home], "oX": h2h["Draw"], "o2": h2h[away],
                "o_over": over, "o_under": under, "has_draw": True}
    else:
        if not (h2h.get(home) and h2h.get(away)):
            return None
        return {"home": home, "away": away, "time": match_time,
                "o1": h2h[home], "oX": None, "o2": h2h[away],
                "o_over": over, "o_under": under, "has_draw": False}


# ==========================================================
# API-Sports 团队统计
# ==========================================================

def _call_api_sports(base_url: str, endpoint: str, api_key: str) -> dict:
    url = f"{base_url}/{endpoint}"
    headers = {"x-apisports-key": api_key}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return {}


def _search_team_id_football(team_name: str, league_id: int, api_key: str) -> int | None:
    """API-Football 队名搜索 → team_id"""
    data = _call_api_sports(API_FOOTBALL_BASE,
                            f"teams?search={team_name}", api_key)
    for team in data.get("response", []):
        tid = team["team"]["id"]
        # 验证该队确实属于目标联赛
        league_data = _call_api_sports(
            API_FOOTBALL_BASE,
            f"teams/statistics?team={tid}&league={league_id}&season=2025",
            api_key
        )
        if league_data.get("results", 0) > 0:
            return tid
    return None


def _search_team_id_basketball(team_name: str, league_id: int, api_key: str) -> int | None:
    """API-Basketball 队名搜索"""
    data = _call_api_sports(API_BASKETBALL_BASE,
                            f"teams?search={team_name}", api_key)
    for team in data.get("response", []):
        tid = team["id"]
        check = _call_api_sports(
            API_BASKETBALL_BASE,
            f"teams/statistics?id={tid}&league={league_id}&season=2025-2026",
            api_key
        )
        if check.get("results", 0) > 0:
            return tid
    return None


def _search_team_id_nfl(team_name: str, league_id: int, api_key: str) -> int | None:
    """API-NFL 队名搜索"""
    data = _call_api_sports(API_AMERICAN_FOOTBALL_BASE,
                            f"teams?search={team_name}", api_key)
    for team in data.get("response", []):
        tid = team["id"]
        check = _call_api_sports(
            API_AMERICAN_FOOTBALL_BASE,
            f"teams/statistics?id={tid}&league={league_id}&season=2025",
            api_key
        )
        if check.get("results", 0) > 0:
            return tid
    return None


def _get_football_stats(team_id: int, league_id: int, api_key: str) -> dict:
    """API-Football 球队统计"""
    data = _call_api_sports(
        API_FOOTBALL_BASE,
        f"teams/statistics?team={team_id}&league={league_id}&season=2025",
        api_key
    )
    resp = data.get("response", {})
    if not resp:
        return {}

    form_str = resp.get("form", "?" * 10)[:10]
    fixtures = resp.get("fixtures", {})
    goals = resp.get("goals", {})

    return {
        "form": form_str,
        "wins_home":   fixtures.get("wins", {}).get("home", 0),
        "draws_home":  fixtures.get("draws", {}).get("home", 0),
        "loses_home":  fixtures.get("loses", {}).get("home", 0),
        "wins_away":   fixtures.get("wins", {}).get("away", 0),
        "draws_away":  fixtures.get("draws", {}).get("away", 0),
        "loses_away":  fixtures.get("loses", {}).get("away", 0),
        "gf_home": float(goals.get("for", {}).get("average", {}).get("home", 0) or 0),
        "gf_away": float(goals.get("for", {}).get("average", {}).get("away", 0) or 0),
        "ga_home": float(goals.get("against", {}).get("average", {}).get("home", 0) or 0),
        "ga_away": float(goals.get("against", {}).get("average", {}).get("away", 0) or 0),
    }


def _get_basketball_stats(team_id: int, league_id: int, api_key: str) -> dict:
    """API-Basketball 球队统计"""
    data = _call_api_sports(
        API_BASKETBALL_BASE,
        f"teams/statistics?id={team_id}&league={league_id}&season=2025-2026",
        api_key
    )
    resp = data.get("response", {})
    if not resp:
        return {}
    return {
        "form": str(resp.get("form", "?" * 10))[:10],
        "wins_home":  resp.get("wins", {}).get("home", {}).get("total", 0),
        "loses_home": resp.get("losses", {}).get("home", {}).get("total", 0),
        "wins_away":  resp.get("wins", {}).get("away", {}).get("total", 0),
        "loses_away": resp.get("losses", {}).get("away", {}).get("total", 0),
        "points_for_avg_home":  float(resp.get("points", {}).get("for", {}).get("average", {}).get("home", 0) or 0),
        "points_for_avg_away":  float(resp.get("points", {}).get("for", {}).get("average", {}).get("away", 0) or 0),
        "points_against_avg_home": float(resp.get("points", {}).get("against", {}).get("average", {}).get("home", 0) or 0),
        "points_against_avg_away": float(resp.get("points", {}).get("against", {}).get("average", {}).get("away", 0) or 0),
    }


def _get_nfl_stats(team_id: int, league_id: int, api_key: str) -> dict:
    """API-NFL 球队统计"""
    data = _call_api_sports(
        API_AMERICAN_FOOTBALL_BASE,
        f"teams/statistics?id={team_id}&league={league_id}&season=2025",
        api_key
    )
    resp = data.get("response", {})
    if not resp:
        return {}
    return {
        "form": str(resp.get("form", "?" * 10))[:10],
        "wins_home":  resp.get("wins", {}).get("home", {}).get("total", 0),
        "loses_home": resp.get("losses", {}).get("home", {}).get("total", 0),
        "wins_away":  resp.get("wins", {}).get("away", {}).get("total", 0),
        "loses_away": resp.get("losses", {}).get("away", {}).get("total", 0),
    }


# ==========================================================
# 各项目采集
# ==========================================================

def _collect_from_odds(sport_dict: dict, api_key: str, start, end,
                       has_draw: bool, label: str, category: str,
                       api_sports_key: str = "",
                       api_sports_type: str = "") -> list:
    """通用：从 Odds API 采集，可选补充 API-Sports 战绩"""
    matches = []
    for sport_key, info in sport_dict.items():
        league_name = info["name"] if isinstance(info, dict) else info
        games = _call_odds_api(sport_key, api_key)

        for g in games:
            odds = _extract_odds(g, has_draw)
            if odds is None or odds["time"] is None:
                continue
            if odds["time"] < start or odds["time"] > end:
                continue

            odds["sport_key"]  = sport_key
            odds["league"]     = league_name
            odds["category"]   = category
            odds["label"]      = label
            odds["stats_home"] = {}
            odds["stats_away"] = {}

            # 尝试补充 API-Sports 战绩
            if api_sports_key and isinstance(info, dict):
                if api_sports_type == "football":
                    league_id = info.get("api_football_id")
                    if league_id:
                        home_id = _search_team_id_football(odds["home"], league_id, api_sports_key)
                        away_id = _search_team_id_football(odds["away"], league_id, api_sports_key)
                        if home_id:
                            odds["stats_home"] = _get_football_stats(home_id, league_id, api_sports_key)
                        if away_id:
                            odds["stats_away"] = _get_football_stats(away_id, league_id, api_sports_key)

                elif api_sports_type == "basketball":
                    league_id = info.get("api_basketball_id")
                    if league_id:
                        home_id = _search_team_id_basketball(odds["home"], league_id, api_sports_key)
                        away_id = _search_team_id_basketball(odds["away"], league_id, api_sports_key)
                        if home_id:
                            odds["stats_home"] = _get_basketball_stats(home_id, league_id, api_sports_key)
                        if away_id:
                            odds["stats_away"] = _get_basketball_stats(away_id, league_id, api_sports_key)

                elif api_sports_type == "nfl":
                    league_id = info.get("api_american_football_id")
                    if league_id:
                        home_id = _search_team_id_nfl(odds["home"], league_id, api_sports_key)
                        away_id = _search_team_id_nfl(odds["away"], league_id, api_sports_key)
                        if home_id:
                            odds["stats_home"] = _get_nfl_stats(home_id, league_id, api_sports_key)
                        if away_id:
                            odds["stats_away"] = _get_nfl_stats(away_id, league_id, api_sports_key)

            matches.append(odds)
    return matches


def fetch_football(odds_key: str, foot_key: str, start, end) -> list:
    return _collect_from_odds(FOOTBALL_LEAGUES, odds_key, start, end,
                              has_draw=True, label="⚽ 足球", category="football",
                              api_sports_key=foot_key, api_sports_type="football")


def fetch_basketball(odds_key: str, basket_key: str, start, end) -> list:
    return _collect_from_odds(BASKETBALL_LEAGUES, odds_key, start, end,
                              has_draw=False, label="🏀 篮球", category="basketball",
                              api_sports_key=basket_key, api_sports_type="basketball")


def fetch_nfl(odds_key: str, nfl_key: str, start, end) -> list:
    return _collect_from_odds(NFL_LEAGUES, odds_key, start, end,
                              has_draw=False, label="🏈 NFL", category="nfl",
                              api_sports_key=nfl_key, api_sports_type="nfl")


def fetch_tennis(odds_key: str, start, end) -> list:
    plain = {k: v for k, v in TENNIS_GRAND_SLAMS.items()}
    return _collect_from_odds(plain, odds_key, start, end,
                              has_draw=False, label="🎾 网球", category="tennis")


def fetch_esports(odds_key: str, start, end) -> list:
    return []


# ==========================================================
# 总入口
# ==========================================================

def fetch_all(odds_key: str, foot_key: str, basket_key: str,
              nfl_key: str, start, end) -> list:
    """拉取全部五项目"""
    all_matches = []

    print("[数据采集] 开始...")

    print("  ⚽ 足球...")
    all_matches += fetch_football(odds_key, foot_key, start, end)

    print("  🏀 篮球...")
    all_matches += fetch_basketball(odds_key, basket_key, start, end)

    print("  🏈 NFL...")
    all_matches += fetch_nfl(odds_key, nfl_key, start, end)

    print("  🎾 网球...")
    all_matches += fetch_tennis(odds_key, start, end)

    print("  🎮 电竞(预留)...")
    all_matches += fetch_esports(odds_key, start, end)

    all_matches.sort(key=lambda m: m["time"] or datetime.max)

    # 统计战绩覆盖情况
    with_stats = sum(1 for m in all_matches if m.get("stats_home") or m.get("stats_away"))
    print(f"[数据采集] 总计 {len(all_matches)} 场 (含战绩 {with_stats} 场)\n")

    return all_matches