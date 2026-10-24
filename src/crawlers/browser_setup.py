import os
import streamlit as st

@st.cache_resource(show_spinner="Đang thiết lập môi trường Chromium...")
def ensure_playwright_browsers():
    """
    Kiểm tra và tự động cài đặt chromium browser cho Playwright
    khi chạy trên Linux/Streamlit Cloud.
    Chuẩn Ponytail: 
    - Dùng @st.cache_resource để chỉ chạy DUY NHẤT 1 lần khi server boot.
    - Không chạy lại nhiều lần, không làm lag giao diện.
    """
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                b = p.chromium.launch(headless=True)
                b.close()
                return True
            except Exception:
                pass
        
        # Nếu chưa có binary thì install
        os.system("playwright install chromium")
        return True
    except Exception as e:
        print(f"[PLAYWRIGHT SETUP ERROR]: {e}")
        return False
