import sqlite3
import os

DB_PATH = os.path.join('data', 'inventory.db')

def get_connection():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database schema."""
    if not os.path.exists('data'):
        os.makedirs('data')
        
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create Ingredients table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ingredients (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT,
        unit TEXT,
        current_stock REAL DEFAULT 0,
        threshold REAL DEFAULT 0,
        cost_per_unit REAL DEFAULT 0
    )
    ''')
    
    # Create Menu Items table (Complete menu catalog from Toast)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        menu TEXT,
        group_path TEXT,
        item_name TEXT NOT NULL,
        item_guid TEXT UNIQUE NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create indexes for menu_items
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_menu_items_guid 
    ON menu_items(item_guid)
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_menu_items_menu 
    ON menu_items(menu)
    ''')
    
    # Create Recipes table (Menu items with ingredient mappings) --- REMOVED: Redundant with menu_items
    
    # Create Recipe Components table (Links menu items to ingredients)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS recipe_components (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        menu_item_guid TEXT NOT NULL,
        ingredient_id TEXT,
        quantity REAL,
        unit TEXT,
        FOREIGN KEY (menu_item_guid) REFERENCES menu_items (item_guid),
        FOREIGN KEY (ingredient_id) REFERENCES ingredients (id)
    )
    ''')
    
    # Create Goods Inward table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS goods_inward (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        ingredient_id TEXT,
        ingredient_name TEXT,
        quantity_received REAL,
        unit TEXT,
        old_stock REAL,
        new_stock REAL,
        supplier TEXT,
        invoice_number TEXT,
        notes TEXT,
        received_by TEXT,
        unit_cost REAL,
        total_cost REAL,
        FOREIGN KEY (ingredient_id) REFERENCES ingredients (id)
    )
    ''')
    
    # Create Inventory Adjustments table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory_adjustments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        ingredient_id TEXT,
        ingredient_name TEXT,
        quantity REAL,
        type TEXT, -- 'Deduction' or 'Addition'
        unit TEXT,
        reason TEXT,
        staff_member TEXT,
        notes TEXT,
        old_stock REAL,
        new_stock REAL,
        cost_per_unit REAL,
        total_waste_cost REAL,
        FOREIGN KEY (ingredient_id) REFERENCES ingredients (id)
    )
    ''')
    
    # Create Orders table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        toast_guid TEXT UNIQUE NOT NULL,
        order_number TEXT,
        opened_date TEXT,
        closed_date TEXT,
        modified_date TEXT,
        deleted BOOLEAN DEFAULT 0,
        total_amount REAL,
        tax_amount REAL,
        tip_amount REAL,
        payment_status TEXT,
        source TEXT,
        raw_json TEXT,
        synced_at TEXT
    )
    ''')
    
    # Create Order Items table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        menu_item_guid TEXT,
        menu_item_name TEXT,
        quantity INTEGER,
        unit_price REAL,
        total_price REAL,
        modifiers TEXT,
        FOREIGN KEY (order_id) REFERENCES orders (id)
    )
    ''')
    
    # Create Order Deductions table (audit trail)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_deductions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        order_item_id INTEGER,
        ingredient_id TEXT,
        quantity_deducted REAL,
        timestamp TEXT,
        FOREIGN KEY (order_id) REFERENCES orders (id),
        FOREIGN KEY (order_item_id) REFERENCES order_items (id),
        FOREIGN KEY (ingredient_id) REFERENCES ingredients (id)
    )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
