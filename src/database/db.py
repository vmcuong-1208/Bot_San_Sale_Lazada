import sqlite3
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
from src.config.settings import DB_PATH, SUPABASE_URL, SUPABASE_KEY

VN_TZ = timezone(timedelta(hours=7))

# Khởi tạo Supabase client nếu đã được cấu hình
_supabase_client = None
if SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL != "your_supabase_url_here":
    try:
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        try:
            print("[DATABASE] Dang su dung co so du lieu Supabase Cloud.")
        except Exception:
            pass
    except Exception as e:
        try:
            print(f"[DATABASE WARN] Fallback ve SQLite: {e}")
        except Exception:
            pass

def is_using_supabase() -> bool:
    return _supabase_client is not None

# ============================================================
# CÁC HÀM XỬ LÝ CHO SQLITE (FALLBACK CỤC BỘ)
# ============================================================
def _get_sqlite_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _init_sqlite():
    conn = _get_sqlite_conn()
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
            discount_amount REAL DEFAULT 0,
            discount_percent REAL DEFAULT 0,
            variants_json TEXT DEFAULT '[]',
            status TEXT DEFAULT 'Đang theo dõi',
            last_checked TEXT,
            created_at TEXT
        )
    """)
    for col in [
        "variant_name TEXT DEFAULT ''", 
        "discount_amount REAL DEFAULT 0", 
        "discount_percent REAL DEFAULT 0",
        "variants_json TEXT DEFAULT '[]'"
    ]:
        try:
            cursor.execute(f"ALTER TABLE products ADD COLUMN {col}")
        except Exception:
            pass
    conn.commit()
    conn.close()

# ============================================================
# GIAO DIỆN DATABASE THỐNG NHẤT (HYBRID ADAPTER)
# ============================================================
def init_db():
    """Khởi tạo database: Nếu dùng SQLite thì tạo bảng; Supabase đã có schema PostgreSQL."""
    if not is_using_supabase():
        _init_sqlite()

def add_product(
    url: str, 
    target_price: float, 
    title: str = "", 
    current_price: float = 0.0, 
    variant_name: str = "",
    discount_amount: float = 0.0,
    discount_percent: float = 0.0
) -> int:
    now_str = datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    lowest_price = current_price if current_price > 0 else target_price

    if is_using_supabase():
        # Kiểm tra xem sản phẩm đã có trong Supabase chưa (qua URL)
        res = _supabase_client.table("products").select("id").eq("url", url).execute()
        if res.data:
            prod_id = res.data[0]["id"]
            _supabase_client.table("products").update({
                "title": title,
                "variant_name": variant_name,
                "target_price": target_price,
                "discount_amount": discount_amount,
                "discount_percent": discount_percent,
                "status": "Đang theo dõi",
                "last_checked": now_str
            }).eq("id", prod_id).execute()
            return prod_id
        else:
            insert_res = _supabase_client.table("products").insert({
                "url": url,
                "title": title,
                "variant_name": variant_name,
                "current_price": current_price,
                "target_price": target_price,
                "lowest_price": lowest_price,
                "discount_amount": discount_amount,
                "discount_percent": discount_percent,
                "status": "Đang theo dõi",
                "last_checked": now_str,
                "created_at": now_str
            }).execute()
            return insert_res.data[0]["id"]
    else:
        conn = _get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO products (url, title, variant_name, current_price, target_price, lowest_price, discount_amount, discount_percent, status, last_checked, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Đang theo dõi', ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title = excluded.title,
                variant_name = excluded.variant_name,
                target_price = excluded.target_price,
                discount_amount = excluded.discount_amount,
                discount_percent = excluded.discount_percent,
                status = 'Đang theo dõi'
        """, (url, title, variant_name, current_price, target_price, lowest_price, discount_amount, discount_percent, now_str, now_str))
        prod_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return prod_id

def get_all_products() -> List[Dict]:
    if is_using_supabase():
        res = _supabase_client.table("products").select("*").order("id", desc=True).execute()
        return res.data or []
    else:
        conn = _get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products ORDER BY id DESC")
        rows = cursor.fetchall()
        results = [dict(row) for row in rows]
        conn.close()
        return results

def get_product_by_id(product_id: int) -> Optional[Dict]:
    if is_using_supabase():
        res = _supabase_client.table("products").select("*").eq("id", product_id).execute()
        return res.data[0] if res.data else None
    else:
        conn = _get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

def update_product_price(
    product_id: int, 
    title: str, 
    current_price: float, 
    lowest_price: float, 
    status: str, 
    variant_name: str = "",
    variants_json: Optional[List[Dict]] = None
):
    import json
    now_str = datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    if is_using_supabase():
        payload = {
            "current_price": current_price,
            "lowest_price": lowest_price,
            "status": status,
            "last_checked": now_str
        }
        if title:
            payload["title"] = title
        if variant_name:
            payload["variant_name"] = variant_name
        if variants_json is not None:
            payload["variants_json"] = variants_json
        try:
            _supabase_client.table("products").update(payload).eq("id", product_id).execute()
        except Exception as e:
            # Nếu Supabase chưa chạy SQL thêm cột variants_json, fallback cập nhật các trường cơ bản
            if "variants_json" in str(e):
                payload.pop("variants_json", None)
                _supabase_client.table("products").update(payload).eq("id", product_id).execute()
            else:
                raise e
    else:
        conn = _get_sqlite_conn()
        cursor = conn.cursor()
        v_json_str = json.dumps(variants_json, ensure_ascii=False) if variants_json is not None else None
        cursor.execute("""
            UPDATE products
            SET title = COALESCE(NULLIF(?, ''), title),
                variant_name = CASE WHEN ? != '' THEN ? ELSE variant_name END,
                current_price = ?,
                lowest_price = ?,
                status = ?,
                last_checked = ?,
                variants_json = COALESCE(?, variants_json)
            WHERE id = ?
        """, (title, variant_name, variant_name, current_price, lowest_price, status, now_str, v_json_str, product_id))
        conn.commit()
        conn.close()

def update_product_variants_json(product_id: int, variants_json: List[Dict]):
    """Cập nhật trạng thái thủ công của danh sách phân loại (ví dụ: đánh dấu hết hàng)."""
    import json
    if is_using_supabase():
        try:
            _supabase_client.table("products").update({"variants_json": variants_json}).eq("id", product_id).execute()
        except Exception as e:
            print(f"[DB WARN] Không thể lưu variants_json lên Supabase: {e}")
    else:
        conn = _get_sqlite_conn()
        cursor = conn.cursor()
        v_json_str = json.dumps(variants_json, ensure_ascii=False)
        cursor.execute("UPDATE products SET variants_json = ? WHERE id = ?", (v_json_str, product_id))
        conn.commit()
        conn.close()

def update_target_price(product_id: int, target_price: float, discount_amount: float = 0.0, discount_percent: float = 0.0):
    if is_using_supabase():
        _supabase_client.table("products").update({
            "target_price": target_price,
            "discount_amount": discount_amount,
            "discount_percent": discount_percent
        }).eq("id", product_id).execute()
    else:
        conn = _get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET target_price = ?, discount_amount = ?, discount_percent = ? WHERE id = ?", (target_price, discount_amount, discount_percent, product_id))
        conn.commit()
        conn.close()

def delete_product(product_id: int):
    if is_using_supabase():
        _supabase_client.table("products").delete().eq("id", product_id).execute()
    else:
        conn = _get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()

def delete_invalid_products() -> int:
    """Xóa tất cả các sản phẩm có trạng thái lỗi link hoặc lỗi cào giá."""
    if is_using_supabase():
        # Lấy danh sách sản phẩm lỗi
        res = _supabase_client.table("products").select("id").ilike("status", "%Lỗi%").execute()
        ids = [item["id"] for item in (res.data or [])]
        if ids:
            _supabase_client.table("products").delete().in_("id", ids).execute()
        return len(ids)
    else:
        conn = _get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE status LIKE '%Lỗi%'")
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted_count
