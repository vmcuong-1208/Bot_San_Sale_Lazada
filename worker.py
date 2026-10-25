import time
import sys
import io
from pathlib import Path

# Đảm bảo đường dẫn import tương thích
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import src.database as db
from src.services.monitor_service import get_monitor_service
from src.config.settings import SUPABASE_URL, SCAN_INTERVAL_SECONDS

def run_worker():
    print("=" * 65)
    print("🤖 KHỞI ĐỘNG LOCAL WORKER QUÉT GIÁ LAZADA/TMALL (HYBRID MODE)")
    print("=" * 65)
    
    # Khởi tạo database adapter
    db.init_db()
    
    if db.is_using_supabase():
        print("✅ Kết nối thành công tới Supabase Cloud Database.")
        print(f"🔗 Supabase Project: {SUPABASE_URL[:30]}...")
    else:
        print("⚠️ Chưa cấu hình SUPABASE_URL trong .env. Đang chạy chế độ SQLite cục bộ.")
        print("👉 Vui lòng thêm SUPABASE_URL và SUPABASE_KEY vào file .env để kết nối chung với Web Cloud!")

    monitor = get_monitor_service(interval_seconds=SCAN_INTERVAL_SECONDS)
    interval_display = f"{SCAN_INTERVAL_SECONDS} giây" if SCAN_INTERVAL_SECONDS < 60 else f"{SCAN_INTERVAL_SECONDS // 60} phút"
    print(f"⏱️ Chu kỳ quét định kỳ: {interval_display} / lần.")
    print("💡 Worker đang chạy bằng IP mạng dân dụng tại nhà (Residential IP),")
    print("   giúp bóc tách giá 100% không bị chặn 'Access denied' bởi Lazada Cloudflare/WAF.")
    print("   Nhấn Ctrl+C để dừng worker.\n")

    try:
        # Chạy vòng lặp quét
        while True:
            monitor.scan_all_products()
            print(f"\n💤 Nghỉ {SCAN_INTERVAL_SECONDS} giây trước lượt quét tiếp theo...")
            # Đếm ngược theo từng giây mượt mà
            for remaining in range(SCAN_INTERVAL_SECONDS, 0, -1):
                time.sleep(1)
                sys.stdout.write(f"\r⏳ Chu kỳ quét tiếp theo sau: {remaining}s...   ")
                sys.stdout.flush()
            print()
    except KeyboardInterrupt:
        print("\n🛑 Đã dừng Local Worker thành công.")

if __name__ == "__main__":
    run_worker()

