"""Prediksi untuk pertandingan mendatang dari FotMob (musim 2026/27)."""
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict

from src.logger import get_logger
from src.fotmob_client import FotMobClient
from src.fotmob_parser import extract_next_data, parse_fixtures
from src.poisson_model import build_score_matrix, compute_markets, fair_odds

logger = get_logger("datafootball.upcoming")

FOTMOB_URL = "https://www.fotmob.com/leagues/47/fixtures/premier-league?season=2026-2027&group=by-date"
OUTPUT_CSV = Path("/root/datafootball/data/predictions/upcoming_predictions.csv")

# Alias tim FotMob -> Football-Data
ALIAS = {
    "AFC Bournemouth": "Bournemouth",
    "Brighton & Hove Albion": "Brighton",
    "Leeds United": "Leeds",
    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "Newcastle United": "Newcastle",
    "Nottingham Forest": "Nott'm Forest",
    "Tottenham Hotspur": "Tottenham",
    "West Ham United": "West Ham",
    "Wolverhampton Wanderers": "Wolves",
    "Ipswich Town": "Ipswich",
    "Coventry City": "Coventry",
    "Hull City": "Hull",
}

def utc_to_wib(utc_str: str) -> str:
    if not utc_str:
        return ""
    try:
        dt = datetime.strptime(utc_str[:19], "%Y-%m-%dT%H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc) + timedelta(hours=7)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return utc_str

def get_latest_features() -> Dict[str, Dict]:
    path = Path("/root/datafootball/data/features/features.csv")
    if not path.exists():
        return {}
    latest = {}
    with open(path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for side in ["home", "away"]:
                team = row[f"{side}_team"]
                att = row[f"{side}_attack_strength"]
                dfn = row[f"{side}_defense_strength"]
                lg = row.get("league_avg_goals")
                if att and dfn and lg:
                    if team not in latest or row["date"] > latest[team]["date"]:
                        latest[team] = {
                            "attack": float(att),
                            "defense": float(dfn),
                            "lg_avg": float(lg),
                            "date": row["date"],
                        }
    return latest

def recommend_bet(prob_h: float, prob_d: float, prob_a: float,
                  prob_over25: float, prob_btts: float) -> Dict:
    """Pilih pasar dengan probabilitas tertinggi."""
    options = [
        ("Home Win", prob_h),
        ("Draw", prob_d),
        ("Away Win", prob_a),
        ("Over 2.5", prob_over25),
        ("BTTS Yes", prob_btts),
    ]
    best = max(options, key=lambda x: x[1])
    return {"bet": best[0], "prob": best[1], "fair_odds": fair_odds(best[1])}

def run_upcoming():
    logger.info("Mengambil jadwal mendatang dari FotMob (2026/27)...")
    client = FotMobClient()
    html = client.get_html(FOTMOB_URL)
    data = extract_next_data(html)
    matches = parse_fixtures(data)
    if not matches:
        logger.error("Tidak ada data dari FotMob.")
        return

    upcoming = [m for m in matches if not m["finished"]]
    logger.info("Ditemukan %d pertandingan mendatang.", len(upcoming))

    features = get_latest_features()
    logger.info("Fitur tersedia untuk %d tim.", len(features))

    out = []
    for m in upcoming:
        home = ALIAS.get(m["home_name"], m["home_name"])
        away = ALIAS.get(m["away_name"], m["away_name"])
        h_feat = features.get(home)
        a_feat = features.get(away)

        if h_feat and a_feat:
            lg = (h_feat["lg_avg"] + a_feat["lg_avg"]) / 2
            lam_h = h_feat["attack"] * a_feat["defense"] * lg * 1.05
            lam_a = a_feat["attack"] * h_feat["defense"] * lg * 0.95
        else:
            lam_h, lam_a = 1.4, 1.1

        lam_h = max(lam_h, 0.1)
        lam_a = max(lam_a, 0.1)

        matrix = build_score_matrix(lam_h, lam_a)
        markets = compute_markets(matrix, lam_h, lam_a)

        rec = recommend_bet(
            markets["prob_home_win"], markets["prob_draw"], markets["prob_away_win"],
            markets["prob_over_2_5"], markets["prob_btts_yes"],
        )

        out.append({
            "match_id": m["fotmob_match_id"],
            "kickoff_wib": utc_to_wib(m["utc_time"]),
            "home_team": home,
            "away_team": away,
            "prob_home_win": round(markets["prob_home_win"], 4),
            "prob_draw": round(markets["prob_draw"], 4),
            "prob_away_win": round(markets["prob_away_win"], 4),
            "prob_over_2_5": round(markets["prob_over_2_5"], 4),
            "prob_btts_yes": round(markets["prob_btts_yes"], 4),
            "recommended_bet": rec["bet"],
            "bet_prob": round(rec["prob"], 4),
            "bet_fair_odds": rec["fair_odds"],
            "lambda_home": round(lam_h, 3),
            "lambda_away": round(lam_a, 3),
            "model_version": "poisson_v2",
        })

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        writer.writeheader()
        writer.writerows(out)
    logger.info("Selesai: %d prediksi mendatang ditulis ke %s", len(out), OUTPUT_CSV)

if __name__ == "__main__":
    run_upcoming()
