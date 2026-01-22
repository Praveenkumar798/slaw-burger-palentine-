import sqlite3
import os

DB_PATH = os.path.join('data', 'inventory.db')

def cleanup():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Update strings or NULLs to 0.0 in numeric columns
    cursor.execute("UPDATE ingredients SET cost_per_unit = 0.0 WHERE cost_per_unit = '' OR cost_per_unit IS NULL")
    cursor.execute("UPDATE ingredients SET current_stock = 0.0 WHERE current_stock = '' OR current_stock IS NULL")
    cursor.execute("UPDATE ingredients SET threshold = 0.0 WHERE threshold = '' OR threshold IS NULL")
    
    print(f"Cleanup complete. Rows updated: {cursor.rowcount}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    cleanup()
