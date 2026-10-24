"""Baseline model: prediksi konstan dari frekuensi historis 1X2."""
import csv
from collections import Counter
from pathlib import Path

from src.logger import get_logger

logger = get_logger("datafootball.baseline")

MATCHES_CSV = Path("/root/datafootball/data/processed/matches.csv")
OUTPUT_CSV = Path("/root/datafootball/data/predictions/baseline_predictions.csv")

def run_baseline():
    # Hitung frekuensi historis dari SELURUH dataset (pembanding sederhana)
    results = []
    with open(MATCHES_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            results.append(row["result_ft"])

    counter = Counter(results)
    total = len(results)
    p_home = counter["H"] / total
    p_draw = counter["D"] / total
    p_away = counter["A"] / total
    logger.info("Frekuensi historis: H=%.4f, D=%.4f, A=%.4f (n=%d)", p_home, p_draw, p_away, total)

    # Tulis prediksi konstan untuk setiap pertandingan
    with open(MATCHES_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    out = []
    for row in rows:
        out.append({
            "match_id": row["match_id"],
            "season": row["season"],
            "date": row["date"],
            "home_team": row["home_team_name"],
            "away_team": row["away_team_name"],
            "prob_home_win": round(p_home, 4),
            "prob_draw": round(p_draw, 4),
            "prob_away_win": round(p_away, 4),
            "fair_odds_home": round(1/p_home, 3),
            "fair_odds_draw": round(1/p_draw, 3),
            "fair_odds_away": round(1/p_away, 3),
            "model_version": "baseline_v1",
        })

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        writer.writeheader()
        writer.writerows(out)
    logger.info("Selesai: %d prediksi baseline ditulis.", len(out))

if __name__ == "__main__":
    run_baseline()
