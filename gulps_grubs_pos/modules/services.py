from modules.database import connect
RANK={"Urgent":1,"High":2,"Normal":3}
def gen_code(category):
    prefix={"Milkshake":"MIL","Milktea":"MT","Float":"FLT","Snack":"SNK"}.get(category,"OTH")
    with connect() as c:n=c.execute("SELECT COUNT(*) FROM products WHERE code LIKE ?",(prefix+"-%",)).fetchone()[0]+1
    return f"{prefix}-{n:03d}"
def save_product(code,name,category,size,price,stock,low):
    code=code or gen_code(category)
    with connect() as c:c.execute("""INSERT INTO products(code,name,category,size,price,stock,low_stock)
    VALUES(?,?,?,?,?,?,?) ON CONFLICT(code) DO UPDATE SET name=excluded.name,category=excluded.category,
    size=excluded.size,price=excluded.price,low_stock=excluded.low_stock""",
    (code,name,category,size,price,stock,low))
def delete_product(code):
    with connect() as c:c.execute("DELETE FROM products WHERE code=?",(code,))
def adjust_stock(code,delta):
    with connect() as c:
        r=c.execute("SELECT stock FROM products WHERE code=?",(code,)).fetchone()
        if not r or r[0]+delta<0:raise ValueError("Product not found or stock cannot become negative.")
        c.execute("UPDATE products SET stock=stock+? WHERE code=?",(delta,code))
def add_inventory_item(name,kind,unit,qty,reorder):
    prefix="PKG" if kind=="Packaging" else "RAW"
    with connect() as c:
        n=c.execute("SELECT COUNT(*) FROM inventory WHERE code LIKE ?",(prefix+"-%",)).fetchone()[0]+1
        c.execute("INSERT INTO inventory(code,name,kind,unit,quantity,reorder_level) VALUES(?,?,?,?,?,?)",
                  (f"{prefix}-{n:03d}",name,kind,unit,qty,reorder))
def restock_inventory(code,qty):
    with connect() as c:
        c.execute("UPDATE inventory SET quantity=quantity+? WHERE code=?",(qty,code))
        c.execute("INSERT INTO inventory_movements(inventory_code,movement,quantity,notes) VALUES(?,?,?,?)",(code,"RESTOCK",qty,"Supply restocked"))
def delete_inventory_item(code):
    with connect() as c:c.execute("DELETE FROM inventory WHERE code=?",(code,))
def save_product_supply(product_id, inventory_id, quantity_per_product, deduction_mode):
    if quantity_per_product <= 0:
        raise ValueError("Supply quantity must be greater than zero.")
    if deduction_mode not in ("Automatic", "Manual"):
        raise ValueError("Invalid deduction mode.")
    with connect() as c:
        c.execute("""INSERT INTO product_supplies(product_id,inventory_id,quantity_per_product,deduction_mode)
                     VALUES(?,?,?,?) ON CONFLICT(product_id,inventory_id) DO UPDATE SET
                     quantity_per_product=excluded.quantity_per_product,deduction_mode=excluded.deduction_mode""",
                  (product_id, inventory_id, quantity_per_product, deduction_mode))

def remove_product_supply(product_id, inventory_id):
    with connect() as c:
        c.execute("DELETE FROM product_supplies WHERE product_id=? AND inventory_id=?", (product_id, inventory_id))

def create_order(items,total,priority):
    with connect() as c:
        required = {}
        for item in items:
            p=c.execute("SELECT stock FROM products WHERE id=?",(item["product_id"],)).fetchone()
            if not p or p["stock"]<item["quantity"]:
                raise ValueError(f'Insufficient menu stock for {item["name"]}.')
            assignments = c.execute("""SELECT ps.inventory_id, ps.quantity_per_product, i.name, i.quantity
                FROM product_supplies ps JOIN inventory i ON i.id=ps.inventory_id
                WHERE ps.product_id=? AND ps.deduction_mode='Automatic'""", (item["product_id"],)).fetchall()
            for a in assignments:
                required[a["inventory_id"]] = required.get(a["inventory_id"], 0) + a["quantity_per_product"] * item["quantity"]
        for inventory_id, needed in required.items():
            row=c.execute("SELECT name,quantity FROM inventory WHERE id=?",(inventory_id,)).fetchone()
            if not row or row["quantity"] < needed:
                name = row["name"] if row else "Assigned supply"
                raise ValueError(f"Not enough {name}. Required: {needed:g}.")
        cur=c.execute("INSERT INTO orders(total,priority,priority_rank) VALUES(?,?,?)",(total,priority,RANK[priority]))
        oid=cur.lastrowid
        for item in items:
            c.execute("INSERT INTO order_items(order_id,product_id,product_name,price,quantity,subtotal) VALUES(?,?,?,?,?,?)",
                      (oid,item["product_id"],item["name"],item["price"],item["quantity"],item["subtotal"]))
            c.execute("UPDATE products SET stock=stock-? WHERE id=?",(item["quantity"],item["product_id"]))
        for inventory_id, needed in required.items():
            c.execute("UPDATE inventory SET quantity=quantity-? WHERE id=?",(needed,inventory_id))
            code=c.execute("SELECT code FROM inventory WHERE id=?",(inventory_id,)).fetchone()["code"]
            c.execute("INSERT INTO inventory_movements(inventory_code,movement,quantity,notes) VALUES(?,?,?,?)",
                      (code,"AUTO_DEDUCTION",-needed,f"Order #{oid}"))
        return oid

def update_order_status(oid,status):
    with connect() as c:c.execute("UPDATE orders SET status=? WHERE id=?",(status,oid))


def consume_inventory(code, qty, notes="Manual consumption"):
    if qty <= 0:
        raise ValueError("Quantity must be greater than zero.")
    with connect() as c:
        row=c.execute("SELECT quantity FROM inventory WHERE code=?",(code,)).fetchone()
        if not row or row["quantity"] < qty:
            raise ValueError("Supply not found or insufficient quantity.")
        c.execute("UPDATE inventory SET quantity=quantity-? WHERE code=?",(qty,code))
        c.execute("INSERT INTO inventory_movements(inventory_code,movement,quantity,notes) VALUES(?,?,?,?)",
                  (code,"MANUAL_DEDUCTION",-qty,notes))
