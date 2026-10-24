"""Model Poisson dengan opsi xG."""
import csv
import math
from pathlib import Path
from typing import Dict, List, Tuple

from src.logger import get_logger

logger = get_logger("datafootball.poisson")

FEATURES_CSV = Path("/root/datafootball/data/features/features.csv")
OUTPUT_CSV = Path("/root/datafootball/data/predictions/poisson_predictions.csv")

MAX_GOALS = 10
HT_GOAL_RATIO = 0.45
MIN_XG_SAMPLE = 3

def poisson_prob(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def build_score_matrix(lambda_home: float, lambda_away: float) -> List[List[float]]:
    return [
        [poisson_prob(h, lambda_home) * poisson_prob(a, lambda_away) for a in range(MAX_GOALS + 1)]
        for h in range(MAX_GOALS + 1)
    ]

def compute_markets(matrix: List[List[float]], lambda_home: float, lambda_away: float) -> Dict:
    prob_home_win = prob_draw = prob_away_win = 0.0
    prob_over_2_5 = prob_over_3_5 = prob_over_4_5 = prob_btts_yes = 0.0
    for h in range(MAX_GOALS + 1):
        for a in range(MAX_GOALS + 1):
            p = matrix[h][a]
            total = h + a
            if h > a: prob_home_win += p
            elif h == a: prob_draw += p
            else: prob_away_win += p
            if total > 2.5: prob_over_2_5 += p
            if total > 3.5: prob_over_3_5 += p
            if total > 4.5: prob_over_4_5 += p
            if h >= 1 and a >= 1: prob_btts_yes += p

    lambda_home_ht = lambda_home * HT_GOAL_RATIO
    lambda_away_ht = lambda_away * HT_GOAL_RATIO
    p0_home_ht = poisson_prob(0, lambda_home_ht)
    p0_away_ht = poisson_prob(0, lambda_away_ht)
    prob_over_0_5_ht = 1.0 - (p0_home_ht * p0_away_ht)

    return {
        "prob_home_win": prob_home_win,
        "prob_draw": prob_draw,
        "prob_away_win": prob_away_win,
        "prob_over_2_5": prob_over_2_5,
        "prob_over_3_5": prob_over_3_5,
        "prob_over_4_5": prob_over_4_5,
        "prob_btts_yes": prob_btts_yes,
        "prob_over_0_5_ht": prob_over_0_5_ht,
    }

def fair_odds(prob: float) -> float:
    return round(1.0 / prob, 3) if prob > 0 else None

def compute_lambdas(row: Dict) -> Tuple[float, float, str]:
    """Hitung λ_home, λ_away, dan sumber (xg / goals / fallback)."""
    lg_avg = float(row["league_avg_goals"]) if row.get("league_avg_goals") else None

    # Cek xG
    h_xg_for = float(row["home_xg_for_avg"]) if row.get("home_xg_for_avg") else None
    h_xg_against = float(row["home_xg_against_avg"]) if row.get("home_xg_against_avg") else None
    a_xg_for = float(row["away_xg_for_avg"]) if row.get("away_xg_for_avg") else None
    a_xg_against = float(row["away_xg_against_avg"]) if row.get("away_xg_against_avg") else None
    h_xg_n = int(row["home_xg_n"]) if row.get("home_xg_n") else 0
    a_xg_n = int(row["away_xg_n"]) if row.get("away_xg_n") else 0

    use_xg = (
        h_xg_for is not None and h_xg_against is not None
        and a_xg_for is not None and a_xg_against is not None
        and h_xg_n >= MIN_XG_SAMPLE and a_xg_n >= MIN_XG_SAMPLE
        and lg_avg is not None
    )

    if use_xg:
        # Gunakan xG-based attack/defense (gol pengganti)
        h_att = h_xg_for / lg_avg
        h_def = h_xg_against / lg_avg
        a_att = a_xg_for / lg_avg
        a_def = a_xg_against / lg_avg
        lam_h = h_att * a_def * lg_avg * 1.05
        lam_a = a_att * h_def * lg_avg * 0.95
        return max(lam_h, 0.1), max(lam_a, 0.1), "xg"

    # Fallback ke attack/defense berbasis gol
    h_att = float(row["home_attack_strength"]) if row.get("home_attack_strength") else None
    h_def = float(row["home_defense_strength"]) if row.get("home_defense_strength") else None
    a_att = float(row["away_attack_strength"]) if row.get("away_attack_strength") else None
    a_def = float(row["away_defense_strength"]) if row.get("away_defense_strength") else None

    if lg_avg is None:
        return 1.4, 1.1, "fallback"
    if h_att is None or h_def is None or a_att is None or a_def is None:
        return lg_avg * 1.1, lg_avg * 0.9, "fallback"

    lam_h = h_att * a_def * lg_avg * 1.05
    lam_a = a_att * h_def * lg_avg * 0.95
    return max(lam_h, 0.1), max(lam_a, 0.1), "goals"

def run_predictions():
    rows = []
    with open(FEATURES_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    logger.info("Memproses %d pertandingan.", len(rows))

    out = []
    source_counter = {"xg": 0, "goals": 0, "fallback": 0}
    for row in rows:
        lam_h, lam_a, source = compute_lambdas(row)
        source_counter[source] += 1
        matrix = build_score_matrix(lam_h, lam_a)
        markets = compute_markets(matrix, lam_h, lam_a)
        out.append({
            "match_id": row["match_id"],
            "season": row["season"],
            "date": row["date"],
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "lambda_home": round(lam_h, 3),
            "lambda_away": round(lam_a, 3),
            "prob_home_win": round(markets["prob_home_win"], 4),
            "prob_draw": round(markets["prob_draw"], 4),
            "prob_away_win": round(markets["prob_away_win"], 4),
            "fair_odds_home": fair_odds(markets["prob_home_win"]),
            "fair_odds_draw": fair_odds(markets["prob_draw"]),
            "fair_odds_away": fair_odds(markets["prob_away_win"]),
            "prob_over_2_5": round(markets["prob_over_2_5"], 4),
            "prob_over_3_5": round(markets["prob_over_3_5"], 4),
            "prob_over_4_5": round(markets["prob_over_4_5"], 4),
            "prob_btts_yes": round(markets["prob_btts_yes"], 4),
            "prob_over_0_5_ht": round(markets["prob_over_0_5_ht"], 4),
            "model_version": f"poisson_v2_{source}",
        })

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        writer.writeheader()
        writer.writerows(out)

    logger.info("Selesai: %d prediksi ditulis. Sumber λ: xg=%d, goals=%d, fallback=%d",
                len(out), source_counter["xg"], source_counter["goals"], source_counter["fallback"])

if __name__ == "__main__":
    run_predictions()
