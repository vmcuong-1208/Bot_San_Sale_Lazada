import os
import subprocess
import threading

_installed_lock = threading.Lock()
_is_installed = False

def ensure_playwright_browsers():
    """
    Kiểm tra và tự động cài đặt chromium browser cho Playwright
    khi chạy trên Linux/Streamlit Cloud nếu chưa cài đặt.
    (Áp dụng chuẩn Ponytail: kiểm tra 1 lần an toàn, không block vô cớ).
    """
    global _is_installed
    if _is_installed:
        return

    with _installed_lock:
        if _is_installed:
            return
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                # Thử khởi chạy kiểm tra xem đã có executable chưa
                try:
                    b = p.chromium.launch(headless=True)
                    b.close()
                    _is_installed = True
                    return
                except Exception:
                    pass
            
            print("[PLAYWRIGHT] Trình duyệt Chromium chưa có sẵn. Đang tự động cài đặt...")
            cmd = ["playwright", "install", "chromium"]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            print("[PLAYWRIGHT] Cài đặt Chromium thành công!")
            _is_installed = True
        except Exception as e:
            print(f"[PLAYWRIGHT WARNING] Không thể tự động chạy playwright install: {e}")

