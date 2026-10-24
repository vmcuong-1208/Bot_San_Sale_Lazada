import re
import time
import requests
from typing import Dict, List, Optional
from src.crawlers.browser_setup import ensure_playwright_browsers

class PriceScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless

    def _extract_price_from_text(self, text: str) -> Optional[float]:
        """Bóc tách số tiền từ chuỗi (ví dụ: '150.000 ₫', '₫ 250,000')."""
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

    def _resolve_real_url(self, url: str) -> str:
        """Tự động phân giải link rút gọn (như s.lazada.vn) sang link sản phẩm gốc."""
        if "s.lazada.vn" in url:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                r = requests.get(url, headers=headers, timeout=10)
                html = r.text
                p1 = html.find("https://www.lazada.vn/products/")
                if p1 != -1:
                    p2 = html.find(".html", p1)
                    if p2 != -1:
                        real_url = html[p1:p2 + 5]
                        print(f"[SCRAPER] Đã chuyển đổi shortlink s.lazada sang link gốc: {real_url}")
                        return real_url
            except Exception as e:
                print(f"[WARN] Lỗi resolve shortlink: {e}")
        return url

    def _scrape_via_requests(self, url: str) -> Dict:
        """
        Phương pháp cào nhanh bằng requests (0.5 giây):
        - Không bị chặn Access denied bởi Cloudflare / Lazada Bot Detection.
        - Trích xuất OG Title, giá và danh sách phân loại (properties) từ SSR HTML.
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        r = requests.get(url, headers=headers, timeout=15)
        html = r.text

        title = ""
        m_title = re.search(r'<meta\s+property=[\'"]og:title[\'"]\s+content=[\'"]([^\'"]+)[\'"]', html)
        if m_title:
            title = m_title.group(1).replace(" | Lazada Việt Nam", "").strip()

        price = 0.0
        # Tìm giá tiền trong HTML
        m_price = re.search(r'\"price\":\s*\"?(\d+(?:\.\d+)?)\"?', html)
        if not m_price:
            m_price = re.search(r'\"salePrice\":\s*\"?(\d+(?:\.\d+)?)\"?', html)
        if not m_price:
            m_price = re.search(r'(\d{1,3}(?:\.\d{3})+)\s*₫', html)
            if m_price:
                price = float(m_price.group(1).replace(".", ""))
        else:
            price = float(m_price.group(1))

        # Trích xuất danh sách phân loại (SKUs) từ trường properties trong JSON SSR
        variants = []
        idx = html.find('"properties":')
        if idx != -1:
            sub = html[idx:idx + 5000]
            # Trích xuất các tên phân loại bên trong values
            v_matches = re.findall(r'\"name\":\s*\"([^\"]+)\"', sub)
            for v in v_matches:
                v_clean = v.strip()
                if v_clean and v_clean not in ["Màu sắc", "Nhóm màu", "Size", "Kích cỡ", "Phân loại"] and v_clean not in variants:
                    variants.append(v_clean)

        return {
            "title": title,
            "price": price,
            "variants": variants,
            "success": bool(title and title != "Access denied")
        }

    def scrape_product_info(self, url: str) -> Dict:
        """
        Cào thông tin tiêu đề, giá và phân loại của sản phẩm.
        Hỗ trợ cả link rút gọn s.lazada.vn và link gốc.
        Áp dụng Ponytail: Ưu tiên requests siêu nhanh; chỉ fallback Playwright nếu cần.
        """
        # 1. Chuẩn hoá link (giải mã s.lazada.vn)
        real_url = self._resolve_real_url(url)

        # 2. Thử cào nhanh bằng requests trước (vượt qua hoàn toàn Access denied)
        try:
            fast_res = self._scrape_via_requests(real_url)
            if fast_res["success"]:
                return {
                    "title": fast_res["title"],
                    "price": fast_res["price"],
                    "variants": fast_res["variants"],
                    "success": True,
                    "error": None
                }
        except Exception as e:
            print(f"[FAST SCRAPER WARN] {e}")

        # 3. Fallback: Dùng Playwright Headless với Stealth
        ensure_playwright_browsers()
        result = {
            "title": "",
            "price": 0.0,
            "variants": [],
            "success": False,
            "error": None
        }

        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-blink-features=AutomationControlled"
                    ]
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1440, "height": 900},
                    locale="vi-VN"
                )
                page = context.new_page()

                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    window.chrome = { runtime: {} };
                    Object.defineProperty(navigator, 'languages', { get: () => ['vi-VN', 'vi', 'en-US', 'en'] });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                """)

                page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["media", "font"] else route.continue_())

                try:
                    page.goto(real_url, wait_until="networkidle", timeout=30000)
                except Exception:
                    page.goto(real_url, wait_until="load", timeout=30000)
                time.sleep(1)

                title = ""
                title_el = page.query_selector("h1.pdp-mod-product-badge-title, h1[class*='pdp-mod-product-badge'], h1.tb-main-title, .ItemHeader--title--1-y3bA9, h1")
                if title_el:
                    title = title_el.inner_text().strip()
                if not title:
                    title = page.title()
                title = re.sub(r'[\r\n\t]+', ' ', title).strip()

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
                        p_extracted = self._extract_price_from_text(txt)
                        if p_extracted and p_extracted > 100:
                            price_val = p_extracted
                            break
                    if price_val > 0:
                        break

                if price_val == 0.0:
                    body_text = page.inner_text("body")
                    m = re.findall(r'(\d{1,3}(?:[.,]\d{3})+)\s*[₫đ]', body_text)
                    if m:
                        clean = m[0].replace(".", "").replace(",", "")
                        price_val = float(clean)

                variants = []
                try:
                    sku_elements = page.query_selector_all(
                        ".sku-variable-size, .sku-prop-content, .sku-name, [class*='sku-variable'], [class*='skuProp'], .sku-item"
                    )
                    seen_sku = set()
                    for el in sku_elements:
                        v_name = el.inner_text().strip().split("\n")[0].strip()
                        if v_name and len(v_name) < 50 and v_name not in seen_sku and not v_name.startswith("₫"):
                            seen_sku.add(v_name)
                            variants.append(v_name)
                except Exception:
                    pass

                result["title"] = title if title else "Sản phẩm Lazada/Tmall"
                result["price"] = price_val
                result["variants"] = variants
                result["success"] = (price_val > 0 and title != "Access denied")
                browser.close()

        except Exception as e:
            result["error"] = str(e)
            print(f"[SCRAPER ERROR] {e}")

        return result
