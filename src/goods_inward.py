"""
Goods Inward (Receipt of Goods) System
Use this when you receive shipments to add stock to inventory
"""

import os
import sqlite3
from datetime import datetime
from src.database import get_connection
from src.inventory_manager import InventoryManager
from src.logger import Logger

class GoodsInwardManager:
    def __init__(self):
        self.inventory = InventoryManager()
        self.logger = Logger()
    
    def load_delivery_history(self):
        """Load past receipt records"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM goods_inward ORDER BY timestamp DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return {"deliveries": [dict(row) for row in rows]}
    
    def receive_delivery(self, ingredient_id, quantity, supplier="", invoice_number="", notes="", unit_cost=None):
        """Receive a delivery and update database"""
        ingredient = self.inventory.get_ingredient(ingredient_id)
        
        if not ingredient:
            self.logger.error(f"Ingredient '{ingredient_id}' not found!")
            return False
        
        # Get current stock
        old_stock = ingredient['current_stock']
        new_stock = old_stock + float(quantity)
        
        # Effective unit cost
        try:
            raw_cost = unit_cost if unit_cost is not None else ingredient.get('cost_per_unit', 0)
            final_unit_cost = float(raw_cost) if raw_cost and raw_cost != '' else 0.0
        except (ValueError, TypeError):
            final_unit_cost = 0.0
            
        total_cost = final_unit_cost * float(quantity)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Update ingredient stock and cost
            cursor.execute('''
                UPDATE ingredients 
                SET current_stock = ?, cost_per_unit = ? 
                WHERE id = ?
            ''', (float(new_stock), float(final_unit_cost), ingredient_id))
            
            # 2. Log receipt
            cursor.execute('''
                INSERT INTO goods_inward (
                    timestamp, ingredient_id, ingredient_name, quantity_received, unit, 
                    old_stock, new_stock, supplier, invoice_number, notes, received_by, 
                    unit_cost, total_cost
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                ingredient_id,
                ingredient['name'],
                float(quantity),
                ingredient['unit'],
                float(old_stock),
                float(new_stock),
                supplier,
                invoice_number,
                notes,
                "System",
                float(final_unit_cost),
                float(total_cost)
            ))
            
            conn.commit()
            
            self.logger.info(f"[DELIVERY] RECEIVED: {quantity} {ingredient['unit']} of {ingredient['name']}")
            self.logger.info(f"   Stock: {old_stock} -> {new_stock} {ingredient['unit']}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error processing delivery: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def receive_multiple_items(self, items):
        """Receive multiple items in one transaction"""
        self.logger.section("RECEIVING GOODS INWARD - MULTIPLE ITEMS")
        success_count = 0
        
        for item in items:
            if self.receive_delivery(
                ingredient_id=item.get('ingredient_id'),
                quantity=item.get('quantity', 0),
                supplier=item.get('supplier', ''),
                invoice_number=item.get('invoice_number', ''),
                notes=item.get('notes', ''),
                unit_cost=item.get('unit_cost', None)
            ):
                success_count += 1
        
        self.logger.section(f"DELIVERY COMPLETE - {success_count}/{len(items)} items received")
        return success_count == len(items)

    def view_delivery_history(self, limit=10):
        """Print recent receipts to console"""
        history = self.load_delivery_history()
        deliveries = history['deliveries']
        
        print("\n" + "="*70)
        print(f"GOODS INWARD HISTORY (Last {limit} receipts)")
        print("="*70)
        
        recent = deliveries[:limit]
        for d in recent:
            print(f"\n[GOODS IN] {d['timestamp'][:19]}")
            print(f"   Item: {d['ingredient_name']}")
            print(f"   Quantity: {d['quantity_received']} {d['unit']}")
            print(f"   Stock: {d['old_stock']} -> {d['new_stock']}")
            if d['supplier']: print(f"   Supplier: {d['supplier']}")
            if d['unit_cost']: print(f"   Cost: ${d['unit_cost']:.2f}/{d['unit']} (Total: ${d['total_cost']:.2f})")