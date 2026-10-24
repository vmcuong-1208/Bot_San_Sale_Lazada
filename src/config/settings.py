import os
from pathlib import Path
from dotenv import load_dotenv

# Thư mục gốc dự án (Root directory)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load biến môi trường từ .env ở root
ENV_FILE = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE)

# Cấu hình Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Cấu hình lọc và quét giá
DISCOUNT_THRESHOLD = int(os.getenv("DISCOUNT_THRESHOLD", "30"))
PRICE_DIFF_ALERT_THRESHOLD = float(os.getenv("PRICE_DIFF_ALERT_THRESHOLD", "300000"))
SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", "300"))

# Đường dẫn Database SQLite
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "products.db"

