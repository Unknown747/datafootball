"""Ekspor odds B365 dari CSV mentah ke odds.csv."""
import csv
import hashlib
import io
from datetime import datetime
from pathlib import Path
from src.logger import get_logger

logger = get_logger("datafootball.odds_export")

RAW_DIR = Path("/root/datafootball/data/raw/football_data")
OUTPUT_CSV = Path("/root/datafootball/data/processed/odds.csv")

def safe_float(s):
    if not s or s.strip() == "":
        return None
    try:
        return float(s.strip())
    except ValueError:
        return None

def run_export():
    all_rows = []
    for filepath in sorted(RAW_DIR.glob("*_E0.csv")):
        season = filepath.name.split("_")[0]
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        lines = content.splitlines()
        if not lines:
            continue
        # Bersihkan BOM
        header = [h.strip().lstrip('\ufeff') for h in lines[0].split(',')]
        if "B365H" not in header:
            continue
        idx_b365h = header.index("B365H")
        idx_b365d = header.index("B365D")
        idx_b365a = header.index("B365A")
        idx_date = header.index("Date")
        idx_home = header.index("HomeTeam")
        idx_away = header.index("AwayTeam")

        reader = csv.DictReader(io.StringIO("\n".join([",".join(header)] + lines[1:])))
        for row in reader:
            try:
                date_parts = row["Date"].strip().split("/")
                year = f"20{date_parts[2]}" if len(date_parts[2]) == 2 else date_parts[2]
                date_iso = f"{year}-{date_parts[1]}-{date_parts[0]}"
                home = row["HomeTeam"].strip()
                away = row["AwayTeam"].strip()
                mid = hashlib.md5(f"{season}_{date_iso}_{home}_{away}".encode()).hexdigest()[:12]
                odds_h = safe_float(row.get("B365H", ""))
                odds_d = safe_float(row.get("B365D", ""))
                odds_a = safe_float(row.get("B365A", ""))
                if odds_h and odds_d and odds_a:
                    all_rows.append({
                        "match_id": mid,
                        "season": season,
                        "date": date_iso,
                        "home_team": home,
                        "away_team": away,
                        "bookmaker": "B365",
                        "odds_home": odds_h,
                        "odds_draw": odds_d,
                        "odds_away": odds_a,
                        "source": "football_data_official",
                        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
            except Exception:
                continue

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)
    logger.info("odds.csv dibuat: %d baris.", len(all_rows))

if __name__ == "__main__":
    run_export()
