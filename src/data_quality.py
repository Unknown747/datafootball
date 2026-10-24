"""Laporan kualitas data dari matches.csv."""
import csv
from collections import Counter
from datetime import datetime
from pathlib import Path
from src.logger import get_logger

logger = get_logger("datafootball.quality")

MATCHES_CSV = Path("/root/datafootball/data/processed/matches.csv")
OUTPUT_CSV = Path("/root/datafootball/data/processed/data_quality.csv")

def run_quality():
    rows = []
    with open(MATCHES_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)

    total = len(rows)
    seasons = Counter(r["season"] for r in rows)
    missing_xg = sum(1 for r in rows if not r.get("home_xg"))
    missing_odds = 0  # odds tidak disimpan di matches.csv
    missing_ht = sum(1 for r in rows if not r.get("home_goals_ht"))

    issues = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for season, count in sorted(seasons.items()):
        issues.append({
            "timestamp": now,
            "check": "season_distribution",
            "season": season,
            "value": count,
            "status": "OK" if count == 380 else ("PARTIAL" if count > 0 else "FAIL"),
        })
    issues.append({
        "timestamp": now,
        "check": "missing_xg",
        "season": "ALL",
        "value": missing_xg,
        "status": "OK" if missing_xg == 0 else "WARN",
    })
    issues.append({
        "timestamp": now,
        "check": "missing_ht",
        "season": "ALL",
        "value": missing_ht,
        "status": "OK" if missing_ht == 0 else "WARN",
    })
    issues.append({
        "timestamp": now,
        "check": "total_rows",
        "season": "ALL",
        "value": total,
        "status": "OK",
    })

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "check", "season", "value", "status"])
        writer.writeheader()
        writer.writerows(issues)
    logger.info("data_quality.csv dibuat: %d baris.", len(issues))

if __name__ == "__main__":
    run_quality()
