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
from src.crawlers.browser_setup import ensure_playwright_browsers

# 1. Cấu hình trang Streamlit chuẩn Modern SaaS
st.set_page_config(
    page_title="Lazada / Tmall Price Tracker",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Khởi tạo DB, Background Service & Browser check
db.init_db()
ensure_playwright_browsers()
monitor = get_monitor_service(interval_seconds=SCAN_INTERVAL_SECONDS)
notifier = TelegramNotifier()

# 3. Modern SaaS Custom CSS (Phong cách Nutlope / Vercel Minimalist)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /* Layout Spacing */
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
        max-width: 1240px;
    }

    /* SaaS Header */
    .saas-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 1.2rem;
        border-bottom: 1px solid #f1f3f5;
        margin-bottom: 1.5rem;
    }
    .saas-title {
        font-size: 1.65rem;
        font-weight: 700;
        color: #111827;
        letter-spacing: -0.025em;
        margin: 0;
    }
    .saas-subtitle {
        font-size: 0.9rem;
        color: #6b7280;
        margin-top: 0.25rem;
    }

    /* Metric Card Modern */
    .metric-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.15rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .metric-card:hover {
        border-color: #d1d5db;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        transform: translateY(-1px);
    }
    .metric-label {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #6b7280;
        margin-bottom: 0.35rem;
    }
    .metric-value {
        font-size: 1.65rem;
        font-weight: 700;
        color: #111827;
        letter-spacing: -0.02em;
        line-height: 1.1;
    }
    .metric-sub {
        font-size: 0.78rem;
        color: #9ca3af;
        margin-top: 0.35rem;
    }

    /* Status Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        line-height: 1;
        letter-spacing: 0.01em;
    }
    .badge-success {
        background-color: #ecfdf5;
        color: #059669;
        border: 1px solid #a7f3d0;
    }
    .badge-warning {
        background-color: #fffbeb;
        color: #d97706;
        border: 1px solid #fde68a;
    }
    .badge-neutral {
        background-color: #f3f4f6;
        color: #4b5563;
        border: 1px solid #e5e7eb;
    }
    .badge-danger {
        background-color: #fef2f2;
        color: #dc2626;
        border: 1px solid #fecaca;
    }

    /* Form Container */
    .form-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.5rem;
    }

    /* Primary & Secondary Buttons Style */
    button[kind="primary"] {
        background-color: #111827 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        border: none !important;
        transition: all 0.15s ease-in-out !important;
    }
    button[kind="primary"]:hover {
        background-color: #000000 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    }
    button[kind="secondary"] {
        border-radius: 8px !important;
        border: 1px solid #e5e7eb !important;
        font-weight: 500 !important;
        transition: all 0.15s ease-in-out !important;
    }
    button[kind="secondary"]:hover {
        border-color: #111827 !important;
        color: #111827 !important;
    }
</style>
""", unsafe_allow_html=True)

# 4. Sidebar: Telegram Bot & Background Scanner
with st.sidebar:
    st.markdown("### ⚡ **Điều Khiển Hệ Thống**")
    
    # Tùy chọn Tự động làm mới dữ liệu (Live Auto-refresh)
    auto_refresh = st.toggle("⏱️ Tự động cập nhật Web (10s)", value=True, help="Tự động đồng bộ số liệu mới nhất từ Supabase Cloud mỗi 10 giây cùng nhịp với Worker")

    # Hiển thị trạng thái kết nối Database (Supabase vs SQLite)
    if db.is_using_supabase():
        st.markdown('<span class="badge badge-success">● Supabase Cloud DB</span>', unsafe_allow_html=True)
        st.caption("Đồng bộ Realtime giữa Web Cloud & Worker nhà.")
    else:
        st.markdown('<span class="badge badge-warning">● SQLite Cục Bộ</span>', unsafe_allow_html=True)
        st.caption("Thêm SUPABASE_URL vào Secrets để bật Hybrid mode.")

    st.markdown("<hr style='margin: 0.8rem 0; border: none; border-top: 1px solid #f1f3f5;'/>", unsafe_allow_html=True)

    # Telegram Status Pill
    is_tg_ok = notifier.is_configured()
    if is_tg_ok:
        st.markdown('<span class="badge badge-success">● Telegram Connected</span>', unsafe_allow_html=True)
        st.caption("Đang kết nối: `@SaleLaz_bot`")
        if st.button("🧪 Bắn tin kiểm tra", use_container_width=True, type="secondary"):
            res = notifier.test_connection()
            if res.get("ok"):
                notifier.send_message("⚡ <b>[System Check]</b>: Kết nối thành công tới Telegram Bot!")
                st.success("Đã gửi tin nhắn test đến Telegram!")
            else:
                st.error(f"Lỗi: {res.get('description')}")
    else:
        st.markdown('<span class="badge badge-warning">● Dry-run (Chưa set token)</span>', unsafe_allow_html=True)
        st.caption("Khai báo `TELEGRAM_BOT_TOKEN` trong Secrets/env.")

    st.markdown("<hr style='margin: 1.2rem 0; border: none; border-top: 1px solid #f1f3f5;'/>", unsafe_allow_html=True)
    st.markdown("### 🔄 **Bộ Quét Tự Động**")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if not monitor.is_running:
            if st.button("▶️ Bắt đầu", use_container_width=True, type="primary"):
                monitor.start_background_loop()
                st.rerun()
        else:
            if st.button("⏹️ Tạm dừng", use_container_width=True, type="secondary"):
                monitor.stop_background_loop()
                st.rerun()

    with col_s2:
        if st.button("🚀 Quét ngay", use_container_width=True, type="secondary"):
            with st.spinner("Đang quét giá toàn bộ..."):
                monitor.scan_all_products()
            st.success("Quét hoàn tất!")
            st.rerun()

    task_status_badge = (
        '<span class="badge badge-success">Đang chạy ngầm</span>' 
        if monitor.is_running 
        else '<span class="badge badge-neutral">Đang tạm dừng</span>'
    )
    st.markdown(f"<div style='margin-top: 0.5rem;'><b>Trạng thái:</b> {task_status_badge}</div>", unsafe_allow_html=True)
    st.caption(f"Lần quét gần nhất: {monitor.last_run_time}")

    # Chức năng tự động xóa sản phẩm lỗi khi quét
    monitor.auto_delete_invalid = st.toggle("🗑️ Tự động xóa nếu link lỗi", value=monitor.auto_delete_invalid, help="Tự động loại bỏ sản phẩm khỏi hệ thống nếu không còn tồn tại hoặc lỗi lấy giá")

    st.markdown("<hr style='margin: 1.2rem 0; border: none; border-top: 1px solid #f1f3f5;'/>", unsafe_allow_html=True)
    with st.expander("📜 **Nhật ký hệ thống (Logs)**", expanded=False):
        if monitor.scan_logs:
            st.code("\n".join(monitor.scan_logs[-15:]), language="text")
        else:
            st.caption("Chưa có nhật ký hoạt động.")

# 5. Header & Overview
c_head1, c_head2 = st.columns([4, 1])
with c_head1:
    st.markdown("""
    <div class="saas-header" style="border-bottom: none; margin-bottom: 0;">
        <div>
            <h1 class="saas-title">⚡ Price Tracker Dashboard</h1>
            <div class="saas-subtitle">Giám sát và tự động cảnh báo biến động giá sàn Lazada / Tmall theo thời gian thực.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
with c_head2:
    st.write("")
    if st.button("🔄 Làm mới bảng", type="secondary", use_container_width=True, help="Tải lại dữ liệu mới nhất từ Supabase Cloud mà không cần F5"):
        st.rerun()

st.markdown("<hr style='margin: 0.5rem 0 1.5rem 0; border: none; border-top: 1px solid #f1f3f5;'/>", unsafe_allow_html=True)

# Lấy dữ liệu sản phẩm
products = db.get_all_products()
total_products = len(products)
touch_target_cnt = sum(1 for p in products if p.get("current_price", 0) > 0 and p.get("current_price", 0) <= p.get("target_price", 0))
near_target_cnt = sum(1 for p in products if p.get("current_price", 0) > p.get("target_price", 0) and (p.get("current_price", 0) - p.get("target_price", 0)) <= PRICE_DIFF_ALERT_THRESHOLD)

# 6. Metric Cards chuẩn Nutlope SaaS
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Tổng sản phẩm</div>
        <div class="metric-value">{total_products}</div>
        <div class="metric-sub">Đang trong danh sách theo dõi</div>
    </div>
    """, unsafe_allow_html=True)

with col_m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label" style="color: #059669;">🎉 Đạt giá đáy</div>
        <div class="metric-value" style="color: #059669;">{touch_target_cnt}</div>
        <div class="metric-sub">Giá ≤ Target Price (Mua ngay)</div>
    </div>
    """, unsafe_allow_html=True)

with col_m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label" style="color: #d97706;">⚠️ Gần chạm đáy</div>
        <div class="metric-value" style="color: #d97706;">{near_target_cnt}</div>
        <div class="metric-sub">Chênh lệch ≤ {int(PRICE_DIFF_ALERT_THRESHOLD/1000)}k VNĐ</div>
    </div>
    """, unsafe_allow_html=True)

with col_m4:
    freq_display = f"{monitor.interval_seconds} giây" if monitor.interval_seconds < 60 else f"{monitor.interval_seconds // 60} phút"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Chu kỳ quét</div>
        <div class="metric-value">{freq_display}</div>
        <div class="metric-sub">{monitor.last_run_time}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# 7. Form Thêm Sản Phẩm Mới (Thiết kế tinh gọn chuẩn Ponytail & SaaS)
with st.expander("➕ **Thêm sản phẩm mới cần theo dõi**", expanded=(total_products == 0)):
    with st.form("add_product_unified_form", clear_on_submit=True):
        f_url = st.text_input(
            "🔗 Link sản phẩm (Lazada / Tmall / Taobao):",
            placeholder="https://s.lazada.vn/... hoặc https://www.lazada.vn/products/..."
        )
        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
        with col_f1:
            f_title = st.text_input(
                "📦 Ghi chú tên sản phẩm (tùy chọn):",
                placeholder="Để trống Worker sẽ tự lấy tên thật trên sàn..."
            )
        with col_f2:
            f_variant = st.text_input(
                "🎨 Phân loại cần săn (tùy chọn):",
                placeholder="Ví dụ: Màu Đen, Size L..."
            )
        with col_f3:
            f_target = st.number_input(
                "🎯 Giá đáy mong muốn (VNĐ):",
                min_value=1000,
                value=200000,
                step=10000,
                format="%d"
            )

        btn_save = st.form_submit_button("💾 Lưu vào danh sách theo dõi", type="primary", use_container_width=True)
        if btn_save:
            if not f_url or not f_url.startswith("http"):
                st.error("Vui lòng nhập đường link URL hợp lệ!")
            else:
                final_title = f_title.strip() if f_title.strip() else "Sản phẩm mới (Đang chờ Worker quét)"
                prod_id = db.add_product(
                    url=f_url.strip(),
                    target_price=float(f_target),
                    title=final_title,
                    current_price=0.0,
                    variant_name=f_variant.strip()
                )
                st.success(f"🎉 Đã lưu sản phẩm thành công vào Supabase (ID: #{prod_id})!")
                st.rerun()

# 8. Bảng danh sách sản phẩm
col_tbl1, col_tbl2 = st.columns([3, 1])
with col_tbl1:
    st.markdown("### 📋 **Danh Sách Sản Phẩm Theo Dõi**")
with col_tbl2:
    if products and any("Lỗi" in (p.get("status") or "") for p in products):
        if st.button("🧹 Dọn sạch sản phẩm lỗi", type="secondary", use_container_width=True, help="Xóa ngay tất cả sản phẩm bị lỗi link hoặc không thể cào giá"):
            deleted = db.delete_invalid_products()
            st.success(f"Đã xóa {deleted} sản phẩm lỗi!")
            st.rerun()

if not products:
    st.info("Chưa có sản phẩm nào. Hãy bấm **Thêm sản phẩm mới** ở trên để bắt đầu theo dõi.")
else:
    def format_badge_status(status_raw: str) -> str:
        s = status_raw or ""
        if "ĐẠT GIÁ ĐÁY" in s or "Thành công" in s:
            return f"🟢 {s}"
        elif "Gần chạm đáy" in s or "Chênh" in s:
            return f"🟡 {s}"
        elif "Lỗi" in s:
            return f"🔴 {s}"
        return f"⚪ {s}"

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
            "Sản phẩm": p["title"] or "Chưa cập nhật",
            "Phân loại": p.get("variant_name") or "Mặc định",
            "Giá hiện tại": curr_str,
            "Giá đáy (Target)": targ_str,
            "Chênh lệch": diff_str,
            "Thấp nhất": low_str,
            "Trạng thái": format_badge_status(p["status"]),
            "Lần cập nhật": p["last_checked"] or "Chưa cập nhật",
            "URL": p["url"]
        })

    df = pd.DataFrame(table_data)

    st.dataframe(
        df,
        column_config={
            "URL": st.column_config.LinkColumn("Link mua hàng", display_text="Truy cập"),
            "Sản phẩm": st.column_config.TextColumn(width="medium"),
            "Phân loại": st.column_config.TextColumn(width="small"),
            "Trạng thái": st.column_config.TextColumn(width="small"),
            "Chênh lệch": st.column_config.TextColumn(width="small"),
        },
        hide_index=True,
        use_container_width=True
    )

    # 9. Quản lý sản phẩm (Xóa / Chỉnh sửa giá đáy)
    st.markdown("##### ⚙️ **Quản lý sản phẩm**")
    col_act1, col_act2, col_act3 = st.columns([2, 1, 1])
    product_options = {f"#{p['id']} - {p['title'][:35]}... ({int(p['target_price']):,}đ)": p["id"] for p in products}

    with col_act1:
        selected_label = st.selectbox("Chọn sản phẩm cần chỉnh sửa:", list(product_options.keys()))
        selected_id = product_options[selected_label]

    with col_act2:
        current_prod = db.get_product_by_id(selected_id)
        current_target = int(current_prod["target_price"]) if current_prod else 100000
        new_target = st.number_input("Cập nhật lại Giá đáy (VNĐ):", min_value=1000, step=10000, value=current_target)
        if st.button("💾 Cập nhật giá", use_container_width=True, type="secondary"):
            db.update_target_price(selected_id, float(new_target))
            st.success("Đã cập nhật giá đáy thành công!")
            st.rerun()

    with col_act3:
        st.write("")
        st.write("")
        if st.button("🗑️ Xoá sản phẩm", use_container_width=True, type="secondary"):
            db.delete_product(selected_id)
            st.warning("Đã xoá khỏi danh sách!")
            st.rerun()

# 10. Tự động đồng bộ số liệu thời gian thực (Ponytail 1-line timer)
if auto_refresh:
    import time
    time.sleep(10)
    st.rerun()
