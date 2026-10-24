"""Impor dan normalisasi data historis Football-Data.co.uk."""
import csv
import hashlib
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.logger import get_logger
from src.data_validator import validate_headers, validate_row

logger = get_logger("datafootball.loader")

RAW_DIR = Path("/root/datafootball/data/raw/football_data")
PROCESSED_DIR = Path("/root/datafootball/data/processed")
MATCHES_CSV = PROCESSED_DIR / "matches.csv"
TEAMS_CSV = PROCESSED_DIR / "teams.csv"
INGESTION_LOG_CSV = PROCESSED_DIR / "ingestion_log.csv"

def parse_date(date_str: str) -> str:
    for fmt in ("%d/%m/%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"Format tanggal tidak dikenal: {date_str}")

def make_team_id(name: str) -> str:
    return hashlib.md5(name.strip().lower().encode()).hexdigest()[:8]

def make_match_id(season: str, date: str, home: str, away: str) -> str:
    raw = f"{season}_{date}_{home}_{away}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

def safe_float(s: Optional[str]) -> Optional[float]:
    if s is None or s.strip() == "":
        return None
    try:
        return float(s.strip())
    except ValueError:
        return None

def safe_int(s: Optional[str]) -> Optional[int]:
    if s is None or s.strip() == "":
        return None
    try:
        return int(float(s.strip()))
    except ValueError:
        return None

def load_csv(filepath: Path, season_code: str) -> Tuple[List[Dict], List[Dict]]:
    valid, errors = [], []
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    
    lines = content.splitlines()
    if not lines:
        return [], []
    
    first_line = lines[0]
    cleaned_first_line = ""
    for char in first_line:
        if char.isascii():
            cleaned_first_line += char
        elif cleaned_first_line:
            break
    lines[0] = cleaned_first_line
    cleaned_content = "\n".join(lines)
    
    f_io = io.StringIO(cleaned_content)
    reader = csv.DictReader(f_io)
    headers = reader.fieldnames or []
    
    ok, missing = validate_headers(headers)
    if not ok:
        logger.error(f"{filepath.name}: Kolom wajib hilang: {missing}")
        return [], [{"file": filepath.name, "line": 1, "error": f"Header tidak valid: {missing}"}]

    for i, row in enumerate(reader, start=2):
        clean_row = {k.strip(): v for k, v in row.items() if k}
        
        is_valid, err = validate_row(clean_row)
        if not is_valid:
            errors.append({"file": filepath.name, "line": i, "error": err})
            continue

        try:
            date_iso = parse_date(clean_row["Date"])
        except ValueError as e:
            errors.append({"file": filepath.name, "line": i, "error": str(e)})
            continue

        home = clean_row["HomeTeam"].strip()
        away = clean_row["AwayTeam"].strip()
        
        match = {
            "match_id": make_match_id(season_code, date_iso, home, away),
            "season": season_code,
            "date": date_iso,
            "home_team_id": make_team_id(home),
            "away_team_id": make_team_id(away),
            "home_team_name": home,
            "away_team_name": away,
            "home_goals_ft": int(clean_row["FTHG"]),
            "away_goals_ft": int(clean_row["FTAG"]),
            "result_ft": clean_row["FTR"],
            "home_goals_ht": safe_int(clean_row.get("HTHG")),
            "away_goals_ht": safe_int(clean_row.get("HTAG")),
            "result_ht": clean_row.get("HTR"),
            "home_xg": safe_float(clean_row.get("HxG")),
            "away_xg": safe_float(clean_row.get("AxG")),
            "home_shots": safe_int(clean_row.get("HS")),
            "away_shots": safe_int(clean_row.get("AS")),
            "home_shots_on_target": safe_int(clean_row.get("HST")),
            "away_shots_on_target": safe_int(clean_row.get("AST")),
            "home_corners": safe_int(clean_row.get("HC")),
            "away_corners": safe_int(clean_row.get("AC")),
            "home_yellow": safe_int(clean_row.get("HY")),
            "away_yellow": safe_int(clean_row.get("AY")),
            "home_red": safe_int(clean_row.get("HR")),
            "away_red": safe_int(clean_row.get("AR")),
            "source": "football_data_official",
            "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        valid.append(match)
    return valid, errors

def save_matches(matches: List[Dict]):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    existing = set()
    if MATCHES_CSV.exists():
        with open(MATCHES_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing.add(row["match_id"])
    
    new_matches = [m for m in matches if m["match_id"] not in existing]
    
    fieldnames = [
        "match_id", "season", "date", "home_team_id", "away_team_id",
        "home_team_name", "away_team_name", "home_goals_ft", "away_goals_ft",
        "result_ft", "home_goals_ht", "away_goals_ht", "result_ht",
        "home_xg", "away_xg",
        "home_shots", "away_shots", "home_shots_on_target", "away_shots_on_target",
        "home_corners", "away_corners", "home_yellow", "away_yellow",
        "home_red", "away_red", "source", "retrieved_at"
    ]
    
    write_header = not MATCHES_CSV.exists()
    with open(MATCHES_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(new_matches)
    return len(new_matches), len(matches) - len(new_matches)

def save_teams(matches: List[Dict]):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    existing = set()
    if TEAMS_CSV.exists():
        with open(TEAMS_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing.add(row["team_id"])
    
    teams = {}
    for m in matches:
        teams[m["home_team_id"]] = m["home_team_name"]
        teams[m["away_team_id"]] = m["away_team_name"]
    
    new_teams = [{"team_id": tid, "name": name} for tid, name in teams.items() if tid not in existing]
    
    write_header = not TEAMS_CSV.exists()
    with open(TEAMS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["team_id", "name"])
        if write_header:
            writer.writeheader()
        writer.writerows(new_teams)

def log_ingestion(season: str, total: int, new: int, dup: int, errors: int):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    write_header = not INGESTION_LOG_CSV.exists()
    status = "SUCCESS" if errors == 0 else ("PARTIAL" if total > 0 else "FAILED")
    with open(INGESTION_LOG_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "season", "total_rows", "new_rows", "duplicate_rows", "error_rows", "status"])
        if write_header:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "season": season,
            "total_rows": total,
            "new_rows": new,
            "duplicate_rows": dup,
            "error_rows": errors,
            "status": status
        })

def run_ingestion():
    files = list(RAW_DIR.glob("*_E0.csv"))
    if not files:
        logger.warning(f"Tidak ada file CSV di {RAW_DIR}")
        return
    
    for filepath in sorted(files):
        season = filepath.name.split("_")[0]
        logger.info(f"Memproses {filepath.name} (musim {season})...")
        valid, errors = load_csv(filepath, season)
        if errors:
            for e in errors[:5]:
                logger.warning(f"  Error baris {e['line']}: {e['error']}")
            if len(errors) > 5:
                logger.warning(f"  ... dan {len(errors)-5} error lainnya.")
        new, dup = save_matches(valid)
        save_teams(valid)
        log_ingestion(season, len(valid), new, dup, len(errors))
        logger.info(f"  Selesai: {new} baru, {dup} duplikat, {len(errors)} gagal.")

if __name__ == "__main__":
    run_ingestion()
