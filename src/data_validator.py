"""Validasi data hasil impor CSV."""
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger("datafootball.validator")

REQUIRED_COLUMNS = ["Div", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]

def validate_headers(headers: List[str]) -> Tuple[bool, List[str]]:
    """Bersihkan BOM dan cek kolom wajib."""
    clean = [h.lstrip('\ufeff').strip() for h in headers]
    missing = [c for c in REQUIRED_COLUMNS if c not in clean]
    if missing:
        return False, missing
    return True, []

def validate_row(row: Dict[str, str]) -> Tuple[bool, str]:
    """Cek nilai minimal yang diperlukan untuk satu baris."""
    for col in ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]:
        if not row.get(col) or row.get(col).strip() == "":
            return False, f"Kolom {col} kosong"
    
    # Cek skor harus integer
    try:
        int(row["FTHG"])
        int(row["FTAG"])
    except ValueError:
        return False, "Skor bukan integer"
        
    return True, ""
