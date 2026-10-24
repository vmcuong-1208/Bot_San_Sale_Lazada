import time
import threading
from typing import Dict, List
import src.database as db
from src.crawlers.price_scraper import PriceScraper
from src.notifications.telegram import TelegramNotifier
from src.config.settings import PRICE_DIFF_ALERT_THRESHOLD, SCAN_INTERVAL_SECONDS

class PriceMonitorService:
    def __init__(self, interval_seconds: int = SCAN_INTERVAL_SECONDS):
        self.interval_seconds = interval_seconds
        self.scraper = PriceScraper(headless=True)
        self.notifier = TelegramNotifier()
        self.is_running = False
        self._thread = None
        self.last_run_time = "Chưa quét"
        self.scan_logs: List[str] = []

    def log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        print(entry)
        self.scan_logs.append(entry)
        if len(self.scan_logs) > 50:
            self.scan_logs.pop(0)

    def check_single_product(self, product: Dict) -> Dict:
        """
        Kiểm tra giá cho 1 sản phẩm và áp dụng logic cảnh báo:
        - Nếu current_price <= target_price:
            Gửi cảnh báo Telegram + Cập nhật lowest_price mới nếu thấp hơn.
        - Nếu current_price > target_price:
            + Chênh lệch (current_price - target_price) > 300.000: Bỏ qua và không báo.
            + Chênh lệch (current_price - target_price) <= 300.000: Gửi cảnh báo Telegram.
        """
        product_id = product["id"]
        url = product["url"]
        target_price = float(product["target_price"])
        old_lowest = float(product.get("lowest_price") or target_price)
        title = product.get("title") or "Sản phẩm"

        self.log(f"Đang kiểm tra: #{product_id} - {title[:30]}...")
        scrape_res = self.scraper.scrape_product_info(url)

        if not scrape_res.get("success"):
            self.log(f"⚠️ Không lấy được giá mới cho #{product_id}. Lỗi: {scrape_res.get('error')}")
            db.update_product_price(
                product_id, 
                title=scrape_res.get("title") or title,
                current_price=product.get("current_price", 0.0),
                lowest_price=old_lowest,
                status="Lỗi cào giá"
            )
            return {"status": "error", "message": scrape_res.get("error")}

        current_price = scrape_res["price"]
        new_title = scrape_res["title"] or title
        new_lowest = min(old_lowest, current_price) if old_lowest > 0 else current_price

        # LOGIC CẢNH BÁO
        if current_price <= target_price:
            status_text = "🎉 ĐẠT GIÁ ĐÁY!"
            self.log(f"🔥 SẢN PHẨM #{product_id} ĐẠT GIÁ ĐÁY: {current_price:,.0f}đ <= {target_price:,.0f}đ")
            self.notifier.send_price_alert(
                title=new_title,
                current_price=current_price,
                target_price=target_price,
                lowest_price=new_lowest,
                link=url,
                alert_type="TOUCH_TARGET"
            )
        else:
            diff = current_price - target_price
            if diff <= PRICE_DIFF_ALERT_THRESHOLD:
                status_text = f"⚠️ Gần chạm đáy (+{int(diff):,}đ)"
                self.log(f"🔔 SẢN PHẨM #{product_id} GẦN GIÁ ĐÁY: Chênh {diff:,.0f}đ <= {PRICE_DIFF_ALERT_THRESHOLD:,.0f}đ. Gửi Telegram.")
                self.notifier.send_price_alert(
                    title=new_title,
                    current_price=current_price,
                    target_price=target_price,
                    lowest_price=new_lowest,
                    link=url,
                    alert_type="NEAR_TARGET"
                )
            else:
                status_text = f"Giá cao (+{int(diff):,}đ)"
                self.log(f"ℹ️ SẢN PHẨM #{product_id}: Chênh {diff:,.0f}đ > {PRICE_DIFF_ALERT_THRESHOLD:,.0f}đ. Bỏ qua.")

        db.update_product_price(
            product_id=product_id,
            title=new_title,
            current_price=current_price,
            lowest_price=new_lowest,
            status=status_text
        )
        return {
            "status": "success",
            "current_price": current_price,
            "lowest_price": new_lowest,
            "product_status": status_text
        }

    def scan_all_products(self):
        """Quét tất cả sản phẩm trong database."""
        products = db.get_all_products()
        if not products:
            self.log("Không có sản phẩm nào trong cơ sở dữ liệu.")
            return

        self.log(f"Bắt đầu quét {len(products)} sản phẩm...")
        for p in products:
            try:
                self.check_single_product(p)
            except Exception as e:
                self.log(f"Lỗi khi xử lý sản phẩm #{p['id']}: {e}")
            time.sleep(2)

        self.last_run_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log(f"Hoàn thành chu trình quét lúc {self.last_run_time}.")

    def _loop(self):
        while self.is_running:
            self.scan_all_products()
            for _ in range(self.interval_seconds):
                if not self.is_running:
                    break
                time.sleep(1)

    def start_background_loop(self):
        if not self.is_running:
            self.is_running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            self.log("Khởi động background task quét giá định kỳ.")

    def stop_background_loop(self):
        self.is_running = False
        self.log("Đã dừng background task.")

# Singleton instance
_monitor_instance = None

def get_monitor_service(interval_seconds: int = SCAN_INTERVAL_SECONDS) -> PriceMonitorService:
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = PriceMonitorService(interval_seconds=interval_seconds)
    return _monitor_instance

