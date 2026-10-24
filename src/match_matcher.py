"""Mencocokkan pertandingan Football-Data dan FotMob."""
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from src.logger import get_logger
from src.fotmob_client import FotMobClient
from src.fotmob_parser import extract_next_data, parse_fixtures

logger = get_logger("datafootball.matcher")

PROCESSED_DIR = Path("/root/datafootball/data/processed")
MATCHES_CSV = PROCESSED_DIR / "matches.csv"
ALIASES_CSV = PROCESSED_DIR / "team_aliases.csv"
CANONICAL_CSV = PROCESSED_DIR / "matches_canonical.csv"
CONFLICTS_CSV = PROCESSED_DIR / "source_conflicts.csv"

FOTMOB_URL = "https://www.fotmob.com/leagues/47/fixtures/premier-league?season=2025-2026&group=by-date"

def load_aliases() -> Dict[str, str]:
    """Buat mapping nama FotMob -> canonical."""
    aliases = {}
    with open(ALIASES_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["source"] == "fotmob":
                aliases[row["source_name"]] = row["canonical_name"]
    return aliases

def load_football_data() -> List[Dict]:
    """Baca matches.csv."""
    matches = []
    with open(MATCHES_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            matches.append(row)
    return matches

def load_fotmob() -> List[Dict]:
    """Ambil dan parse data FotMob."""
    client = FotMobClient()
    html = client.get_html(FOTMOB_URL)
    data = extract_next_data(html)
    return parse_fixtures(data)

def normalize_fotmob_date(utc_time: str) -> str:
    """Ubah ISO UTC ke YYYY-MM-DD."""
    dt = datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%SZ")
    return dt.strftime("%Y-%m-%d")

def run_matching():
    aliases = load_aliases()
    fd_matches = load_football_data()
    fotmob_matches = load_fotmob()

    # Filter Football-Data hanya musim 2526 (2025/26)
    fd_2526 = [m for m in fd_matches if m["season"] == "2526"]
    logger.info("Football-Data 2526: %d pertandingan", len(fd_2526))

    # Buat index Football-Data berdasarkan (date, home, away)
    fd_index = {}
    for m in fd_2526:
        key = (m["date"], m["home_team_name"], m["away_team_name"])
        fd_index[key] = m

    canonical = []
    conflicts = []

    for fm in fotmob_matches:
        if not fm["finished"] or fm["home_goals"] is None:
            continue  # Lewati pertandingan yang belum selesai

        fm_date = normalize_fotmob_date(fm["utc_time"])
        home_canon = aliases.get(fm["home_name"], fm["home_name"])
        away_canon = aliases.get(fm["away_name"], fm["away_name"])

        key = (fm_date, home_canon, away_canon)
        fd_match = fd_index.get(key)

        if fd_match:
            # Pertandingan cocok
            if (int(fd_match["home_goals_ft"]) != fm["home_goals"] or
                int(fd_match["away_goals_ft"]) != fm["away_goals"]):
                conflicts.append({
                    "date": fm_date,
                    "home": home_canon,
                    "away": away_canon,
                    "fd_score": f"{fd_match['home_goals_ft']}-{fd_match['away_goals_ft']}",
                    "fotmob_score": f"{fm['home_goals']}-{fm['away_goals']}",
                })
            
            canonical.append({
                "match_id": fd_match["match_id"],
                "season": "2526",
                "date": fm_date,
                "home_team": home_canon,
                "away_team": away_canon,
                "home_goals": fd_match["home_goals_ft"],
                "away_goals": fd_match["away_goals_ft"],
                "source": "football_data+fotmob",
                "fotmob_match_id": fm["fotmob_match_id"],
                "status": "matched",
            })
        else:
            # Hanya ada di FotMob
            canonical.append({
                "match_id": f"fm_{fm['fotmob_match_id']}",
                "season": "2526",
                "date": fm_date,
                "home_team": home_canon,
                "away_team": away_canon,
                "home_goals": fm["home_goals"],
                "away_goals": fm["away_goals"],
                "source": "fotmob_only",
                "fotmob_match_id": fm["fotmob_match_id"],
                "status": "fotmob_only",
            })

    # Simpan canonical
    with open(CANONICAL_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "match_id", "season", "date", "home_team", "away_team",
            "home_goals", "away_goals", "source", "fotmob_match_id", "status"
        ])
        writer.writeheader()
        writer.writerows(canonical)

    # Simpan conflicts
    with open(CONFLICTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "date", "home", "away", "fd_score", "fotmob_score"
        ])
        writer.writeheader()
        writer.writerows(conflicts)

    logger.info("Selesai: %d pertandingan kanonis, %d konflik.", len(canonical), len(conflicts))

if __name__ == "__main__":
    run_matching()
