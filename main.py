import os
import sys
import io
import time
from pathlib import Path

# Đảm bảo đường dẫn import tương thích
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.crawlers.flash_sale_crawler import FlashSaleCrawler
from src.notifications.telegram import TelegramNotifier
from src.config.settings import DISCOUNT_THRESHOLD

def run_flash_sale_bot():
    print("=" * 60)
    print("🚀 BẮT ĐẦU QUÉT SẢN PHẨM FLASH SALE LAZADA")
    print("=" * 60)

    print(f"🎯 Ngưỡng lọc giảm giá: >= {DISCOUNT_THRESHOLD}%")

    notifier = TelegramNotifier()
    if notifier.is_configured():
        print("🔗 Đang kiểm tra kết nối Telegram Bot...")
        test_res = notifier.test_connection()
        if test_res.get("ok"):
            bot_name = test_res.get("result", {}).get("username", "Unknown")
            print(f"✅ Kết nối Telegram Bot thành công: @{bot_name}")
        else:
            print(f"⚠️ Kiểm tra Telegram Bot không thành công: {test_res.get('description')}")
    else:
        print("ℹ️ Telegram Bot chưa được thiết lập Token/Chat ID trong file .env (chế độ Test/Dry-run)")

    crawler = FlashSaleCrawler(headless=True)
    print("\n🌐 Bắt đầu thu thập dữ liệu bằng Playwright...")
    products = crawler.fetch_flash_sale_products()

    print(f"\n📊 Tổng số sản phẩm Flash Sale thu thập được: {len(products)}")

    qualifying_products = [
        p for p in products if p.get("discount", 0) >= DISCOUNT_THRESHOLD
    ]

    print(f"🔥 Số sản phẩm đạt điều kiện giảm giá >= {DISCOUNT_THRESHOLD}%: {len(qualifying_products)}")
    print("-" * 60)

    if not qualifying_products:
        print(f"Không có sản phẩm nào đạt mức giảm giá >= {DISCOUNT_THRESHOLD}%.")
        if products:
            print("Gợi ý top 3 sản phẩm có % giảm giá cao nhất hiện tại:")
            sorted_products = sorted(products, key=lambda x: x.get("discount", 0), reverse=True)
            for p in sorted_products[:3]:
                print(f" • [{p['discount']}%] {p['title']} - Giá: {p['price']}")
        return

    for idx, p in enumerate(qualifying_products, start=1):
        print(f"\n[{idx}/{len(qualifying_products)}] Sản phẩm:")
        print(f"  📦 Tên: {p['title']}")
        print(f"  💰 Giá mới: {p['price']}")
        print(f"  🏷️ Giá cũ: {p['original_price']}")
        print(f"  📉 Giảm: -{p['discount']}%")
        print(f"  🔗 Link: {p['link']}")

        if notifier.is_configured():
            success = notifier.send_flash_sale_alert(p)
            if success:
                print("  ✅ Đã gửi thông báo đến Telegram.")
            else:
                print("  ❌ Gửi thông báo đến Telegram thất bại.")
            time.sleep(1)
        else:
            print("  ℹ️ [Dry-run] Bỏ qua gửi Telegram do chưa điền .env.")

    print("\n" + "=" * 60)
    print("✨ HOÀN THÀNH CHU TRÌNH KIỂM TRA")
    print("=" * 60)

if __name__ == "__main__":
    run_flash_sale_bot()
