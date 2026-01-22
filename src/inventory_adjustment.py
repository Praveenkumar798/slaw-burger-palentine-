"""
Inventory Adjustment Management
Handles Waste, Consumption, Corrections, and other manual stock changes
"""

import os
from datetime import datetime
from src.database import get_connection
from src.inventory_manager import InventoryManager
from src.logger import Logger

class AdjustmentManager:
    def __init__(self):
        self.inventory = InventoryManager()
        self.logger = Logger()
    
    def load_adjustment_history(self):
        """Load adjustment history from database"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM inventory_adjustments ORDER BY timestamp DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return {"adjustments": [dict(row) for row in rows]}
    
    def log_adjustment(self, ingredient_id, quantity, reason, adjustment_type="Deduction", staff_member="", notes=""):
        """Log an inventory adjustment to SQLite"""
        ingredient = self.inventory.get_ingredient(ingredient_id)
        
        if not ingredient:
            self.logger.error(f"Ingredient '{ingredient_id}' not found!")
            return False
        
        try:
            quantity = float(quantity)
        except ValueError:
            return False

        # Get current stock
        old_stock = float(ingredient['current_stock'])
        
        # Calculate new stock
        if adjustment_type == "Addition":
            new_stock = old_stock + quantity
        else:
            new_stock = old_stock - quantity
            
        cost_per_unit = float(ingredient.get('cost_per_unit', 0))
        total_cost = cost_per_unit * quantity
        
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Update ingredient stock
            cursor.execute('UPDATE ingredients SET current_stock = ? WHERE id = ?', (float(new_stock), ingredient_id))
            
            # 2. Log event
            cursor.execute('''
                INSERT INTO inventory_adjustments (
                    timestamp, ingredient_id, ingredient_name, quantity, type, unit,
                    reason, staff_member, notes, old_stock, new_stock, cost_per_unit, total_waste_cost
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                ingredient_id,
                ingredient['name'],
                float(quantity),
                adjustment_type,
                ingredient['unit'],
                reason,
                staff_member,
                notes,
                float(old_stock),
                float(new_stock),
                float(cost_per_unit),
                float(total_cost if adjustment_type == "Deduction" else -total_cost)
            ))
            
            conn.commit()
            
            action = adjustment_type.upper()
            self.logger.info(f"[{action}] LOGGED: {quantity} {ingredient['unit']} of {ingredient['name']} - {reason}")
            self.logger.info(f"   Stock: {old_stock} -> {new_stock} {ingredient['unit']}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error logging adjustment: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_adjustment_summary(self, days=30):
        """Generate adjustment summary (primarily for waste/consumption)"""
        from datetime import timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM inventory_adjustments 
            WHERE timestamp >= ? AND type = 'Deduction'
        ''', (cutoff_date,))
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        summary_by_ingredient = {}
        summary_by_reason = {}
        total_cost = 0
        
        for event in events:
            ing_name = event['ingredient_name']
            if ing_name not in summary_by_ingredient:
                summary_by_ingredient[ing_name] = {'quantity': 0, 'unit': event['unit'], 'cost': 0, 'count': 0}
            
            summary_by_ingredient[ing_name]['quantity'] += event['quantity']
            summary_by_ingredient[ing_name]['cost'] += event['total_waste_cost']
            summary_by_ingredient[ing_name]['count'] += 1
            
            reason = event['reason']
            if reason not in summary_by_reason:
                summary_by_reason[reason] = {'count': 0, 'cost': 0}
            summary_by_reason[reason]['count'] += 1
            summary_by_reason[reason]['cost'] += event['total_waste_cost']
            
            total_cost += event['total_waste_cost']
        
        return {
            'by_ingredient': summary_by_ingredient,
            'by_reason': summary_by_reason,
            'total_cost': total_cost,
            'period_days': days
        }
