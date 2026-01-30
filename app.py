from flask import Flask, render_template, jsonify, request
from src.inventory_manager import InventoryManager
from src.goods_inward import GoodsInwardManager
from src.inventory_adjustment import AdjustmentManager
import collections
from datetime import datetime
from src import toast_api
from src.database import get_connection, init_db

app = Flask(__name__)

# Initialize database on startup
try:
    init_db()
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"⚠️  Database initialization warning: {e}")

inventory = InventoryManager()
delivery_manager = GoodsInwardManager()
adjustment_manager = AdjustmentManager()

@app.route('/api/sync/toast', methods=['POST'])
def sync_toast():
    """Initial check/preview for sync"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Received sync preview request")
    try:
        # We call run_sync with dry_run=True to get the preview
        try:
            success, result = toast_api.run_sync(dry_run=True)
        except Exception as sync_error:
            print(f"Sync exception: {sync_error}")
            import traceback
            traceback.print_exc()
            return jsonify({"status": "error", "message": f"Sync failed: {str(sync_error)}"}), 500
        
        if success:
            if isinstance(result, str): # "No new orders found"
                return jsonify({"status": "success", "message": result, "new_orders": 0})
            
            # result is a dict with orders and deductions
            if isinstance(result, dict) and 'orders' in result and 'deductions' in result:
                return jsonify({
                    "status": "success", 
                    "preview": True,
                    "orders": result.get('orders', []),
                    "deductions": result.get('deductions', []),
                    "new_orders": len(result.get('orders', []))
                })
            else:
                # Fallback if result format is unexpected
                return jsonify({"status": "success", "message": "Sync ready", "new_orders": 0})
        
        error_msg = str(result) if result else "Unknown error during sync"
        return jsonify({"status": "error", "message": error_msg}), 500
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Exception in sync_toast: {error_msg}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route('/api/sync/toast/confirm', methods=['POST'])
def confirm_sync():
    """Finalize the sync after user approval"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Received sync confirmation")
    try:
        try:
            success, message = toast_api.run_sync(dry_run=False)
        except Exception as sync_error:
            print(f"Sync exception: {sync_error}")
            import traceback
            traceback.print_exc()
            return jsonify({"status": "error", "message": f"Sync failed: {str(sync_error)}"}), 500
            
        if success:
            return jsonify({"status": "success", "message": message})
        error_msg = str(message) if message else "Sync failed"
        return jsonify({"status": "error", "message": error_msg}), 500
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Exception in confirm_sync: {error_msg}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route('/')
def dashboard():
    # Get raw stock data
    stock = inventory.get_all_stock()
    recipes = inventory.get_all_recipes()
    
    # Sort alphabetical for fields
    sorted_stock = sorted(stock, key=lambda x: x['name'])

    # Group by category for Dashboard View
    inventory_by_category = collections.defaultdict(list)
    category_order = ["Meat", "Bread", "Produce", "Dairy", "sides", "Sauce", "Drink", "Dessert"]
    
    for item in stock:
        cat = item.get('category', 'Other')
        qty = item.get('quantity', item.get('current_stock', 0))
        threshold = item.get('threshold', 0)
        
        normalized_item = {
            'id': item['id'],
            'name': item['name'],
            'current_stock': qty,
            'unit': item['unit'],
            'low_stock_threshold': threshold,
            'category': cat,
            'cost_per_unit': item.get('cost_per_unit', 0)
        }
        inventory_by_category[cat].append(normalized_item)

    # Sort categories
    sorted_inventory = {}
    for cat in category_order:
        if cat in inventory_by_category:
            sorted_inventory[cat] = inventory_by_category[cat]
    for cat in inventory_by_category:
        if cat not in sorted_inventory:
            sorted_inventory[cat] = inventory_by_category[cat]

    return render_template('index.html', 
                         inventory_by_category=sorted_inventory,
                         all_ingredients=sorted_stock,
                         recipes=recipes)


@app.route('/api/toast/menu')
def get_toast_menu():
    creds = toast_api.load_credentials()
    if not creds:
        return jsonify({"status": "error", "message": "Toast credentials not found"}), 400
    
    menu = toast_api.get_menu(creds['ACCESS_TOKEN'], creds['RESTAURANT_GUID'])
    if menu:
        return jsonify(menu)
    return jsonify({"status": "error", "message": "Failed to fetch menu from Toast"}), 500

@app.route('/api/menu/local')
def get_local_menu():
    """Load menu items from database"""
    try:
        # Load from menu_items in database
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT item_guid, item_name, menu, group_path 
            FROM menu_items 
            ORDER BY menu, item_name
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        menu_items = []
        for row in rows:
            menu_items.append({
                'guid': row['item_guid'],
                'name': row['item_name'],
                'menu': row['menu'],
                'group': row['group_path']
            })
        
        return jsonify({"status": "success", "menu_items": menu_items})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    return jsonify(inventory.get_all_recipes())


@app.route('/api/stock')
def api_stock():
    return jsonify(inventory.get_all_stock())

@app.route('/api/ingredients', methods=['POST'])
def add_ingredient():
    data = request.json
    try:
        if not data.get('name'):
            return jsonify({"status": "error", "message": "Name is required"}), 400
            
        new_item = inventory.add_ingredient(
            name=data['name'],
            category=data.get('category', 'Other'),
            unit=data.get('unit', 'unit'),
            cost_per_unit=data.get('cost_per_unit', 0),
            threshold=data.get('threshold', 5)
        )
        
        if new_item:
            return jsonify({"status": "success", "message": "Ingredient created", "item": new_item})
        return jsonify({"status": "error", "message": "Failed to create ingredient"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/ingredients/<id>', methods=['PUT', 'POST'])
def update_ingredient(id):
    data = request.json
    try:
        success = inventory.update_ingredient_details(id, data)
        if success:
            return jsonify({"status": "success", "message": "Ingredient updated"})
        return jsonify({"status": "error", "message": "Ingredient not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/ingredients/<id>', methods=['DELETE'])
def delete_ingredient(id):
    try:
        success = inventory.delete_ingredient(id)
        if success:
            return jsonify({"status": "success", "message": "Ingredient deleted"})
        return jsonify({"status": "error", "message": "Ingredient not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/receive', methods=['POST'])
def receive_delivery():
    data = request.json
    try:
        success = delivery_manager.receive_delivery(
            ingredient_id=data['ingredient_id'],
            quantity=float(data['quantity']),
            supplier=data.get('supplier'),
            invoice_number=data.get('invoice'),
            notes=data.get('notes'),
            unit_cost=float(data['cost']) if data.get('cost') else None
        )
        if success:
            return jsonify({"status": "success", "message": "Delivery received"})
        return jsonify({"status": "error", "message": "Failed to update inventory"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/receive/bulk', methods=['POST'])
def receive_bulk_delivery():
    data = request.json
    try:
        items = data.get('items', [])
        if not items:
            return jsonify({"status": "error", "message": "No items provided"}), 400
            
        success = delivery_manager.receive_multiple_items(items)
        
        if success:
            return jsonify({"status": "success", "message": f"Successfully received {len(items)} items"})
        return jsonify({"status": "warning", "message": "Completed with some potential warnings"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/adjust', methods=['POST'])
def log_adjustment():
    data = request.json
    try:
        success = adjustment_manager.log_adjustment(
            ingredient_id=data['ingredient_id'],
            quantity=float(data['quantity']),
            reason=data['reason'],
            adjustment_type=data.get('type', 'Deduction'),
            staff_member=data.get('staff'),
            notes=data.get('notes')
        )
        if success:
            return jsonify({"status": "success", "message": "Adjustment logged"})
        return jsonify({"status": "error", "message": "Failed to log adjustment"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/waste', methods=['POST'])
def log_waste_legacy():
    # Keep for compatibility with old UI calls
    return log_adjustment()

@app.route('/api/history')
def get_history():
    # Fetch recent deliveries and manual adjustments
    deliveries = delivery_manager.load_delivery_history().get('deliveries', [])[:10]
    adjustments = adjustment_manager.load_adjustment_history().get('adjustments', [])[:10]
    
    return jsonify({
        "deliveries": sorted(deliveries, key=lambda x: x['timestamp'], reverse=True),
        "waste": sorted(adjustments, key=lambda x: x['timestamp'], reverse=True)
    })

@app.route('/api/orders')
def get_orders():
    """Get recent orders with basic info"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, toast_guid, order_number, closed_date, total_amount, payment_status, source
            FROM orders
            ORDER BY closed_date DESC
            LIMIT 50
        ''')
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({"status": "success", "orders": orders})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/orders/<int:order_id>')
def get_order_details(order_id):
    """Get detailed order information with items and deductions"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get order
        cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        order = cursor.fetchone()
        if not order:
            conn.close()
            return jsonify({"status": "error", "message": "Order not found"}), 404
        
        order_data = dict(order)
        
        # Get order items
        cursor.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,))
        order_data['items'] = [dict(row) for row in cursor.fetchall()]
        
        # Get deductions for this order
        cursor.execute('''
            SELECT od.*, i.name as ingredient_name, i.unit
            FROM order_deductions od
            JOIN ingredients i ON od.ingredient_id = i.id
            WHERE od.order_id = ?
        ''', (order_id,))
        order_data['deductions'] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return jsonify({"status": "success", "order": order_data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/orders/stats')
def get_order_stats():
    """Get order statistics"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Total orders
        cursor.execute('SELECT COUNT(*) as count, SUM(total_amount) as revenue FROM orders WHERE deleted = 0')
        stats = dict(cursor.fetchone())
        
        # Orders today
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT COUNT(*) as count FROM orders WHERE DATE(closed_date) = ? AND deleted = 0', (today,))
        stats['today_count'] = cursor.fetchone()['count']
        
        conn.close()
        return jsonify({"status": "success", "stats": stats})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/recipes', methods=['POST'])
def save_recipe():
    data = request.json
    try:
        menu_guid = data.get('menu_guid')
        components = data.get('components', [])
        
        if not menu_guid:
            return jsonify({"status": "error", "message": "Menu GUID is required"}), 400
            
        success = inventory.update_recipe(menu_guid, components)
        
        if success:
            return jsonify({"status": "success", "message": "Recipe saved successfully"})
        return jsonify({"status": "error", "message": "Failed to save recipe"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/recipes/<guid>', methods=['DELETE'])
def delete_recipe(guid):
    try:
        success = inventory.delete_recipe(guid)
        if success:
            return jsonify({"status": "success", "message": "Recipe deleted"})
        return jsonify({"status": "error", "message": "Failed to delete recipe"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    print("Starting Slawburger Inventory UI...")
    app.run(host='0.0.0.0', port=5000, debug=True)
