import streamlit as st
from modules.database import init_db, get_products, get_inventory, get_orders, get_sales_summary, get_low_stock
from modules.dsa import AVLTree, LinkedListCart, MinHeap
from modules.services import create_order, update_order_status, save_product, delete_product, adjust_stock, add_inventory_item, restock_inventory, delete_inventory_item

st.set_page_config(page_title="Gulps & Grubs POS", page_icon="🥤", layout="wide")
init_db()

st.markdown("""
<style>
.stApp {background:#f6f7fb;}
[data-testid="stHeader"] {background:rgba(255,255,255,0);}
.block-container {padding-top:1.5rem; max-width:1400px;}
.hero {background:linear-gradient(120deg,#182b24,#315b48);padding:24px 28px;border-radius:18px;color:white;margin-bottom:18px;}
.hero h1 {margin:0;color:white;font-size:2rem;}
.hero p {margin:6px 0 0;color:#e4eee7;}
div[data-testid="stMetric"] {background:white;padding:14px;border:1px solid #e8eaf0;border-radius:14px;}
.stButton>button {border-radius:10px;font-weight:600;}
</style>
<div class="hero"><h1>🥤 Gulps & Grubs POS</h1><p>Point of Sale • Order Priority • Product & Inventory Control</p></div>
""", unsafe_allow_html=True)

mode = st.radio("Select mode", ["Cashier", "Admin", "Inventory Manager"], horizontal=True)
products = get_products()
tree = AVLTree()
for p in products:
    tree.insert(p["name"].lower(), p)

def show_product_table(rows):
    if rows:
        st.dataframe([{ "Code": p["code"], "Product": p["name"], "Category": p["category"],
                        "Price (₱)": p["price"], "Menu Stock": p["stock"], "Status": p["status"] } for p in rows],
                     use_container_width=True, hide_index=True)
    else:
        st.info("No products found.")

if mode == "Cashier":
    st.subheader("Cashier Mode")
    left, right = st.columns([1.3, 1])
    if "cart" not in st.session_state:
        st.session_state.cart = LinkedListCart()
    cart = st.session_state.cart
    with left:
        st.markdown("#### Find products")
        query = st.text_input("Search by product name", key="cash_search")
        matches = tree.search_prefix(query.lower()) if query.strip() else products
        show_product_table(matches)
        if matches:
            names = [p["name"] for p in matches]
            selected = st.selectbox("Choose product", names)
            product = next(p for p in matches if p["name"] == selected)
            qty = st.number_input("Quantity", min_value=1, max_value=max(1, int(product["stock"])), value=1, step=1)
            if st.button("Add to cart", type="primary"):
                if product["stock"] < qty:
                    st.error("Not enough menu stock.")
                else:
                    cart.add(product["id"], product["name"], product["price"], int(qty))
                    st.success(f"Added {qty} × {product['name']}")
    with right:
        st.markdown("#### Current cart")
        items = cart.to_list()
        if items:
            for item in items:
                c1, c2 = st.columns([3,1])
                c1.write(f"**{item['name']}** × {item['quantity']} — ₱{item['subtotal']:.2f}")
                if c2.button("Remove", key=f"rm_{item['product_id']}"):
                    cart.remove(item["product_id"]); st.rerun()
            st.markdown(f"### Total: ₱{cart.total():.2f}")
            priority = st.selectbox("Order priority", ["Normal", "High", "Urgent"])
            if st.button("Send order to queue", type="primary", use_container_width=True):
                try:
                    order_id = create_order(items, cart.total(), priority)
                    cart.clear()
                    st.success(f"Order #{order_id} sent to the priority queue.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
            if st.button("Clear cart"):
                cart.clear(); st.rerun()
        else:
            st.caption("Your cart is empty.")
    st.divider()
    st.markdown("#### Live order queue")
    pending = get_orders(["Pending", "Preparing"])
    heap = MinHeap()
    for order in pending:
        heap.push(order["priority_rank"], order["created_at"], order)
    queue = []
    while len(heap):
        queue.append(heap.pop()[2])
    if queue:
        st.dataframe([{"Order": f"#{o['id']}", "Priority": o["priority"], "Total": f"₱{o['total']:.2f}",
                       "Status": o["status"], "Placed": o["created_at"]} for o in queue],
                     use_container_width=True, hide_index=True)
    else:
        st.info("No pending orders.")

elif mode == "Admin":
    st.subheader("Admin Mode")
    summary = get_sales_summary()
    a,b,c = st.columns(3)
    a.metric("Total sales", f"₱{summary['sales']:.2f}")
    b.metric("Transactions", summary["transactions"])
    c.metric("Products", len(products))
    tab1, tab2, tab3 = st.tabs(["Products", "Sales & Reports", "Order Queue"])
    with tab1:
        st.markdown("#### Add / edit product")
        with st.form("product_form"):
            code = st.text_input("Product code (leave blank to auto-generate)")
            name = st.text_input("Product name")
            category = st.selectbox("Category", ["Milkshake", "Milktea", "Float", "Snack", "Other"])
            price = st.number_input("Selling price (₱)", min_value=0.0, value=50.0, step=1.0)
            stock = st.number_input("Menu stock", min_value=0, value=20, step=1)
            low = st.number_input("Low-stock threshold", min_value=0, value=5, step=1)
            submitted = st.form_submit_button("Save product")
            if submitted:
                if not name.strip() or price <= 0:
                    st.error("Enter a product name and a price greater than zero.")
                else:
                    try:
                        save_product(code.strip() or None, name.strip(), category, price, int(stock), int(low))
                        st.success("Product saved.")
                        st.rerun()
                    except Exception as e: st.error(str(e))
        st.markdown("#### Search / delete products")
        q = st.text_input("Search products", key="admin_search").lower()
        show_product_table([p for p in products if q in p["name"].lower() or q in p["code"].lower()])
        if products:
            target = st.selectbox("Select product to delete", [f"{p['code']} — {p['name']}" for p in products])
            if st.button("Delete selected product"):
                delete_product(target.split(" — ")[0]); st.success("Product deleted."); st.rerun()
        st.caption("To edit, save the same existing product code again with its updated details.")
    with tab2:
        st.markdown("#### Stock alerts")
        low_rows = get_low_stock()
        if low_rows:
            st.warning("Products at or below their low-stock threshold.")
            show_product_table(low_rows)
        else: st.success("No low-stock products.")
        st.markdown("#### Recent sales")
        orders = get_orders(["Completed"])
        if orders:
            st.dataframe([{"Order": o["id"], "Total": f"₱{o['total']:.2f}", "Date": o["created_at"]} for o in orders],
                         use_container_width=True, hide_index=True)
        else: st.info("No completed sales yet. Mark queued orders completed to include them in sales.")
    with tab3:
        orders = get_orders(["Pending", "Preparing"])
        if orders:
            for o in sorted(orders, key=lambda x: (x["priority_rank"], x["created_at"])):
                col1,col2,col3 = st.columns([3,1,1])
                col1.write(f"**Order #{o['id']}** · {o['priority']} · ₱{o['total']:.2f} · {o['status']}")
                if col2.button("Preparing", key=f"prep{o['id']}"): update_order_status(o["id"], "Preparing"); st.rerun()
                if col3.button("Complete", key=f"done{o['id']}"): update_order_status(o["id"], "Completed"); st.rerun()
        else: st.info("Queue is empty.")

else:
    st.subheader("Inventory Manager Mode")
    inv = get_inventory()
    tab1, tab2, tab3 = st.tabs(["Supply inventory", "Restock", "Menu product stock"])
    with tab1:
        st.markdown("#### Raw materials & supplies")
        if inv:
            st.dataframe([{"Code":x["code"],"Supply":x["name"],"Unit":x["unit"],"On hand":x["quantity"],
                           "Reorder level":x["reorder_level"],"Status":"LOW" if x["quantity"] <= x["reorder_level"] else "OK"} for x in inv],
                         use_container_width=True, hide_index=True)
        else: st.info("No raw-material supplies have been added.")
        with st.form("add_supply"):
            st.markdown("#### Add supply")
            nm = st.text_input("Supply name")
            unit = st.text_input("Unit (e.g. pcs, kg, pack, bottle)", value="pcs")
            amount = st.number_input("Opening quantity", min_value=0.0, value=0.0)
            reorder = st.number_input("Reorder level", min_value=0.0, value=5.0)
            if st.form_submit_button("Add supply"):
                if nm.strip(): add_inventory_item(nm.strip(), unit.strip(), amount, reorder); st.success("Supply added."); st.rerun()
                else: st.error("Supply name is required.")
        if inv:
            chosen = st.selectbox("Select supply to remove", [f"{x['code']} — {x['name']}" for x in inv])
            if st.button("Delete supply"): delete_inventory_item(chosen.split(" — ")[0]); st.rerun()
    with tab2:
        if inv:
            chosen = st.selectbox("Supply to restock", [f"{x['code']} — {x['name']}" for x in inv], key="restock_select")
            amount = st.number_input("Restock quantity", min_value=0.01, value=1.0, step=1.0)
            if st.button("Record restock", type="primary"):
                restock_inventory(chosen.split(" — ")[0], amount); st.success("Restock recorded."); st.rerun()
        st.caption("Every restock is recorded in the inventory movement history.")
    with tab3:
        st.markdown("#### Menu products")
        show_product_table(products)
        if products:
            chosen = st.selectbox("Menu item", [f"{p['code']} — {p['name']}" for p in products])
            delta = st.number_input("Stock adjustment (+ to add, - to deduct)", value=0, step=1)
            if st.button("Update menu stock"):
                adjust_stock(chosen.split(" — ")[0], int(delta)); st.success("Menu stock updated."); st.rerun()
        st.caption("This tab tracks finished menu-item stock. Raw ingredients are tracked separately above.")
