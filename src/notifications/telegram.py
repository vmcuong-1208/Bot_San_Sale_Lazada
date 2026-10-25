import requests
from src.config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class TelegramNotifier:
    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def is_configured(self) -> bool:
        return bool(
            self.token 
            and self.chat_id 
            and self.token != "your_bot_token_here" 
            and self.chat_id != "your_chat_id_here"
        )

    def test_connection(self) -> dict:
        """Kiểm tra token telegram bot có hợp lệ không."""
        if not self.is_configured():
            return {"ok": False, "description": "Token hoặc Chat ID chưa được cấu hình trong .env"}
        try:
            url = f"{self.base_url}/getMe"
            resp = requests.get(url, timeout=10)
            return resp.json()
        except Exception as e:
            return {"ok": False, "description": str(e)}

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Gửi tin nhắn qua Telegram Bot API."""
        if not self.is_configured():
            print(f"[DRY-RUN TELEGRAM]:\n{text}")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False
        }
        try:
            resp = requests.post(url, json=payload, timeout=15)
            data = resp.json()
            if not data.get("ok"):
                print(f"[ERROR] Gửi tin nhắn Telegram thất bại: {data.get('description')}")
                return False
            return True
        except Exception as e:
            print(f"[ERROR] Lỗi kết nối Telegram: {e}")
            return False

    def send_flash_sale_alert(self, product: dict) -> bool:
        """Định dạng và gửi thông báo sản phẩm Flash Sale."""
        title = product.get("title", "Không có tiêu đề").replace("<", "&lt;").replace(">", "&gt;")
        price = product.get("price", "N/A")
        original_price = product.get("original_price", "N/A")
        discount = product.get("discount", 0)
        link = product.get("link", "#")

        message = (
            "🔥 <b>LAZADA FLASH SALE ALERT!</b> 🔥\n\n"
            f"📦 <b>Sản phẩm:</b> {title}\n"
            f"💰 <b>Giá Flash Sale:</b> <code>{price}</code>\n"
            f"🏷️ <b>Giá gốc:</b> <strike>{original_price}</strike>\n"
            f"📉 <b>Giảm giá:</b> <b>-{discount}%</b>\n\n"
            f"👉 <a href=\"{link}\">Xem và mua ngay trên Lazada</a>"
        )
        return self.send_message(message)

    def send_price_alert(
        self, 
        title: str, 
        current_price: float, 
        target_price: float, 
        lowest_price: float, 
        link: str, 
        alert_type: str = "TOUCH_TARGET",
        effective_price: float = 0.0,
        discount_desc: str = ""
    ) -> bool:
        """
        Gửi cảnh báo giá sản phẩm theo dõi:
        - TOUCH_TARGET: giá thực tính <= target_price
        - NEAR_TARGET: giá thực tính > target_price nhưng chênh lệch <= 300.000đ
        """
        safe_title = title.replace("<", "&lt;").replace(">", "&gt;")
        display_check_price = effective_price if effective_price > 0 else current_price
        curr_str = f"{int(current_price):,} ₫".replace(",", ".")
        eff_str = f"{int(display_check_price):,} ₫".replace(",", ".")
        target_str = f"{int(target_price):,} ₫".replace(",", ".")
        lowest_str = f"{int(lowest_price):,} ₫".replace(",", ".")
        diff = display_check_price - target_price
        diff_str = f"{int(abs(diff)):,} ₫".replace(",", ".")

        if alert_type == "TOUCH_TARGET":
            header = "🎯 <b>CHẠM GIÁ ĐÁY MỤC TIÊU!</b> 🎯"
            note = f"🎉 Giá sau áp voucher đã <b>bằng hoặc thấp hơn</b> giá đáy mong muốn! Rẻ hơn: <b>-{diff_str}</b>"
        else:
            header = "⚠️ <b>CẢNH BÁO: GẦN CHẠM GIÁ ĐÁY!</b> ⚠️"
            note = f"🔔 Giá sau áp voucher chỉ còn cách giá đáy <b>{diff_str}</b> (≤ 300.000 ₫)!"

        voucher_line = f"🎟️ <b>Mã giảm giá dự kiến:</b> <code>{discount_desc}</code>\n" if discount_desc else ""
        price_line = f"💵 <b>Giá web gốc:</b> <code>{curr_str}</code>\n"
        if discount_desc:
            price_line += f"📱 <b>Giá ước tính trên App (Sau mã):</b> <code>{eff_str}</code>\n"

        message = (
            f"{header}\n\n"
            f"📦 <b>Sản phẩm:</b> {safe_title}\n"
            f"{price_line}"
            f"{voucher_line}"
            f"🎯 <b>Giá đáy đặt:</b> <code>{target_str}</code>\n"
            f"📉 <b>Thấp nhất lịch sử:</b> <code>{lowest_str}</code>\n\n"
            f"{note}\n\n"
            f"👉 <a href=\"{link}\">Truy cập mua ngay trên Lazada/Tmall</a>"
        )
        return self.send_message(message)

