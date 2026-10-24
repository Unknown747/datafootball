"""Parser untuk data JSON dari FotMob (__NEXT_DATA__)."""
import json
import re
from typing import Dict, List, Optional
from src.logger import get_logger

logger = get_logger("datafootball.fotmob_parser")

def extract_next_data(html: str) -> Optional[Dict]:
    """Ekstrak JSON dari tag __NEXT_DATA__."""
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if not match:
        logger.error("Tag __NEXT_DATA__ tidak ditemukan.")
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        logger.error("Gagal parse JSON: %s", e)
        return None

def parse_fixtures(data: Dict) -> List[Dict]:
    """Ekstrak daftar pertandingan dari data __NEXT_DATA__."""
    try:
        fixtures = data["props"]["pageProps"]["fixtures"]
        all_matches = fixtures.get("allMatches", [])
    except KeyError:
        logger.error("Struktur JSON tidak sesuai (fixtures/allMatches tidak ditemukan).")
        return []

    matches = []
    for m in all_matches:
        # Ambil skor jika tersedia
        score_str = m.get("status", {}).get("scoreStr", "")
        home_goals, away_goals = None, None
        if score_str and "-" in score_str:
            try:
                parts = score_str.split("-")
                home_goals = int(parts[0].strip())
                away_goals = int(parts[1].strip())
            except ValueError:
                pass

        matches.append({
            "fotmob_match_id": m.get("id"),
            "utc_time": m.get("status", {}).get("utcTime"),
            "home_name": m.get("home", {}).get("name"),
            "home_id": m.get("home", {}).get("id"),
            "away_name": m.get("away", {}).get("name"),
            "away_id": m.get("away", {}).get("id"),
            "home_goals": home_goals,
            "away_goals": away_goals,
            "status": m.get("status", {}).get("reason", {}).get("short"),
            "finished": m.get("status", {}).get("finished", False),
            "round": m.get("round"),
        })
    
    logger.info("Berhasil mem-parsing %d pertandingan.", len(matches))
    return matches
