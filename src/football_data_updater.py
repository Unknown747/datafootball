"""Update database dari Football-Data.co.uk untuk musim aktif."""
import subprocess
from pathlib import Path
from src.logger import get_logger
from src.football_data_loader import run_ingestion

logger = get_logger("datafootball.updater")

RAW_DIR = Path("/root/datafootball/data/raw/football_data")
BASE_URL = "https://football-data.co.uk/mmz4281"
ACTIVE_SEASON = "2526"

def update_active_season():
    """Unduh ulang file musim aktif, lalu impor."""
    url = f"{BASE_URL}/{ACTIVE_SEASON}/E0.csv"
    out = RAW_DIR / f"{ACTIVE_SEASON}_E0.csv"
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Mengunduh %s...", url)
    result = subprocess.run(
        ["curl", "-4", "-sSL", "-o", str(out), "-w", "%{http_code}", "--max-time", "60", url],
        capture_output=True, text=True,
    )
    if result.stdout.strip() != "200":
        logger.error("Gagal mengunduh: HTTP %s", result.stdout.strip())
        return

    logger.info("Unduhan selesai. Menjalankan impor...")
    run_ingestion()

if __name__ == "__main__":
    update_active_season()
