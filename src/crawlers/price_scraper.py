import re
import time
from typing import Dict, Optional
from playwright.sync_api import sync_playwright

class PriceScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless

    def _extract_price_from_text(self, text: str) -> Optional[float]:
        """Bóc tách số tiền từ chuỗi (ví dụ: '150.000 ₫', '¥99.00', '₫ 250,000')."""
        if not text:
            return None
        matches = re.findall(r'(\d{1,3}(?:[.,]\d{3})+|\d+)', text)
        for m in matches:
            clean = m.replace(".", "").replace(",", "")
            if clean.isdigit() and int(clean) > 0:
                val = float(clean)
                if val >= 100:
                    return val
        return None

    def scrape_product_info(self, url: str) -> Dict:
        """
        Cào thông tin tiêu đề và giá hiện tại của sản phẩm từ URL (Lazada / Tmall / Taobao).
        """
        result = {
            "title": "",
            "price": 0.0,
            "success": False,
            "error": None
        }

        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-blink-features=AutomationControlled"
                    ]
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1440, "height": 900}
                )
                page = context.new_page()

                # Chặn image/font thừa để tăng tốc tải trang
                page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())

                print(f"[SCRAPER] Đang tải trang: {url} ...")
                page.goto(url, wait_until="domcontentloaded", timeout=40000)
                time.sleep(2)

                # 1. Trích xuất Title
                title = ""
                title_el = page.query_selector("h1.pdp-mod-product-badge-title, h1[class*='pdp-mod-product-badge'], h1.tb-main-title, .ItemHeader--title--1-y3bA9, h1")
                if title_el:
                    title = title_el.inner_text().strip()
                if not title:
                    title = page.title()
                title = re.sub(r'[\r\n\t]+', ' ', title).strip()

                # 2. Trích xuất Price
                price_val = 0.0
                price_selectors = [
                    ".pdp-price_type_normal",
                    ".pdp-v2-product-price-content-sale-price",
                    ".pdp-price",
                    "[class*='pdp-price']",
                    ".tm-price",
                    ".ItemHeader--price--21XF90V",
                    "[class*='Price--priceText']"
                ]

                for sel in price_selectors:
                    els = page.query_selector_all(sel)
                    for el in els:
                        txt = el.inner_text()
                        p = self._extract_price_from_text(txt)
                        if p and p > 100:
                            price_val = p
                            break
                    if price_val > 0:
                        break

                if price_val == 0.0:
                    body_text = page.inner_text("body")
                    m = re.findall(r'(\d{1,3}(?:[.,]\d{3})+)\s*[₫đ]', body_text)
                    if m:
                        clean = m[0].replace(".", "").replace(",", "")
                        price_val = float(clean)

                result["title"] = title if title else "Sản phẩm Lazada/Tmall"
                result["price"] = price_val
                result["success"] = (price_val > 0)
                browser.close()

            except Exception as e:
                result["error"] = str(e)
                print(f"[SCRAPER ERROR] {e}")

        return result

