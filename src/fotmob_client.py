"""HTTP client untuk FotMob menggunakan curl_cffi."""
import time
from curl_cffi import requests
from src.logger import get_logger

logger = get_logger("datafootball.fotmob_client")

class FotMobClient:
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries

    def get_html(self, url: str) -> str:
        """Ambil HTML dengan retry terbatas."""
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info("GET %s (percobaan %d/%d)", url, attempt, self.max_retries)
                r = requests.get(url, impersonate="chrome", timeout=self.timeout)
                if r.status_code == 200:
                    return r.text
                else:
                    logger.warning("HTTP %s untuk %s", r.status_code, url)
            except Exception as e:
                logger.warning("Error: %s", e)
            
            if attempt < self.max_retries:
                time.sleep(2 * attempt)  # backoff
                
        raise RuntimeError(f"Gagal mengambil {url} setelah {self.max_retries} percobaan.")
