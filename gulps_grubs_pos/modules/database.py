import os
import sqlite3
from pathlib import Path

# Streamlit Cloud can set GULPS_GRUBS_DB_PATH to a mounted persistent
# location. Otherwise, keep the database in the project's data/ directory.
PROJECT_DIR = Path(__file__).resolve().parent.parent
DB = Path(os.environ.get("GULPS_GRUBS_DB_PATH", PROJECT_DIR / "data" / "gulps_grubs.db"))


def connect():
    # SQLite creates the database file, but it cannot create missing folders.
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB), timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c
def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT UNIQUE NOT NULL,
          name TEXT NOT NULL,category TEXT NOT NULL,size TEXT NOT NULL,price REAL NOT NULL,stock INTEGER NOT NULL DEFAULT 0,
          low_stock INTEGER NOT NULL DEFAULT 5,availability TEXT NOT NULL DEFAULT 'Available');
        CREATE TABLE IF NOT EXISTS inventory(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT UNIQUE NOT NULL,
          name TEXT NOT NULL,kind TEXT NOT NULL,unit TEXT NOT NULL,quantity REAL NOT NULL DEFAULT 0,reorder_level REAL NOT NULL DEFAULT 5);
        CREATE TABLE IF NOT EXISTS inventory_movements(id INTEGER PRIMARY KEY AUTOINCREMENT,inventory_code TEXT,movement TEXT,
          quantity REAL,notes TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS product_supplies(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          product_id INTEGER NOT NULL,
          inventory_id INTEGER NOT NULL,
          quantity_per_product REAL NOT NULL DEFAULT 1,
          deduction_mode TEXT NOT NULL DEFAULT 'Automatic',
          UNIQUE(product_id, inventory_id),
          FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
          FOREIGN KEY(inventory_id) REFERENCES inventory(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,total REAL NOT NULL,priority TEXT NOT NULL,
          priority_rank INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'Pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER NOT NULL,
          product_id INTEGER,product_name TEXT NOT NULL,price REAL NOT NULL,quantity INTEGER NOT NULL,subtotal REAL NOT NULL,
          FOREIGN KEY(order_id) REFERENCES orders(id));
        """)
        movement_columns = [r[1] for r in c.execute("PRAGMA table_info(inventory_movements)")]
        if "notes" not in movement_columns:
            c.execute("ALTER TABLE inventory_movements ADD COLUMN notes TEXT")
        if c.execute("SELECT COUNT(*) FROM products").fetchone()[0]==0:
            c.executemany("INSERT INTO products(code,name,category,size,price,stock,low_stock) VALUES(?,?,?,?,?,?,?)",[
            ("MIL-001","Chocolate Kisses","Milkshake","12 oz",35,25,5),("MIL-002","Cookies n Cream","Milkshake","16 oz",45,25,5),
            ("MT-001","Wintermelon","Milktea","12 oz",39,30,5),("MT-002","Okinawa","Milktea","16 oz",49,30,5)])
        if c.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]==0:
            c.executemany("INSERT INTO inventory(code,name,kind,unit,quantity,reorder_level) VALUES(?,?,?,?,?,?)",[
            ("PKG-001","12 oz cups","Packaging","pcs",100,20),("PKG-002","16 oz cups","Packaging","pcs",100,20),
            ("PKG-003","Straws","Packaging","pcs",200,30),("RAW-001","Milk","Ingredient","liters",10,3),
            ("RAW-002","Sugar","Ingredient","kg",8,2),("RAW-003","Pearls / Sago","Ingredient","kg",4,1)])
        # One-time default assignments for existing menu items: size-matched cup + straw.
        for product in c.execute("SELECT id,size FROM products").fetchall():
            cup_name = f"{product['size']} cups"
            cup = c.execute("SELECT id FROM inventory WHERE kind='Packaging' AND lower(name)=lower(?)", (cup_name,)).fetchone()
            straw = c.execute("SELECT id FROM inventory WHERE kind='Packaging' AND lower(name)='straws'").fetchone()
            if cup:
                c.execute("INSERT OR IGNORE INTO product_supplies(product_id,inventory_id,quantity_per_product,deduction_mode) VALUES(?,?,1,'Automatic')", (product['id'],cup['id']))
            if straw:
                c.execute("INSERT OR IGNORE INTO product_supplies(product_id,inventory_id,quantity_per_product,deduction_mode) VALUES(?,?,1,'Automatic')", (product['id'],straw['id']))
def fetch(sql,args=()):
    with connect() as c:return [dict(r) for r in c.execute(sql,args).fetchall()]
def get_products():return fetch("SELECT * FROM products ORDER BY name,size")
def get_inventory():return fetch("SELECT * FROM inventory ORDER BY kind,name")
def get_orders(statuses=None):
    if statuses:
        marks=",".join("?" for _ in statuses); return fetch(f"SELECT * FROM orders WHERE status IN ({marks}) ORDER BY created_at",statuses)
    return fetch("SELECT * FROM orders ORDER BY id DESC")
def get_sales_summary():return fetch("SELECT COALESCE(SUM(total),0) sales,COUNT(*) transactions FROM orders WHERE status='Completed'")[0]
def get_low_stock():return fetch("SELECT * FROM products WHERE stock<=low_stock ORDER BY stock")


def get_product_supplies(product_id):
    return fetch("""SELECT ps.*, i.code, i.name, i.unit, i.quantity, i.kind
                  FROM product_supplies ps JOIN inventory i ON i.id=ps.inventory_id
                  WHERE ps.product_id=? ORDER BY i.name""", (product_id,))

def get_all_product_supplies():
    return fetch("""SELECT ps.*, p.name AS product_name, p.size, i.name AS supply_name, i.unit
                  FROM product_supplies ps JOIN products p ON p.id=ps.product_id
                  JOIN inventory i ON i.id=ps.inventory_id ORDER BY p.name, i.name""")

def get_inventory_movements(limit=100):
    return fetch("""SELECT m.*, i.name AS supply_name, i.unit FROM inventory_movements m
                  LEFT JOIN inventory i ON i.code=m.inventory_code ORDER BY m.id DESC LIMIT ?""", (limit,))
