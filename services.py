from datetime import datetime
from modules.database import connect

RANKS={"Urgent":1,"High":2,"Normal":3}

def generate_product_code(category):
    prefix={"Milkshake":"MIL","Milktea":"MT","Float":"FLT","Snack":"SNK"}.get(category,"OTH")
    with connect() as c:
        n=c.execute("SELECT COUNT(*) FROM products WHERE code LIKE ?",(prefix+"-%",)).fetchone()[0]+1
    return f"{prefix}-{n:03d}"

def save_product(code,name,category,price,stock,low_stock):
    code=code or generate_product_code(category)
    with connect() as c:
        c.execute("""INSERT INTO products(code,name,category,price,stock,low_stock)
        VALUES(?,?,?,?,?,?) ON CONFLICT(code) DO UPDATE SET name=excluded.name,
        category=excluded.category,price=excluded.price,stock=excluded.stock,low_stock=excluded.low_stock""",
        (code,name,category,price,stock,low_stock))
def delete_product(code):
    with connect() as c: c.execute("DELETE FROM products WHERE code=?",(code,))
def adjust_stock(code,delta):
    with connect() as c:
        row=c.execute("SELECT stock FROM products WHERE code=?",(code,)).fetchone()
        if not row: raise ValueError("Product not found.")
        if row[0]+delta<0: raise ValueError("Stock cannot become negative.")
        c.execute("UPDATE products SET stock=stock+? WHERE code=?",(delta,code))
def add_inventory_item(name,unit,quantity,reorder):
    with connect() as c:
        n=c.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]+1
        c.execute("INSERT INTO inventory(code,name,unit,quantity,reorder_level) VALUES(?,?,?,?,?)",
                  (f"RAW-{n:03d}",name,unit,quantity,reorder))
def restock_inventory(code,quantity):
    with connect() as c:
        c.execute("UPDATE inventory SET quantity=quantity+? WHERE code=?",(quantity,code))
        c.execute("INSERT INTO inventory_movements(inventory_code,movement,quantity) VALUES(?,?,?)",
                  (code,"RESTOCK",quantity))
def delete_inventory_item(code):
    with connect() as c: c.execute("DELETE FROM inventory WHERE code=?",(code,))
def create_order(items,total,priority):
    with connect() as c:
        # Validate all menu stock before changing any stock.
        for item in items:
            row=c.execute("SELECT stock FROM products WHERE id=?",(item["product_id"],)).fetchone()
            if not row or row[0] < item["quantity"]:
                raise ValueError(f"Insufficient stock for {item['name']}. Refresh the product list.")
        cur=c.execute("INSERT INTO orders(total,priority,priority_rank) VALUES(?,?,?)",
                      (total,priority,RANKS[priority]))
        oid=cur.lastrowid
        for item in items:
            c.execute("INSERT INTO order_items(order_id,product_id,product_name,price,quantity,subtotal) VALUES(?,?,?,?,?,?)",
                      (oid,item["product_id"],item["name"],item["price"],item["quantity"],item["subtotal"]))
            c.execute("UPDATE products SET stock=stock-? WHERE id=?",(item["quantity"],item["product_id"]))
        return oid
def update_order_status(order_id,status):
    with connect() as c: c.execute("UPDATE orders SET status=? WHERE id=?",(status,order_id))
