import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "gulps_grubs.db"

def connect():
    con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS products(
          id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
          name TEXT NOT NULL, category TEXT NOT NULL, price REAL NOT NULL CHECK(price>=0),
          stock INTEGER NOT NULL DEFAULT 0 CHECK(stock>=0), low_stock INTEGER NOT NULL DEFAULT 5,
          status TEXT NOT NULL DEFAULT 'Active');
        CREATE TABLE IF NOT EXISTS inventory(
          id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
          name TEXT NOT NULL, unit TEXT NOT NULL, quantity REAL NOT NULL DEFAULT 0,
          reorder_level REAL NOT NULL DEFAULT 5);
        CREATE TABLE IF NOT EXISTS inventory_movements(
          id INTEGER PRIMARY KEY AUTOINCREMENT, inventory_code TEXT, movement TEXT,
          quantity REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS orders(
          id INTEGER PRIMARY KEY AUTOINCREMENT, total REAL NOT NULL,
          priority TEXT NOT NULL, priority_rank INTEGER NOT NULL,
          status TEXT NOT NULL DEFAULT 'Pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS order_items(
          id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL,
          product_id INTEGER, product_name TEXT NOT NULL, price REAL NOT NULL,
          quantity INTEGER NOT NULL, subtotal REAL NOT NULL,
          FOREIGN KEY(order_id) REFERENCES orders(id));
        """)
        if c.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            c.executemany("INSERT INTO products(code,name,category,price,stock,low_stock) VALUES(?,?,?,?,?,?)",[
             ("MIL-001","Chocolate Kisses Milkshake","Milkshake",45,25,5),
             ("MIL-002","Cookies n Cream Milkshake","Milkshake",45,25,5),
             ("MT-001","Wintermelon Milktea","Milktea",49,30,5),
             ("FLT-001","Classic Float","Float",55,20,5)])
        if c.execute("SELECT COUNT(*) FROM inventory").fetchone()[0] == 0:
            c.executemany("INSERT INTO inventory(code,name,unit,quantity,reorder_level) VALUES(?,?,?,?,?)",[
             ("RAW-001","Milk","liters",10,3),("RAW-002","Pearls / Sago","kg",4,1),
             ("RAW-003","Cups","pcs",100,20),("RAW-004","Sugar","kg",8,2)])
def rows(sql,args=()):
    with connect() as c: return [dict(x) for x in c.execute(sql,args).fetchall()]
def get_products(): return rows("SELECT * FROM products ORDER BY name")
def get_inventory(): return rows("SELECT * FROM inventory ORDER BY name")
def get_orders(statuses=None):
    if statuses:
        marks=",".join("?" for _ in statuses)
        return rows(f"SELECT * FROM orders WHERE status IN ({marks}) ORDER BY created_at",statuses)
    return rows("SELECT * FROM orders ORDER BY id DESC")
def get_sales_summary():
    r=rows("SELECT COALESCE(SUM(total),0) sales, COUNT(*) transactions FROM orders WHERE status='Completed'")[0]
    return r
def get_low_stock(): return rows("SELECT * FROM products WHERE stock<=low_stock ORDER BY stock")
