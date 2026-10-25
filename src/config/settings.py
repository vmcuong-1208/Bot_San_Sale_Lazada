import os
from pathlib import Path
from dotenv import load_dotenv

# Thư mục gốc dự án (Root directory)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load biến môi trường từ .env ở root (khi chạy local)
ENV_FILE = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE)

def get_secret(key: str, default: str = "") -> str:
    """
    Ưu tiên đọc biến cấu hình từ Streamlit Secrets (khi deploy Streamlit Cloud),
    nếu không có thì fallback sang os.getenv (khi chạy local với file .env).
    """
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)

# Cấu hình Telegram (hỗ trợ cả Streamlit Secrets và .env)
TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = get_secret("TELEGRAM_CHAT_ID", "")

# Cấu hình Supabase (PostgreSQL Cloud)
_raw_supabase_url = get_secret("SUPABASE_URL", "")
# Tự động loại bỏ hậu tố /rest/v1 hoặc dấu gạch chéo cuối để tránh lỗi PGRST125
SUPABASE_URL = _raw_supabase_url.split("/rest/v1")[0].rstrip("/") if _raw_supabase_url else ""
SUPABASE_KEY = get_secret("SUPABASE_KEY", "")

# Cấu hình lọc và quét giá
DISCOUNT_THRESHOLD = int(get_secret("DISCOUNT_THRESHOLD", "30"))
PRICE_DIFF_ALERT_THRESHOLD = float(get_secret("PRICE_DIFF_ALERT_THRESHOLD", "300000"))
SCAN_INTERVAL_SECONDS = int(get_secret("SCAN_INTERVAL_SECONDS", "300"))

# Đường dẫn Database SQLite (Local fallback khi chưa có Supabase)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "products.db"
