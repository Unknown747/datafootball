"""Ekspor xG dari matches.csv ke xg.csv."""
import csv
from datetime import datetime
from pathlib import Path
from src.logger import get_logger

logger = get_logger("datafootball.xg_export")

MATCHES_CSV = Path("/root/datafootball/data/processed/matches.csv")
OUTPUT_CSV = Path("/root/datafootball/data/processed/xg.csv")

def run_export():
    rows = []
    with open(MATCHES_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("home_xg") and row.get("away_xg"):
                rows.append({
                    "match_id": row["match_id"],
                    "season": row["season"],
                    "date": row["date"],
                    "home_team": row["home_team_name"],
                    "away_team": row["away_team_name"],
                    "home_xg": row["home_xg"],
                    "away_xg": row["away_xg"],
                    "source": row.get("source", "football_data_official"),
                    "retrieved_at": row.get("retrieved_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                })
    if not rows:
        logger.warning("Tidak ada data xG.")
        return
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    logger.info("xg.csv dibuat: %d baris.", len(rows))

if __name__ == "__main__":
    run_export()
