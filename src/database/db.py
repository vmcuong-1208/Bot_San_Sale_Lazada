import sqlite3
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
from src.config.settings import DB_PATH

VN_TZ = timezone(timedelta(hours=7))

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            variant_name TEXT DEFAULT '',
            current_price REAL DEFAULT 0,
            target_price REAL NOT NULL,
            lowest_price REAL DEFAULT 0,
            status TEXT DEFAULT 'Đang theo dõi',
            last_checked TEXT,
            created_at TEXT
        )
    """)
    # Migration an toàn: Tự động bổ sung cột variant_name nếu database cũ chưa có
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN variant_name TEXT DEFAULT ''")
    except Exception:
        pass  # Cột đã tồn tại, bỏ qua an toàn
    conn.commit()
    conn.close()

def add_product(url: str, target_price: float, title: str = "", current_price: float = 0.0, variant_name: str = "") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    lowest_price = current_price if current_price > 0 else target_price
    cursor.execute("""
        INSERT INTO products (url, title, variant_name, current_price, target_price, lowest_price, status, last_checked, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'Đang theo dõi', ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            title = excluded.title,
            variant_name = excluded.variant_name,
            target_price = excluded.target_price,
            status = 'Đang theo dõi'
    """, (url, title, variant_name, current_price, target_price, lowest_price, now_str, now_str))
    product_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return product_id

def get_all_products() -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY id DESC")
    rows = cursor.fetchall()
    results = [dict(row) for row in rows]
    conn.close()
    return results

def get_product_by_id(product_id: int) -> Optional[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_product_price(product_id: int, title: str, current_price: float, lowest_price: float, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE products
        SET title = COALESCE(NULLIF(?, ''), title),
            current_price = ?,
            lowest_price = ?,
            status = ?,
            last_checked = ?
        WHERE id = ?
    """, (title, current_price, lowest_price, status, now_str, product_id))
    conn.commit()
    conn.close()

def update_target_price(product_id: int, target_price: float):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET target_price = ? WHERE id = ?", (target_price, product_id))
    conn.commit()
    conn.close()

def delete_product(product_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

def delete_invalid_products() -> int:
    """Xóa tất cả các sản phẩm có trạng thái lỗi link hoặc lỗi cào giá."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE status LIKE '%Lỗi%'")
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count

