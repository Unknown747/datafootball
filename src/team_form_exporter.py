"""Ekspor form tim dari features.csv ke team_form.csv."""
import csv
from pathlib import Path
from src.logger import get_logger

logger = get_logger("datafootball.team_form")

FEATURES_CSV = Path("/root/datafootball/data/features/features.csv")
OUTPUT_CSV = Path("/root/datafootball/data/processed/team_form.csv")

def run_export():
    rows = []
    with open(FEATURES_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)

    # Ambil form terbaru per tim (berdasarkan tanggal terakhir)
    latest = {}
    for row in rows:
        for side in ["home", "away"]:
            team = row[f"{side}_team"]
            if team not in latest or row["date"] > latest[team]["date"]:
                latest[team] = {
                    "team": team,
                    "date": row["date"],
                    "season": row["season"],
                    "form_pts_5": row[f"{side}_form_pts_5"],
                    "form_gf_avg_5": row[f"{side}_form_gf_avg_5"],
                    "form_ga_avg_5": row[f"{side}_form_ga_avg_5"],
                    "form_n": row[f"{side}_form_n"],
                    "attack_strength": row[f"{side}_attack_strength"],
                    "defense_strength": row[f"{side}_defense_strength"],
                }

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "team", "date", "season", "form_pts_5", "form_gf_avg_5", "form_ga_avg_5",
            "form_n", "attack_strength", "defense_strength"
        ])
        writer.writeheader()
        writer.writerows(latest.values())
    logger.info("team_form.csv dibuat: %d tim.", len(latest))

if __name__ == "__main__":
    run_export()
