"""
config.py —— 赛事定义 & 全局常量
"""
from datetime import timedelta, timezone

# ========== 时区 ==========
BEIJING_TZ = timezone(timedelta(hours=8))

# ========== 足球联赛 ==========
FOOTBALL_LEAGUES = {
    "soccer_epl":                        {"name": "英超",      "api_football_id": 39},
    "soccer_spain_la_liga":              {"name": "西甲",      "api_football_id": 140},
    "soccer_italy_serie_a":              {"name": "意甲",      "api_football_id": 135},
    "soccer_germany_bundesliga":         {"name": "德甲",      "api_football_id": 78},
    "soccer_france_ligue_one":           {"name": "法甲",      "api_football_id": 61},
    "soccer_uefa_champs_league":         {"name": "欧冠",      "api_football_id": 2},
    "soccer_uefa_europa_league":         {"name": "欧联",      "api_football_id": 3},
    "soccer_uefa_european_championship":  {"name": "欧洲杯",    "api_football_id": 4},
}

# ========== 篮球联赛 ==========
BASKETBALL_LEAGUES = {
    "basketball_nba":  {"name": "NBA",   "api_basketball_id": 12},
    "basketball_wnba": {"name": "WNBA",  "api_basketball_id": 44},
}

# ========== NFL ==========
NFL_LEAGUES = {
    "americanfootball_nfl": {"name": "NFL", "api_american_football_id": 1},
}

# ========== 网球大满贯 ==========
TENNIS_GRAND_SLAMS = {
    "tennis_atp_aus_open_singles":  "澳网(ATP)",
    "tennis_wta_aus_open_singles":  "澳网(WTA)",
    "tennis_atp_french_open":       "法网(ATP)",
    "tennis_wta_french_open":       "法网(WTA)",
    "tennis_atp_wimbledon":         "温网(ATP)",
    "tennis_wta_wimbledon":         "温网(WTA)",
    "tennis_atp_us_open":           "美网(ATP)",
    "tennis_wta_us_open":           "美网(WTA)",
}

# ========== 电竞（预留）==========
ESPORTS_LEAGUES = {}

# ========== Odds API 参数 ==========
ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports"
ODDS_MARKETS   = "h2h,totals"
ODDS_REGIONS   = "eu"
ODDS_FORMAT    = "decimal"

# ========== API-Sports 参数 ==========
API_FOOTBALL_BASE           = "https://v3.football.api-sports.io"
API_BASKETBALL_BASE         = "https://v1.basketball.api-sports.io"
API_AMERICAN_FOOTBALL_BASE  = "https://v1.american-football.api-sports.io"

# ========== 泊松模型参数 ==========
LEAGUE_AVG_GOALS  = 1.35
HOME_ADVANTAGE    = 1.25
AWAY_DISCOUNT     = 0.85
POISSON_MAX_GOALS = 10

# ========== 凯利 & 信心评分 ==========
KELLY_FRACTION     = 0.25
MIN_EV_THRESHOLD   = 0.02