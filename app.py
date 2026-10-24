import sys
from pathlib import Path

# Đảm bảo nhận diện package src khi chạy từ bất kỳ đâu
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
import src.database as db
from src.services.monitor_service import get_monitor_service
from src.notifications.telegram import TelegramNotifier
from src.config.settings import SCAN_INTERVAL_SECONDS, PRICE_DIFF_ALERT_THRESHOLD

# 1. Cấu hình trang Streamlit
st.set_page_config(
    page_title="Lazada/Tmall Price Tracker",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Khởi tạo DB & Background Service
db.init_db()
monitor = get_monitor_service(interval_seconds=SCAN_INTERVAL_SECONDS)
notifier = TelegramNotifier()

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #e9ecef;
    }
</style>
""", unsafe_allow_html=True)

# 3. Sidebar: Quản lý Background Task & Telegram Bot
with st.sidebar:
    st.header("🤖 Cài đặt Telegram Bot")
    is_tg_ok = notifier.is_configured()
    if is_tg_ok:
        st.success("✅ Telegram Bot đã cấu hình")
        if st.button("🧪 Kiểm tra kết nối Telegram"):
            res = notifier.test_connection()
            if res.get("ok"):
                bot_user = res.get("result", {}).get("username")
                st.success(f"Kết nối thành công tới: @{bot_user}")
                notifier.send_message("🔔 <b>[Dashboard Test]</b>: Kết nối thành công tới Telegram Bot!")
                st.info("Đã gửi tin nhắn test đến Telegram của bạn.")
            else:
                st.error(f"Lỗi: {res.get('description')}")
    else:
        st.warning("⚠️ Chưa cấu hình Token hoặc Chat ID trong file `.env` (Đang ở chế độ Dry-run/Mô phỏng).")

    st.markdown("---")
    st.header("⚡ Background Task Quét Giá")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if not monitor.is_running:
            if st.button("▶️ Khởi động quét", use_container_width=True, type="primary"):
                monitor.start_background_loop()
                st.rerun()
        else:
            if st.button("⏹️ Tạm dừng quét", use_container_width=True):
                monitor.stop_background_loop()
                st.rerun()

    with col_s2:
        if st.button("🔄 Quét ngay", use_container_width=True):
            with st.spinner("Đang quét tất cả sản phẩm..."):
                monitor.scan_all_products()
            st.success("Đã hoàn thành quét!")
            st.rerun()

    status_icon = "🟢 Đang chạy" if monitor.is_running else "⚪ Đang dừng"
    st.write(f"**Trạng thái task:** {status_icon}")
    st.write(f"**Lần quét gần nhất:** {monitor.last_run_time}")

    st.markdown("---")
    st.subheader("📜 Nhật ký hoạt động")
    if monitor.scan_logs:
        st.code("\n".join(monitor.scan_logs[-10:]), language="text")
    else:
        st.caption("Chưa có nhật ký.")

# 4. Giao diện chính
st.title("🛒 Dashboard Quản Lý & Săn Giá Lazada / Tmall")
st.caption(f"Tự động theo dõi biến động giá, phát hiện giá chạm đáy hoặc gần chạm đáy (<= {int(PRICE_DIFF_ALERT_THRESHOLD):,}đ) và gửi cảnh báo Telegram tức thì.")

# Thống kê tổng quan
products = db.get_all_products()
total_products = len(products)
touch_target_cnt = sum(1 for p in products if p.get("current_price", 0) > 0 and p.get("current_price", 0) <= p.get("target_price", 0))
near_target_cnt = sum(1 for p in products if p.get("current_price", 0) > p.get("target_price", 0) and (p.get("current_price", 0) - p.get("target_price", 0)) <= PRICE_DIFF_ALERT_THRESHOLD)

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.metric("Tổng sản phẩm theo dõi", total_products)
with col_m2:
    st.metric("🎉 Đạt giá đáy (<= Target)", touch_target_cnt)
with col_m3:
    st.metric(f"⚠️ Gần chạm đáy (<= {int(PRICE_DIFF_ALERT_THRESHOLD/1000)}k)", near_target_cnt)
with col_m4:
    st.metric("Tần suất quét tự động", f"{monitor.interval_seconds // 60} phút")

st.markdown("---")

# 5. Form Thêm Sản Phẩm Mới
with st.expander("➕ **Thêm sản phẩm mới cần theo dõi giá**", expanded=(total_products == 0)):
    with st.form("add_product_form", clear_on_submit=True):
        f_url = st.text_input("🔗 Link sản phẩm (Lazada / Tmall / Taobao):", placeholder="https://www.lazada.vn/products/...")
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            f_target_price = st.number_input("🎯 Giá đáy mong muốn (VNĐ):", min_value=1000, value=100000, step=10000, format="%d")
        with col_f2:
            f_check_now = st.checkbox("Quét giá ngay khi thêm", value=True)

        submitted = st.form_submit_button("Lưu sản phẩm", type="primary")
        if submitted:
            if not f_url or not f_url.startswith("http"):
                st.error("Vui lòng nhập đường link URL hợp lệ!")
            else:
                prod_id = db.add_product(url=f_url.strip(), target_price=float(f_target_price))
                st.success(f"Đã thêm sản phẩm thành công (ID: #{prod_id})!")
                if f_check_now:
                    with st.spinner("Đang mở trình duyệt lấy giá và tiêu đề sản phẩm lần đầu..."):
                        p_data = db.get_product_by_id(prod_id)
                        monitor.check_single_product(p_data)
                st.rerun()

# 6. Bảng danh sách sản phẩm
st.subheader("📋 Danh Sách Sản Phẩm Theo Dõi")

if not products:
    st.info("Chưa có sản phẩm nào. Hãy bấm **Thêm sản phẩm mới** ở trên để bắt đầu theo dõi.")
else:
    table_data = []
    for p in products:
        c_price = p.get("current_price", 0)
        t_price = p.get("target_price", 0)
        l_price = p.get("lowest_price", 0)

        curr_str = f"{int(c_price):,} ₫".replace(",", ".") if c_price > 0 else "Chưa quét"
        targ_str = f"{int(t_price):,} ₫".replace(",", ".")
        low_str = f"{int(l_price):,} ₫".replace(",", ".") if l_price > 0 else "Chưa có"

        diff_str = "—"
        if c_price > 0:
            diff = c_price - t_price
            diff_str = f"+{int(diff):,} ₫".replace(",", ".") if diff > 0 else f"{int(diff):,} ₫".replace(",", ".")

        table_data.append({
            "ID": p["id"],
            "Tên sản phẩm": p["title"] or "Chưa cập nhật",
            "Giá hiện tại": curr_str,
            "Giá đáy (Target)": targ_str,
            "Chênh lệch": diff_str,
            "Thấp nhất lịch sử": low_str,
            "Trạng thái": p["status"],
            "Lần cập nhật": p["last_checked"] or "Chưa cập nhật",
            "URL": p["url"]
        })

    df = pd.DataFrame(table_data)

    st.dataframe(
        df,
        column_config={
            "URL": st.column_config.LinkColumn("Link mua hàng", display_text="Xem sản phẩm"),
            "Tên sản phẩm": st.column_config.TextColumn(width="medium"),
            "Trạng thái": st.column_config.TextColumn(width="small"),
        },
        hide_index=True,
        use_container_width=True
    )

    st.markdown("#### ⚙️ Thao tác trên sản phẩm")
    col_act1, col_act2, col_act3 = st.columns([2, 1, 1])
    product_options = {f"#{p['id']} - {p['title'][:40]}... ({int(p['target_price']):,}đ)": p["id"] for p in products}

    with col_act1:
        selected_label = st.selectbox("Chọn sản phẩm:", list(product_options.keys()))
        selected_id = product_options[selected_label]

    with col_act2:
        current_prod = db.get_product_by_id(selected_id)
        current_target = int(current_prod["target_price"]) if current_prod else 100000
        new_target = st.number_input("Cập nhật lại Giá đáy (Target):", min_value=1000, step=10000, value=current_target)
        if st.button("💾 Cập nhật giá đáy", use_container_width=True):
            db.update_target_price(selected_id, float(new_target))
            st.success("Đã cập nhật giá đáy!")
            st.rerun()

    with col_act3:
        st.write("")
        st.write("")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔍 Quét lại", use_container_width=True):
                with st.spinner("Đang quét giá..."):
                    p_data = db.get_product_by_id(selected_id)
                    res = monitor.check_single_product(p_data)
                st.success(f"Xong! Giá mới: {res.get('current_price', 0):,.0f}đ")
                st.rerun()
        with col_btn2:
            if st.button("🗑️ Xoá", use_container_width=True, type="secondary"):
                db.delete_product(selected_id)
                st.warning("Đã xoá sản phẩm!")
                st.rerun()
