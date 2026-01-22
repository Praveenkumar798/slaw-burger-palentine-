import sqlite3

conn = sqlite3.connect('data/inventory.db')
cursor = conn.cursor()

# Check inventory levels
print("=== SAMPLE INVENTORY LEVELS ===")
cursor.execute('SELECT name, current_stock, unit FROM ingredients ORDER BY name LIMIT 15')
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]} {row[2]}")

print("\n=== RECENT ORDER DEDUCTIONS ===")
cursor.execute('''
    SELECT od.timestamp, i.name, od.quantity_deducted, i.unit
    FROM order_deductions od
    JOIN ingredients i ON od.ingredient_id = i.id
    ORDER BY od.timestamp DESC
    LIMIT 10
''')
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]} - Deducted {row[2]} {row[3]}")

print("\n=== ORDERS SUMMARY ===")
cursor.execute('SELECT COUNT(*) FROM orders')
print(f"Total orders stored: {cursor.fetchone()[0]}")

cursor.execute('SELECT COUNT(*) FROM order_deductions')
print(f"Total ingredient deductions: {cursor.fetchone()[0]}")

cursor.execute('SELECT COUNT(*) FROM recipe_components')
print(f"Total recipe components configured: {cursor.fetchone()[0]}")

# Check if any ingredients have negative stock
print("\n=== INGREDIENTS WITH NEGATIVE STOCK ===")
cursor.execute('SELECT name, current_stock, unit FROM ingredients WHERE current_stock < 0')
negative = cursor.fetchall()
if negative:
    for row in negative:
        print(f"  {row[0]}: {row[1]} {row[2]}")
else:
    print("  None (all stock levels are positive)")

conn.close()
