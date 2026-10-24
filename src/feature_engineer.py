"""Fitur statistik dengan time decay, season decay, dan xG."""
import csv
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.logger import get_logger

logger = get_logger("datafootball.features")

MATCHES_CSV = Path("/root/datafootball/data/processed/matches.csv")
OUTPUT_CSV = Path("/root/datafootball/data/features/features.csv")

HALF_LIFE_DAYS = 180.0

def parse_date(d: str) -> datetime:
    return datetime.strptime(d, "%Y-%m-%d")

def to_year(season_code: str) -> int:
    return int("20" + season_code[:2])

def season_weight(current_season: str, hist_season: str) -> float:
    diff = to_year(current_season) - to_year(hist_season)
    if diff <= 0:
        return 1.0
    return 0.5 ** diff

def weight_for_match(current_date: datetime, current_season: str,
                     hist_date: datetime, hist_season: str) -> float:
    days = max((current_date - hist_date).days, 0)
    time_w = 0.5 ** (days / HALF_LIFE_DAYS)
    season_w = season_weight(current_season, hist_season)
    return time_w * season_w

def safe_float(s: Optional[str]) -> Optional[float]:
    if s is None or s.strip() == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None

def run_feature_engineering():
    matches = []
    with open(MATCHES_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["date_obj"] = parse_date(row["date"])
            row["home_goals_ft"] = int(row["home_goals_ft"])
            row["away_goals_ft"] = int(row["away_goals_ft"])
            row["home_xg_val"] = safe_float(row.get("home_xg"))
            row["away_xg_val"] = safe_float(row.get("away_xg"))
            matches.append(row)
    matches.sort(key=lambda m: (m["date_obj"], m["match_id"]))
    logger.info("Memproses %d pertandingan.", len(matches))

    team_history = defaultdict(list)
    league_stats = defaultdict(list)

    features = []

    for m in matches:
        season = m["season"]
        home = m["home_team_name"]
        away = m["away_team_name"]
        hg = m["home_goals_ft"]
        ag = m["away_goals_ft"]
        hxg = m["home_xg_val"]
        axg = m["away_xg_val"]
        cur_date = m["date_obj"]

        # --- FORM ---
        def form_stats(team):
            hist = [x for x in team_history[team] if x["date"] < cur_date]
            hist = sorted(hist, key=lambda x: x["date"], reverse=True)[:5]
            if not hist:
                return {"pts": None, "gf": None, "ga": None, "n": 0}
            total_w = 0.0
            w_pts = 0.0
            w_gf = 0.0
            w_ga = 0.0
            for h in hist:
                w = weight_for_match(cur_date, season, h["date"], h["season"])
                total_w += w
                if h["team"] == h["home"]:
                    gf, ga = h["hg"], h["ag"]
                    if h["hg"] > h["ag"]: pts = 3
                    elif h["hg"] == h["ag"]: pts = 1
                    else: pts = 0
                else:
                    gf, ga = h["ag"], h["hg"]
                    if h["ag"] > h["hg"]: pts = 3
                    elif h["ag"] == h["hg"]: pts = 1
                    else: pts = 0
                w_pts += w * pts
                w_gf += w * gf
                w_ga += w * ga
            if total_w == 0:
                return {"pts": None, "gf": None, "ga": None, "n": len(hist)}
            return {
                "pts": w_pts / total_w,
                "gf": w_gf / total_w,
                "ga": w_ga / total_w,
                "n": len(hist),
            }

        h_form = form_stats(home)
        a_form = form_stats(away)

        # --- HOME/AWAY STATS ---
        def home_away_stats(team, is_home):
            hist = [x for x in team_history[team]
                    if x["date"] < cur_date
                    and ((x["home"] == team) if is_home else (x["away"] == team))]
            if not hist:
                return {"gf_avg": None, "ga_avg": None, "n": 0}
            total_w = 0.0
            w_gf = 0.0
            w_ga = 0.0
            for x in hist:
                w = weight_for_match(cur_date, season, x["date"], x["season"])
                total_w += w
                if x["home"] == team:
                    w_gf += w * x["hg"]
                    w_ga += w * x["ag"]
                else:
                    w_gf += w * x["ag"]
                    w_ga += w * x["hg"]
            return {
                "gf_avg": w_gf / total_w if total_w > 0 else None,
                "ga_avg": w_ga / total_w if total_w > 0 else None,
                "n": len(hist),
            }

        h_home = home_away_stats(home, True)
        a_away = home_away_stats(away, False)

        # --- LEAGUE AVERAGES ---
        def league_avgs():
            hist = [x for x in league_stats[season] if x[0] < cur_date]
            if not hist:
                return None, None, None
            total_w = 0.0
            w_goals = 0.0
            w_over = 0.0
            w_btts = 0.0
            for (d, tg, over, btts) in hist:
                w = weight_for_match(cur_date, season, d, season)
                total_w += w
                w_goals += w * tg
                w_over += w * (1 if over else 0)
                w_btts += w * (1 if btts else 0)
            avg_per_team = (w_goals / total_w) / 2 if total_w > 0 else None
            return avg_per_team, w_over/total_w, w_btts/total_w

        lg_avg, lg_over25, lg_btts = league_avgs()

        # --- ATTACK/DEFENSE (gol) ---
        def team_attack_defense(team, lg_avg):
            if lg_avg is None:
                return None, None
            hist = [x for x in team_history[team] if x["date"] < cur_date]
            if not hist:
                return None, None
            total_w = 0.0
            w_scored = 0.0
            w_conceded = 0.0
            for x in hist:
                w = weight_for_match(cur_date, season, x["date"], x["season"])
                total_w += w
                if x["home"] == team:
                    w_scored += w * x["hg"]
                    w_conceded += w * x["ag"]
                else:
                    w_scored += w * x["ag"]
                    w_conceded += w * x["hg"]
            if total_w == 0:
                return None, None
            attack = (w_scored / total_w) / lg_avg
            defense = (w_conceded / total_w) / lg_avg
            return attack, defense

        h_att, h_def = team_attack_defense(home, lg_avg)
        a_att, a_def = team_attack_defense(away, lg_avg)

        # --- xG STATS (jika tersedia) ---
        def team_xg_stats(team, lg_avg):
            if lg_avg is None:
                return None, None, 0
            hist = [x for x in team_history[team]
                    if x["date"] < cur_date and x.get("hxg") is not None and x.get("axg") is not None]
            if not hist:
                return None, None, 0
            total_w = 0.0
            w_for = 0.0
            w_against = 0.0
            for x in hist:
                w = weight_for_match(cur_date, season, x["date"], x["season"])
                total_w += w
                if x["home"] == team:
                    w_for += w * x["hxg"]
                    w_against += w * x["axg"]
                else:
                    w_for += w * x["axg"]
                    w_against += w * x["hxg"]
            if total_w == 0:
                return None, None, 0
            xg_for = w_for / total_w
            xg_against = w_against / total_w
            return xg_for, xg_against, len(hist)

        h_xg_for, h_xg_against, h_xg_n = team_xg_stats(home, lg_avg)
        a_xg_for, a_xg_against, a_xg_n = team_xg_stats(away, lg_avg)

        # --- H2H ---
        h2h = [x for x in team_history[home]
               if x["date"] < cur_date
               and ((x["home"] == home and x["away"] == away) or (x["home"] == away and x["away"] == home))]
        h2h_home_wins = sum(1 for x in h2h if (x["home"] == home and x["hg"] > x["ag"]) or (x["away"] == home and x["ag"] > x["hg"]))
        h2h_draws = sum(1 for x in h2h if x["hg"] == x["ag"])
        h2h_away_wins = len(h2h) - h2h_home_wins - h2h_draws

        # --- DAYS REST ---
        def days_rest(team):
            prev = [x for x in team_history[team] if x["date"] < cur_date]
            if not prev:
                return None
            last = max(prev, key=lambda x: x["date"])
            return (cur_date - last["date"]).days

        h_rest = days_rest(home)
        a_rest = days_rest(away)

        features.append({
            "match_id": m["match_id"],
            "season": season,
            "date": m["date"],
            "home_team": home,
            "away_team": away,
            "home_goals": hg,
            "away_goals": ag,
            "home_form_pts_5": round(h_form["pts"], 3) if h_form["pts"] is not None else "",
            "home_form_gf_avg_5": round(h_form["gf"], 3) if h_form["gf"] is not None else "",
            "home_form_ga_avg_5": round(h_form["ga"], 3) if h_form["ga"] is not None else "",
            "home_form_n": h_form["n"],
            "away_form_pts_5": round(a_form["pts"], 3) if a_form["pts"] is not None else "",
            "away_form_gf_avg_5": round(a_form["gf"], 3) if a_form["gf"] is not None else "",
            "away_form_ga_avg_5": round(a_form["ga"], 3) if a_form["ga"] is not None else "",
            "away_form_n": a_form["n"],
            "home_home_gf_avg": round(h_home["gf_avg"], 3) if h_home["gf_avg"] is not None else "",
            "home_home_ga_avg": round(h_home["ga_avg"], 3) if h_home["ga_avg"] is not None else "",
            "away_away_gf_avg": round(a_away["gf_avg"], 3) if a_away["gf_avg"] is not None else "",
            "away_away_ga_avg": round(a_away["ga_avg"], 3) if a_away["ga_avg"] is not None else "",
            "home_attack_strength": round(h_att, 3) if h_att is not None else "",
            "home_defense_strength": round(h_def, 3) if h_def is not None else "",
            "away_attack_strength": round(a_att, 3) if a_att is not None else "",
            "away_defense_strength": round(a_def, 3) if a_def is not None else "",
            "home_xg_for_avg": round(h_xg_for, 3) if h_xg_for is not None else "",
            "home_xg_against_avg": round(h_xg_against, 3) if h_xg_against is not None else "",
            "away_xg_for_avg": round(a_xg_for, 3) if a_xg_for is not None else "",
            "away_xg_against_avg": round(a_xg_against, 3) if a_xg_against is not None else "",
            "home_xg_n": h_xg_n,
            "away_xg_n": a_xg_n,
            "league_avg_goals": round(lg_avg, 3) if lg_avg else "",
            "league_over25_rate": round(lg_over25, 3) if lg_over25 is not None else "",
            "league_btts_rate": round(lg_btts, 3) if lg_btts is not None else "",
            "h2h_n": len(h2h),
            "h2h_home_wins": h2h_home_wins,
            "h2h_draws": h2h_draws,
            "h2h_away_wins": h2h_away_wins,
            "home_days_rest": h_rest,
            "away_days_rest": a_rest,
        })

        team_history[home].append({"team": home, "home": home, "away": away, "hg": hg, "ag": ag,
                                   "hxg": hxg, "axg": axg, "date": cur_date, "season": season})
        team_history[away].append({"team": away, "home": home, "away": away, "hg": hg, "ag": ag,
                                   "hxg": hxg, "axg": axg, "date": cur_date, "season": season})
        league_stats[season].append((cur_date, hg + ag, (hg + ag) > 2.5, hg > 0 and ag > 0))

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(features[0].keys()))
        writer.writeheader()
        writer.writerows(features)
    logger.info("Selesai: %d baris fitur ditulis ke %s", len(features), OUTPUT_CSV)

if __name__ == "__main__":
    run_feature_engineering()
