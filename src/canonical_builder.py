"""Bangun matches_canonical.csv dari matches.csv (semua musim)."""
import csv
from pathlib import Path
from src.logger import get_logger

logger = get_logger("datafootball.canonical")

MATCHES_CSV = Path("/root/datafootball/data/processed/matches.csv")
OUTPUT_CSV = Path("/root/datafootball/data/processed/matches_canonical.csv")

def run_build():
    rows = []
    with open(MATCHES_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append({
                "match_id": row["match_id"],
                "season": row["season"],
                "date": row["date"],
                "home_team": row["home_team_name"],
                "away_team": row["away_team_name"],
                "home_goals": row["home_goals_ft"],
                "away_goals": row["away_goals_ft"],
                "result": row["result_ft"],
                "source": row["source"],
                "fotmob_match_id": "",  # belum diisi
                "status": "matched" if row["season"] != "2627" else "fotmob_only",
            })
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    logger.info("matches_canonical.csv dibuat: %d baris.", len(rows))

if __name__ == "__main__":
    run_build()
