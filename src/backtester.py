"""Backtesting: evaluasi model Poisson, Elo, dan Baseline."""
import csv
import math
from pathlib import Path
from typing import Dict, List

from src.logger import get_logger

logger = get_logger("datafootball.backtester")

PRED_DIR = Path("/root/datafootball/data/predictions")
EVAL_DIR = Path("/root/datafootball/data/evaluations")
MATCHES_CSV = Path("/root/datafootball/data/processed/matches.csv")

def load_results() -> Dict[str, str]:
    """Ambil hasil aktual (H/D/A) per match_id."""
    results = {}
    with open(MATCHES_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            results[row["match_id"]] = row["result_ft"]
    return results

def log_loss(probs: List[float], actual_idx: int) -> float:
    """Log loss untuk satu pertandingan. actual_idx: 0=H, 1=D, 2=A."""
    p = probs[actual_idx]
    eps = 1e-15
    return -math.log(max(p, eps))

def brier_score(probs: List[float], actual_idx: int) -> float:
    """Brier score untuk satu pertandingan."""
    targets = [0.0, 0.0, 0.0]
    targets[actual_idx] = 1.0
    return sum((p - t) ** 2 for p, t in zip(probs, targets)) / 3.0

def evaluate_model(model_name: str, value_csv: Path, results: Dict[str, str]) -> Dict:
    """Hitung metrik untuk satu model pada pertandingan dengan odds lengkap."""
    n = 0
    sum_ll = 0.0
    sum_brier = 0.0
    correct = 0

    with open(value_csv, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Hanya evaluasi jika odds lengkap
            if not row["actual_odds_home"] or not row["actual_odds_draw"] or not row["actual_odds_away"]:
                continue

            actual = results.get(row["match_id"])
            if actual not in ("H", "D", "A"):
                continue

            probs = [float(row["prob_home_win"]), float(row["prob_draw"]), float(row["prob_away_win"])]
            # Normalisasi (jaga-jaga ada pembulatan)
            s = sum(probs)
            probs = [p / s for p in probs]

            actual_idx = {"H": 0, "D": 1, "A": 2}[actual]
            sum_ll += log_loss(probs, actual_idx)
            sum_brier += brier_score(probs, actual_idx)

            pred_idx = probs.index(max(probs))
            if pred_idx == actual_idx:
                correct += 1

            n += 1

    if n == 0:
        logger.warning("%s: tidak ada pertandingan dengan odds lengkap.", model_name)
        return {"model": model_name, "n_matches": 0}

    return {
        "model": model_name,
        "n_matches": n,
        "log_loss": round(sum_ll / n, 4),
        "brier_score": round(sum_brier / n, 4),
        "accuracy": round(correct / n, 4),
    }

def run_backtest():
    results = load_results()
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for name in ["poisson", "elo", "baseline"]:
        csv_path = PRED_DIR / f"value_{name}.csv"
        if not csv_path.exists():
            logger.warning("File %s tidak ditemukan, lewati.", csv_path)
            continue
        metric = evaluate_model(name, csv_path, results)
        rows.append(metric)
        logger.info("%s: n=%d, log_loss=%.4f, brier=%.4f, acc=%.4f",
                    metric.get("model"), metric.get("n_matches", 0),
                    metric.get("log_loss", 0), metric.get("brier_score", 0),
                    metric.get("accuracy", 0))

    out_path = EVAL_DIR / "backtest_results.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["model", "n_matches", "log_loss", "brier_score", "accuracy"])
        writer.writeheader()
        writer.writerows(rows)

    logger.info("Hasil backtest disimpan ke %s", out_path)

if __name__ == "__main__":
    run_backtest()
