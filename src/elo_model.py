"""Model Elo untuk prediksi 1X2 dengan rating dinamis."""
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

from src.logger import get_logger

logger = get_logger("datafootball.elo")

MATCHES_CSV = Path("/root/datafootball/data/processed/matches.csv")
OUTPUT_CSV = Path("/root/datafootball/data/predictions/elo_predictions.csv")

INITIAL_RATING = 1500.0
K_FACTOR = 20.0
HOME_ADVANTAGE = 65.0
DRAW_PROB_FACTOR = 0.28  # proporsi draw pada selisih Elo 0

def expected_score(r_a: float, r_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((r_b - r_a) / 400.0))

def elo_to_1x2(r_home_adj: float, r_away: float) -> Tuple[float, float, float]:
    """Konversi selisih Elo ke probabilitas 1X2 (H, D, A)."""
    diff = r_home_adj - r_away
    # Probabilitas home win (exclude draw)
    p_home_no_draw = expected_score(r_home_adj, r_away)
    # Skala draw berdasarkan |diff|: makin besar selisih, makin kecil draw
    draw_scale = max(0.10, DRAW_PROB_FACTOR - abs(diff) / 2000.0)
    p_draw = draw_scale
    # Sisa dibagi proporsional
    remaining = 1.0 - p_draw
    p_home = remaining * p_home_no_draw
    p_away = remaining * (1.0 - p_home_no_draw)
    return p_home, p_draw, p_away

def run_elo():
    rows = []
    with open(MATCHES_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["date_obj"] = datetime.strptime(row["date"], "%Y-%m-%d")
            rows.append(row)
    rows.sort(key=lambda r: (r["date_obj"], r["match_id"]))

    ratings = defaultdict(lambda: INITIAL_RATING)
    out = []

    for row in rows:
        home = row["home_team_name"]
        away = row["away_team_name"]
        hg = int(row["home_goals_ft"])
        ag = int(row["away_goals_ft"])

        r_home = ratings[home]
        r_away = ratings[away]

        p_h, p_d, p_a = elo_to_1x2(r_home + HOME_ADVANTAGE, r_away)

        out.append({
            "match_id": row["match_id"],
            "season": row["season"],
            "date": row["date"],
            "home_team": home,
            "away_team": away,
            "prob_home_win": round(p_h, 4),
            "prob_draw": round(p_d, 4),
            "prob_away_win": round(p_a, 4),
            "fair_odds_home": round(1/p_h, 3) if p_h > 0 else None,
            "fair_odds_draw": round(1/p_d, 3) if p_d > 0 else None,
            "fair_odds_away": round(1/p_a, 3) if p_a > 0 else None,
            "elo_home_before": round(r_home, 1),
            "elo_away_before": round(r_away, 1),
            "model_version": "elo_v1",
        })

        # Update rating setelah pertandingan
        exp_h = expected_score(r_home + HOME_ADVANTAGE, r_away)
        if hg > ag:
            actual_h = 1.0
        elif hg == ag:
            actual_h = 0.5
        else:
            actual_h = 0.0

        ratings[home] = r_home + K_FACTOR * (actual_h - exp_h)
        ratings[away] = r_away + K_FACTOR * ((1.0 - actual_h) - (1.0 - exp_h))

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        writer.writeheader()
        writer.writerows(out)
    logger.info("Selesai: %d prediksi Elo ditulis.", len(out))

if __name__ == "__main__":
    run_elo()
