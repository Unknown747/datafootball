"""Hitung klasemen dari matches.csv."""
import csv
from collections import defaultdict
from pathlib import Path
from src.logger import get_logger

logger = get_logger("datafootball.standings")

MATCHES_CSV = Path("/root/datafootball/data/processed/matches.csv")
OUTPUT_CSV = Path("/root/datafootball/data/processed/standings.csv")

def run_standings():
    rows = []
    with open(MATCHES_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    rows.sort(key=lambda r: r["date"])

    # Hanya hitung musim 2026/27 (2627) untuk klasemen terbaru
    season = "2627"
    rows = [r for r in rows if r["season"] == season]

    stats = defaultdict(lambda: {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0})

    for r in rows:
        home = r["home_team_name"]
        away = r["away_team_name"]
        hg = int(r["home_goals_ft"])
        ag = int(r["away_goals_ft"])

        stats[home]["P"] += 1
        stats[away]["P"] += 1
        stats[home]["GF"] += hg
        stats[home]["GA"] += ag
        stats[away]["GF"] += ag
        stats[away]["GA"] += hg

        if hg > ag:
            stats[home]["W"] += 1
            stats[home]["Pts"] += 3
            stats[away]["L"] += 1
        elif hg < ag:
            stats[away]["W"] += 1
            stats[away]["Pts"] += 3
            stats[home]["L"] += 1
        else:
            stats[home]["D"] += 1
            stats[away]["D"] += 1
            stats[home]["Pts"] += 1
            stats[away]["Pts"] += 1

    # Urutkan
    table = []
    for team, s in stats.items():
        table.append({
            "season": season,
            "team": team,
            "played": s["P"],
            "wins": s["W"],
            "draws": s["D"],
            "losses": s["L"],
            "gf": s["GF"],
            "ga": s["GA"],
            "gd": s["GF"] - s["GA"],
            "points": s["Pts"],
        })
    table.sort(key=lambda x: (-x["points"], -x["gd"], -x["gf"]))

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "season", "team", "played", "wins", "draws", "losses", "gf", "ga", "gd", "points"
        ])
        writer.writeheader()
        writer.writerows(table)
    logger.info("Klasemen %s: %d tim ditulis ke %s", season, len(table), OUTPUT_CSV)

if __name__ == "__main__":
    run_standings()
