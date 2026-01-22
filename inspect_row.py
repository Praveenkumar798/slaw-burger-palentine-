import sqlite3
import os

DB_PATH = os.path.join('data', 'inventory.db')

def inspect():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, cost_per_unit FROM ingredients WHERE name = 'Beef Patty'")
    row = cursor.fetchone()
    if row:
        print(f"ID: {row[0]}, Name: {row[1]}, Cost: {repr(row[2])}, Type: {type(row[2])}")
    conn.close()

if __name__ == "__main__":
    inspect()
