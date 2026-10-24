import re
import time
from typing import List, Dict
from playwright.sync_api import sync_playwright

class FlashSaleCrawler:
    LAZADA_HOME_URL = "https://www.lazada.vn/#?"
    LAZFLASH_URL = "https://pages.lazada.vn/wow/gcp/route/lazada/vn/upr_1000345_lazada/channel/vn/upr-router/vn?wh_pid=/lazada/channel/vn/shopping-guide/lazflash"

    def __init__(self, headless: bool = True):
        self.headless = headless

    def _parse_raw_text(self, text: str, href: str) -> Dict:
        """Phân tích văn bản của card để trích xuất title, giá mới, giá cũ, và % giảm."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            return None

        # 1. Tìm % giảm
        discount_val = 0
        discount_match = re.search(r'-(\d+)%', text)
        if discount_match:
            discount_val = int(discount_match.group(1))

        # 2. Tìm giá tiền
        price_lines = [l for l in lines if '₫' in l]
        prices = []
        for pl in price_lines:
            matches = re.findall(r'(\d{1,3}(?:[.,]\d{3})+)\s*₫?', pl)
            for m in matches:
                p_clean = m.strip() + " ₫"
                if p_clean not in prices:
                    prices.append(p_clean)

        if not prices:
            for line in lines:
                matches = re.findall(r'(\d{1,3}(?:[.,]\d{3})+)', line)
                for m in matches:
                    p_clean = m.strip() + " ₫"
                    if p_clean not in prices:
                        prices.append(p_clean)

        price = prices[0] if len(prices) > 0 else "N/A"
        original_price = prices[1] if len(prices) > 1 else "N/A"

        # 3. Tên sản phẩm
        title = ""
        for line in lines:
            if not re.search(r'^\d', line) and not re.search(r'^-\d+%', line) and '₫' not in line:
                title = line
                break
        if not title and len(lines) > 0:
            title = lines[0]

        # 4. Chuẩn hoá URL
        clean_link = href
        if clean_link.startswith("//"):
            clean_link = "https:" + clean_link

        return {
            "title": title,
            "price": price,
            "original_price": original_price,
            "discount": discount_val,
            "link": clean_link
        }

    def fetch_flash_sale_products(self) -> List[Dict]:
        """Crawl danh sách sản phẩm Flash Sale từ Lazada bằng Playwright."""
        products = []
        seen_links = set()

        with sync_playwright() as p:
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

            # Kênh LazFlash channel chuyên biệt
            print("[INFO] Đang truy cập kênh LazFlash chuyên biệt...")
            try:
                page.goto(self.LAZFLASH_URL, wait_until="networkidle", timeout=45000)
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 1000);")
                    time.sleep(1)

                raw_items = page.evaluate("""() => {
                    const res = [];
                    const links = Array.from(document.querySelectorAll('a[href*="/products/"]'));
                    for (const a of links) {
                        const txt = a.innerText.trim();
                        if (txt && (txt.includes('₫') || txt.includes('%'))) {
                            res.push({ href: a.href, text: txt });
                        }
                    }
                    return res;
                }""")

                for it in raw_items:
                    parsed = self._parse_raw_text(it["text"], it["href"])
                    if parsed and parsed["link"] not in seen_links:
                        seen_links.add(parsed["link"])
                        products.append(parsed)

                print(f"[INFO] Tìm thấy {len(products)} sản phẩm từ LazFlash channel.")
            except Exception as e:
                print(f"[WARN] Lỗi khi tải LazFlash channel: {e}")

            # Bổ sung từ trang chủ Lazada nếu cần
            if len(products) < 5:
                print("[INFO] Truy cập trang chủ Lazada để lấy Deal Chớp Nhoáng...")
                try:
                    page.goto(self.LAZADA_HOME_URL, wait_until="networkidle", timeout=45000)
                    time.sleep(2)
                    page.evaluate("window.scrollBy(0, 800);")
                    time.sleep(1)

                    raw_home_items = page.evaluate("""() => {
                        const res = [];
                        const units = Array.from(document.querySelectorAll('.card-fs-content-body-unit, #js_flashSale a[href*="/products/"]'));
                        for (const u of units) {
                            const a = u.tagName === 'A' ? u : u.querySelector('a');
                            const href = a ? a.href : '';
                            const txt = u.innerText.trim();
                            if (txt) {
                                res.push({ href: href, text: txt });
                            }
                        }
                        return res;
                    }""")

                    for it in raw_home_items:
                        parsed = self._parse_raw_text(it["text"], it["href"])
                        if parsed and parsed["link"] not in seen_links:
                            seen_links.add(parsed["link"])
                            products.append(parsed)

                    print(f"[INFO] Tổng số sản phẩm sau khi quét trang chủ: {len(products)}")
                except Exception as e:
                    print(f"[WARN] Lỗi khi tải trang chủ Deal Chớp Nhoáng: {e}")

            browser.close()

        return products

