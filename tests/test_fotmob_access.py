"""Uji akses ke halaman fixtures FotMob dan ekstraksi data."""
import json
import re
from curl_cffi import requests
from src.logger import get_logger

logger = get_logger("datafootball.test_fotmob")

URL = "https://www.fotmob.com/leagues/47/fixtures/premier-league?season=2025-2026&group=by-date"

def main():
    logger.info("Mengakses: %s", URL)
    try:
        r = requests.get(URL, impersonate="chrome", timeout=30)
        logger.info("HTTP Status: %s", r.status_code)
        logger.info("Ukuran HTML: %d bytes", len(r.text))

        if r.status_code != 200:
            logger.error("Gagal mengakses halaman.")
            return

        # Coba cari __NEXT_DATA__
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.DOTALL)
        if not match:
            logger.warning("Tag __NEXT_DATA__ tidak ditemukan di HTML.")
            return

        logger.info("Tag __NEXT_DATA__ ditemukan. Mencoba parse JSON...")
        try:
            data = json.loads(match.group(1))
            logger.info("JSON berhasil diparse.")
            
            # Cek struktur dasar
            props = data.get("props", {})
            page_props = props.get("pageProps", {})
            
            if not page_props:
                logger.warning("pageProps kosong. Struktur mungkin berbeda.")
                return
                
            logger.info("Keys di pageProps: %s", list(page_props.keys()))
            
            # Coba cari data liga/pertandingan
            # Biasanya ada di 'league' atau 'content'
            if "league" in page_props:
                league_data = page_props["league"]
                logger.info("Keys di league: %s", list(league_data.keys()))
                
                # Cari daftar pertandingan (biasanya di 'matches' atau 'fixtures')
                matches = league_data.get("matches") or league_data.get("fixtures") or []
                if matches:
                    logger.info("Ditemukan %d pertandingan.", len(matches))
                    # Tampilkan 1 contoh
                    logger.info("Contoh pertandingan: %s", json.dumps(matches[0], indent=2)[:500])
                else:
                    logger.warning("Tidak ada key 'matches' atau 'fixtures' di league data.")
            else:
                logger.warning("Key 'league' tidak ditemukan di pageProps.")

        except json.JSONDecodeError as e:
            logger.error("Gagal parse JSON: %s", e)

    except Exception as e:
        logger.error("Error: %s", e)

if __name__ == "__main__":
    main()
