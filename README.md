# Lazada & Tmall Price Tracker Dashboard 🛒

Web Dashboard quản lý, theo dõi biến động giá sản phẩm Lazada / Tmall, lưu trữ SQLite và tự động quét giá định kỳ bằng Playwright, gửi cảnh báo qua Telegram Bot.

---

## 📁 Cấu trúc thư mục chuẩn chuyên nghiệp (Clean Architecture)

```text
Build Tools Lazada/
├── data/                               # Dữ liệu ứng dụng
│   └── products.db                     # SQLite database lưu sản phẩm & lịch sử giá
│
├── src/                                # Mã nguồn chính (Source code)
│   ├── __init__.py
│   ├── config/                         # Cấu hình hệ thống & môi trường
│   │   ├── __init__.py
│   │   └── settings.py                 # Đọc cấu hình từ .env, đường dẫn DB, ngưỡng báo giá
│   │
│   ├── database/                       # Tầng cơ sở dữ liệu (Data Access Layer)
│   │   ├── __init__.py
│   │   └── db.py                       # CRUD sản phẩm, cập nhật giá và trạng thái
│   │
│   ├── crawlers/                       # Tầng thu thập dữ liệu (Playwright Crawlers)
│   │   ├── __init__.py
│   │   ├── flash_sale_crawler.py       # Crawler bóc tách deal Flash Sale Lazada
│   │   └── price_scraper.py            # Scraper cào giá và tiêu đề sản phẩm chi tiết
│   │
│   ├── notifications/                  # Tầng thông báo (Notification Services)
│   │   ├── __init__.py
│   │   └── telegram.py                 # Telegram Bot API client gửi alert giá & sale
│   │
│   └── services/                       # Tầng nghiệp vụ (Business Logic Services)
│       ├── __init__.py
│       └── monitor_service.py          # Background task theo dõi và so khớp giá định kỳ
│
├── .env                                # Biến môi trường (Token, Chat ID, Ngưỡng giá)
├── .env.example                        # File mẫu hướng dẫn điền .env
├── requirements.txt                    # Thư viện phụ thuộc
├── app.py                              # Entry point chạy Web Dashboard (Streamlit)
├── main.py                             # Entry point chạy quét Flash Sale tự động (CLI)
└── README.md                           # Tài liệu hướng dẫn sử dụng
```

---

## 🌟 Chức năng nổi bật

1. **Giao diện Web Streamlit hiện đại**:
   - Form thêm sản phẩm: Nhập Link sản phẩm và Giá đáy mong muốn (Target Price).
   - Bảng danh sách trực quan: Hiển thị Tên sản phẩm, Giá hiện tại, Giá đáy, Chênh lệch, Giá thấp nhất lịch sử, Trạng thái và Link mua hàng.
   - Thao tác nhanh: Cập nhật giá đáy, quét lại ngay lập tức hoặc xoá sản phẩm.

2. **Cơ sở dữ liệu SQLite**:
   - Lưu trữ tự động trong `data/products.db`.
   - Các trường: `id`, `url`, `title`, `current_price`, `target_price`, `lowest_price`, `status`, `last_checked`, `created_at`.

3. **Logic Cào Giá & Cảnh Báo Telegram**:
   - Tự động chạy **Background Task** ngầm định kỳ bằng Playwright (Headless Chromium).
   - **Trường hợp 1**: `current_price <= target_price` $\rightarrow$ Gửi cảnh báo Telegram "Chạm giá đáy" và cập nhật `lowest_price` mới.
   - **Trường hợp 2**: `current_price > target_price`:
     - Nếu chênh lệch `(current_price - target_price) > 300.000` $\rightarrow$ Bỏ qua, không báo tin.
     - Nếu chênh lệch `(current_price - target_price) <= 300.000` $\rightarrow$ Gửi tin nhắn Telegram "Cảnh báo: Gần chạm giá đáy".

---

## 🚀 Hướng dẫn khởi chạy

### 1. Cài đặt môi trường
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Cấu hình Telegram Bot & Supabase (`.env`)
Tạo file `.env` (tham khảo `.env.example`) và điền thông tin của bạn:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
DISCOUNT_THRESHOLD=30
SCAN_INTERVAL_SECONDS=300

# Cấu hình Supabase (PostgreSQL Cloud)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-key-here
```

### 3. Khởi chạy Web Dashboard
```bash
streamlit run app.py
```
👉 Mở trình duyệt tại: **`http://localhost:8501`**

### 4. Khởi chạy kịch bản quét Flash Sale Lazada độc lập
```bash
python main.py
```
