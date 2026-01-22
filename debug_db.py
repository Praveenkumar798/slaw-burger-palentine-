import sqlite3
import os

DB_PATH = os.path.join('data', 'inventory.db')

def check_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("--- Ingredients (Top 10) ---")
    cursor.execute("SELECT * FROM ingredients LIMIT 10")
    for row in cursor.fetchall():
        print(dict(row))
        
    print("\n--- Recent Goods Inward (Top 5) ---")
    cursor.execute("SELECT * FROM goods_inward ORDER BY timestamp DESC LIMIT 5")
    for row in cursor.fetchall():
        print(dict(row))
        
    conn.close()

if __name__ == "__main__":
    check_db()
