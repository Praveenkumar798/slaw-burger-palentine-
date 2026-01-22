import sqlite3
import os
from datetime import datetime
from src.database import get_connection

class InventoryManager:
    def __init__(self):
        # We now use the database connection instead of these file paths for core data
        # but keep them for backward compatibility or reference if needed
        self.LOG_FILE = os.path.join('logs', 'inventory_log.txt')

    def log(self, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        entry = f"[{timestamp}] {message}"
        print(entry)
        if not os.path.exists('logs'):
            os.makedirs('logs')
        with open(self.LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(entry + "\n")

    def get_all_stock(self):
        """Return list of all ingredients"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM ingredients ORDER BY name ASC')
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts with consistent key naming
        ingredients = []
        for row in rows:
            ing = dict(row)
            # Ensure numeric fields are floats
            for field in ['current_stock', 'threshold', 'cost_per_unit']:
                try:
                    ing[field] = float(ing[field]) if ing[field] is not None and ing[field] != '' else 0.0
                except (ValueError, TypeError):
                    ing[field] = 0.0
            
            # Ensure both 'quantity' and 'current_stock' are available for compatibility
            ing['quantity'] = ing['current_stock']
            ingredients.append(ing)
        return ingredients

    def get_ingredient(self, ingredient_id):
        """Get single ingredient by ID"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM ingredients WHERE id = ?', (ingredient_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            ing = dict(row)
            # Ensure numeric fields are floats
            for field in ['current_stock', 'threshold', 'cost_per_unit']:
                try:
                    ing[field] = float(ing[field]) if ing[field] is not None and ing[field] != '' else 0.0
                except (ValueError, TypeError):
                    ing[field] = 0.0
            ing['quantity'] = ing['current_stock']
            return ing
        return None

    def update_stock(self, ingredient_id, new_quantity):
        """Update stock for a specific ingredient"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE ingredients SET current_stock = ? WHERE id = ?', (float(new_quantity), ingredient_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
        
    def add_ingredient(self, name, category, unit, cost_per_unit=0.0, threshold=5.0):
        """Add a new ingredient"""
        # Generate a slug-like ID if not provided, or just use name
        ing_id = name.lower().replace(" ", "_")
        
        # Check if ID already exists, if so append a number
        conn = get_connection()
        cursor = conn.cursor()
        
        temp_id = ing_id
        counter = 1
        while True:
            cursor.execute('SELECT id FROM ingredients WHERE id = ?', (temp_id,))
            if not cursor.fetchone():
                ing_id = temp_id
                break
            temp_id = f"{ing_id}_{counter}"
            counter += 1
            
        cursor.execute('''
        INSERT INTO ingredients (id, name, category, unit, cost_per_unit, current_stock, threshold)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (ing_id, name, category, unit, float(cost_per_unit), 0.0, float(threshold)))
        
        conn.commit()
        
        # Fetch the created item
        cursor.execute('SELECT * FROM ingredients WHERE id = ?', (ing_id,))
        new_item = dict(cursor.fetchone())
        new_item['quantity'] = new_item['current_stock']
        
        conn.close()
        return new_item

    def update_ingredient_details(self, ingredient_id, updates):
        """Update ingredient details"""
        if not updates:
            return False
            
        allowed_fields = ['name', 'category', 'unit', 'threshold', 'cost_per_unit', 'current_stock']
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if key in allowed_fields:
                # Cast numeric fields to float if they are strings or empty
                if key in ['threshold', 'cost_per_unit', 'current_stock']:
                    try:
                        value = float(value) if value != '' and value is not None else 0.0
                    except (ValueError, TypeError):
                        value = 0.0
                set_clauses.append(f"{key} = ?")
                values.append(value)
        
        if not set_clauses:
            return False
            
        values.append(ingredient_id)
        query = f"UPDATE ingredients SET {', '.join(set_clauses)} WHERE id = ?"
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, values)
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_all_recipes(self):
        """Get all recipes mapped by menu GUID"""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get all menu items that have recipe components
        cursor.execute('''
            SELECT DISTINCT menu_item_guid 
            FROM recipe_components
        ''')
        menu_guids = [row['menu_item_guid'] for row in cursor.fetchall()]
        
        all_recipes = {}
        for guid in menu_guids:
            cursor.execute('''
                SELECT ingredient_id, quantity 
                FROM recipe_components 
                WHERE menu_item_guid = ?
            ''', (guid,))
            components = [dict(row) for row in cursor.fetchall()]
            all_recipes[guid] = components
            
        conn.close()
        return all_recipes

    def update_recipe(self, menu_item_guid, ingredients_list):
        """
        ingredients_list: [{"ingredient_id": "...", "quantity": 1.5}, ...]
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Delete existing components
            cursor.execute('DELETE FROM recipe_components WHERE menu_item_guid = ?', (menu_item_guid,))
            
            # Insert new components
            for item in ingredients_list:
                cursor.execute('''
                    INSERT INTO recipe_components (menu_item_guid, ingredient_id, quantity)
                    VALUES (?, ?, ?)
                ''', (menu_item_guid, item['ingredient_id'], item['quantity']))
            
            conn.commit()
            return True
        except Exception as e:
            self.log(f"Error updating recipe: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_recipe(self, menu_item_guid):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM recipe_components WHERE menu_item_guid = ?', (menu_item_guid,))
            success = cursor.rowcount > 0
            conn.commit()
            return success
        except Exception as e:
            self.log(f"Error deleting recipe: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def update_cost(self, ingredient_id, new_cost):
        return self.update_ingredient_details(ingredient_id, {'cost_per_unit': new_cost})

    def delete_ingredient(self, ingredient_id):
        """Delete an ingredient and its recipe mappings"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Remove from recipe components first to maintain integrity
            cursor.execute('DELETE FROM recipe_components WHERE ingredient_id = ?', (ingredient_id,))
            # Remove from ingredients
            cursor.execute('DELETE FROM ingredients WHERE id = ?', (ingredient_id,))
            success = cursor.rowcount > 0
            conn.commit()
            return success
        except Exception as e:
            self.log(f"Error deleting ingredient {ingredient_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
