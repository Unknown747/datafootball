"""Menghitung value dari odds aktual vs probabilitas model."""
import csv
from pathlib import Path
from typing import Dict, List, Optional

from src.logger import get_logger

logger = get_logger("datafootball.odds")

RAW_DIR = Path("/root/datafootball/data/raw/football_data")
PROCESSED_DIR = Path("/root/datafootball/data/processed")
PRED_DIR = Path("/root/datafootball/data/predictions")

MATCHES_CSV = PROCESSED_DIR / "matches.csv"
VALUE_THRESHOLD = 5.0  # ambang value untuk flag

def load_actual_odds() -> Dict[str, Dict[str, Optional[float]]]:
    """Baca odds B365 dari file CSV mentah, kunci = match_id."""
    odds_map = {}
    import hashlib
    
    for filepath in RAW_DIR.glob("*_E0.csv"):
        season = filepath.name.split("_")[0]
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        if not lines:
            continue
        # Bersihkan BOM di header
        header = [h.strip().lstrip('\ufeff') for h in lines[0].split(',')]
        idx_b365h = header.index("B365H") if "B365H" in header else None
        idx_b365d = header.index("B365D") if "B365D" in header else None
        idx_b365a = header.index("B365A") if "B365A" in header else None

        # Parsing manual baris per baris (bisa ada koma di nama? tidak, CSV aman)
        import io
        reader = csv.DictReader(io.StringIO("\n".join([",".join(header)] + lines[1:])))
        
        for i, row in enumerate(reader, start=2):
            try:
                date_parts = row["Date"].strip().split("/")
                if len(date_parts[2]) == 2:
                    year = f"20{date_parts[2]}"
                else:
                    year = date_parts[2]
                date_iso = f"{year}-{date_parts[1]}-{date_parts[0]}"
                home = row["HomeTeam"].strip()
                away = row["AwayTeam"].strip()
                mid = hashlib.md5(f"{season}_{date_iso}_{home}_{away}".encode()).hexdigest()[:12]

                def safe_float(s):
                    try:
                        v = float(s.strip())
                        return v if v > 0 else None
                    except (ValueError, AttributeError):
                        return None

                odds_map[mid] = {
                    "B365H": safe_float(row.get("B365H", "")),
                    "B365D": safe_float(row.get("B365D", "")),
                    "B365A": safe_float(row.get("B365A", "")),
                }
            except Exception:
                continue
    return odds_map

def compute_value(prob: Optional[float], odds: Optional[float]) -> Optional[float]:
    if prob is None or odds is None or prob <= 0 or odds <= 0:
        return None
    return round(((prob * odds) - 1) * 100, 2)

def process_model(model_name: str, pred_csv: Path, odds_map: Dict):
    with open(pred_csv, "r", encoding="utf-8") as f:
        preds = list(csv.DictReader(f))

    out = []
    matched_odds_count = 0
    value_flags = {"home": 0, "draw": 0, "away": 0}

    for p in preds:
        mid = p["match_id"]
        odds = odds_map.get(mid, {})
        
        # Jika tidak ada odds, tandai N/A
        prob_h = float(p["prob_home_win"]) if p["prob_home_win"] else None
        prob_d = float(p["prob_draw"]) if p["prob_draw"] else None
        prob_a = float(p["prob_away_win"]) if p["prob_away_win"] else None

        val_h = compute_value(prob_h, odds.get("B365H"))
        val_d = compute_value(prob_d, odds.get("B365D"))
        val_a = compute_value(prob_a, odds.get("B365A"))

        has_odds = all(odds.get(k) is not None for k in ["B365H", "B365D", "B365A"])
        if has_odds:
            matched_odds_count += 1

        # Flag jika ada value > threshold
        flag_parts = []
        if val_h is not None and val_h > VALUE_THRESHOLD:
            flag_parts.append(f"H({val_h}%)")
            value_flags["home"] += 1
        if val_d is not None and val_d > VALUE_THRESHOLD:
            flag_parts.append(f"D({val_d}%)")
            value_flags["draw"] += 1
        if val_a is not None and val_a > VALUE_THRESHOLD:
            flag_parts.append(f"A({val_a}%)")
            value_flags["away"] += 1

        out.append({
            "match_id": mid,
            "season": p["season"],
            "date": p["date"],
            "home_team": p["home_team"],
            "away_team": p["away_team"],
            "prob_home_win": p["prob_home_win"],
            "prob_draw": p["prob_draw"],
            "prob_away_win": p["prob_away_win"],
            "fair_odds_home": p["fair_odds_home"],
            "fair_odds_draw": p["fair_odds_draw"],
            "fair_odds_away": p["fair_odds_away"],
            "actual_odds_home": odds.get("B365H") or "",
            "actual_odds_draw": odds.get("B365D") or "",
            "actual_odds_away": odds.get("B365A") or "",
            "value_home_pct": val_h if val_h is not None else "",
            "value_draw_pct": val_d if val_d is not None else "",
            "value_away_pct": val_a if val_a is not None else "",
            "value_flag": ";".join(flag_parts) if flag_parts else "",
            "model_version": p["model_version"],
        })

    out_path = PRED_DIR / f"value_{model_name}.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        writer.writeheader()
        writer.writerows(out)

    logger.info(
        "%s: %d baris, %d dengan odds lengkap, value flag: H=%d D=%d A=%d -> %s",
        model_name, len(out), matched_odds_count,
        value_flags["home"], value_flags["draw"], value_flags["away"], out_path.name,
    )

def main():
    logger.info("Memuat odds aktual dari data mentah...")
    odds_map = load_actual_odds()
    logger.info("Total pertandingan dengan odds: %d", len(odds_map))

    process_model("poisson", PRED_DIR / "poisson_predictions.csv", odds_map)
    process_model("elo", PRED_DIR / "elo_predictions.csv", odds_map)
    process_model("baseline", PRED_DIR / "baseline_predictions.csv", odds_map)

if __name__ == "__main__":
    main()
