# Gulps & Grubs POS System

A Python + Streamlit point-of-sale and inventory-management MVP with three workspaces and three manually implemented data structures.

## Run locally

1. Install Python 3.10 or newer.
2. Extract this ZIP file.
3. Open a terminal in the `gulps_grubs_pos_mvp` folder.
4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Start the application:

   ```bash
   streamlit run app.py
   ```

The application creates the `data/` folder and SQLite database automatically on first launch. The starter database includes sample menu products and supplies. Replace these with your actual records in Admin and Inventory Manager.

## Three workspaces

### Cashier
- Search and select available menu products.
- Manage the shopping cart using the custom Linked List.
- Select Urgent, High, or Normal priority.
- Submit orders to the Min-Heap queue.
- View the pending/preparing order queue.

### Admin
- Add, edit (save using the existing product code), delete, and search menu products.
- Set category, size, price, opening stock, and low-stock threshold.
- Assign shared supplies to menu products.
- Choose whether each assignment is Automatic or Manual.
- View sales, completed orders, low-stock and high-stock menu reports, and the order queue.
- Update order status to Preparing or Complete.

### Inventory Manager
- Adjust finished menu-product stock.
- Add, search, restock, and delete shared supply records.
- Record manual consumption of ingredients and other manually tracked supplies.
- View inventory movement history and stock alerts.

## Partially automatic inventory (Option B)

Shared supplies are stored once in the `inventory` table. Many menu products can point to the same supply through `product_supplies`.

- **Automatic:** standardized packaging such as cups, straws, and lids. The assigned quantity is deducted when an order is submitted.
- **Manual:** milk, sugar, flavorings, pearls, and other ingredients. The Inventory Manager records consumption in the **Record manual usage** tab.

Admin assigns supply requirements in **Menu products & supply assignments**. For example, assign one 12 oz cup and one straw to each 12 oz drink. The same 12 oz cup record can be assigned to multiple drinks. Assign ingredient quantities as Manual if they should not be automatically deducted.

The starter records include automatic assignments for size-matched cups and straws. New products need their own supply assignments before those supplies will be deducted.

Order confirmation and automatic supply deductions run in one SQLite transaction. If stock validation fails, the order and deductions are rolled back. Automatic deductions are written to inventory movement history. Manual consumption and restocking are also logged.

## DSA implementation

- **Linked List:** Cashier cart insertion, removal, traversal, and total calculation.
- **AVL Tree:** Menu product-name index for prefix searching.
- **Min-Heap:** Priority queue; Urgent = 1, High = 2, Normal = 3. Order ID breaks same-timestamp ties.

SQLite is the persistent record store. The DSA structures are implemented in Python for the application's operations and academic demonstration.

## Database and hosting notes

The database is created at `data/gulps_grubs.db` by default. You can set the environment variable `GULPS_GRUBS_DB_PATH` to a writable persistent database path.

**Streamlit Community Cloud warning:** its local app filesystem is not guaranteed to persist across restarts or redeployments. Do not use this local SQLite file as the only copy of real sales or inventory data. For live business use, use a managed persistent database (for example PostgreSQL/Supabase) or a hosting environment with a persistent volume, and maintain backups.

## Important MVP limitation

The three workspace choices are not secure user authentication. Anyone who can access the app can switch workspaces. Add login and server-side role authorization before using this for a real business or exposing it publicly. This project is intended as an academic/demo MVP.
