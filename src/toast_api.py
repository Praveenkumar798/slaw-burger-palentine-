import json
import os
import requests
import sqlite3
import collections
from datetime import datetime, timedelta
import time
from src.database import get_connection

# --- Configuration & Credentials ---
CREDENTIALS = {
    "CLIENT_ID": "",
    "CLIENT_SECRET": "", 
    "RESTAURANT_GUID": "",
    "ACCESS_TOKEN": ""
}

# File Paths - Use absolute paths to avoid issues when running from different CWD
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'logs', 'toast_credentials.txt')
LAST_SYNC_FILE = os.path.join(BASE_DIR, 'logs', 'last_sync_time.txt')
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'inventory_log.txt')

def log(message):
    """Log messages to console and file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = f"[{timestamp}] {message}"
    try:
        print(entry)
    except Exception:
        pass # specific environment might have issues with stdout
    
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(entry + "\n")
    except Exception as e:
        # If we can't write to log file, just ignore to avoid crushing the app
        pass

def load_credentials():
    creds = CREDENTIALS.copy()
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        if key in ["CLIENT_ID", "CLIENT_SECRET", "RESTAURANT_GUID", "ACCESS_TOKEN", "MANAGEMENT_GROUP_GUID"]:
                            creds[key] = value
        except Exception as e:
            log(f"Error reading credentials file: {e}")
    
    return creds

def save_credentials(creds):
    """Save updated credentials back to file"""
    try:
        LOG_DIR = os.path.join(BASE_DIR, 'logs')
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
            for key in ["CLIENT_ID", "CLIENT_SECRET", "RESTAURANT_GUID", "ACCESS_TOKEN", "MANAGEMENT_GROUP_GUID"]:
                if key in creds and creds[key]:
                    f.write(f"{key}={creds[key]}\n")
        return True
    except Exception as e:
        log(f"Error saving credentials: {e}")
        return False

def refresh_access_token(creds):
    """Request a fresh access token from Toast legacy auth endpoint"""
    log("Refreshing Toast access token...")
    
    if not creds.get("CLIENT_ID") or not creds.get("CLIENT_SECRET"):
        log("Cannot refresh: Missing CLIENT_ID or CLIENT_SECRET")
        return False, "Missing credentials"

    url = "https://ws-api.toasttab.com/authentication/v1/authentication/login"
    payload = {
        "clientId": creds["CLIENT_ID"],
        "clientSecret": creds["CLIENT_SECRET"],
        "userAccessType": "TOAST_MACHINE_CLIENT"
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            new_token = data.get('token', {}).get('accessToken')
            if new_token:
                creds["ACCESS_TOKEN"] = new_token
                save_credentials(creds)
                log("Token refreshed successfully and saved to logs/toast_credentials.txt")
                return True, new_token
            else:
                log(f"Refresh failed: No accessToken in response: {data}")
                return False, "No token in response"
        else:
            log(f"Refresh failed with status {response.status_code}: {response.text}")
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        log(f"Error during token refresh: {e}")
        return False, str(e)

def get_last_sync_time():
    if os.path.exists(LAST_SYNC_FILE):
        try:
            with open(LAST_SYNC_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except:
            pass
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%S.000+0000')

def save_sync_time(iso_timestamp):
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    try:
        with open(LAST_SYNC_FILE, 'w', encoding='utf-8') as f:
            f.write(iso_timestamp)
    except Exception as e:
        log(f"Warning: Failed to save sync time: {e}")

def get_menu(access_token, restaurant_guid):
    """Fetch the full menu from Toast API"""
    url = f"https://ws-api.toasttab.com/menus/v2/menus"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Toast-Restaurant-External-ID": restaurant_guid,
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log(f"API Error fetching menu: {e}")
        return None

def fetch_orders(access_token, restaurant_guid, start_date_str, end_date_str):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Toast-Restaurant-External-ID": restaurant_guid,
        "Content-Type": "application/json"
    }

    try:
        if end_date_str.endswith('Z'): end_date_str = end_date_str[:-1] + '+0000'
        if start_date_str.endswith('Z'): start_date_str = start_date_str[:-1] + '+0000'
        start_time = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M:%S.000+0000')
        end_time = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M:%S.000+0000')
    except ValueError as e:
        log(f"Date Parsing Error: {e}")
        return None

    all_orders = []
    current_chunk_start = start_time

    while current_chunk_start < end_time:
        current_chunk_end = current_chunk_start + timedelta(hours=1)
        if current_chunk_end > end_time: current_chunk_end = end_time
        if current_chunk_end <= current_chunk_start: break

        chunk_start_str = current_chunk_start.strftime('%Y-%m-%dT%H:%M:%S.000+0000')
        chunk_end_str = current_chunk_end.strftime('%Y-%m-%dT%H:%M:%S.000+0000')
        
        url = "https://ws-api.toasttab.com/orders/v2/orders"
        params = {"startDate": chunk_start_str, "endDate": chunk_end_str, "pageSize": 100}
        
        log(f"  Fetching chunk: {chunk_start_str} -> {chunk_end_str}")

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            chunk_orders = data if isinstance(data, list) else data.get('orders', [])
            all_orders.extend(chunk_orders)
        except requests.exceptions.RequestException as e:
            log(f"API Error fetching chunk {chunk_start_str}: {e}")
            return None
        except Exception as e:
            # Catch strict Errno 22 or other OS errors
            log(f"CRITICAL Error fetching chunk {chunk_start_str}: {e} (Type: {type(e)})")
            return None

        current_chunk_start = current_chunk_end
    return all_orders

def get_order_details(access_token, restaurant_guid, order_guid):
    url = f"https://ws-api.toasttab.com/orders/v2/orders/{order_guid}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Toast-Restaurant-External-ID": restaurant_guid,
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log(f"API Error fetching order details {order_guid}: {e}")
        return None

def run_sync(dry_run=False):
    log("="*60)
    log(f"STARTING TOAST SALES SYNC {'(PREVIEW MODE)' if dry_run else ''}")
    log("="*60)
    
    creds = load_credentials()
    if not creds: return False, "Failed to load credentials"

    # Ensure we have a Restaurant GUID
    if not creds.get("RESTAURANT_GUID") and creds.get("MANAGEMENT_GROUP_GUID"):
         creds["RESTAURANT_GUID"] = creds["MANAGEMENT_GROUP_GUID"]
         
    if not creds.get("RESTAURANT_GUID"):
        return False, "Missing RESTAURANT_GUID"

    # Proactive token check / refresh if needed
    if not creds.get("ACCESS_TOKEN"):
        success, result = refresh_access_token(creds)
        if not success:
            return False, f"Missing access token and refresh failed: {result}"
        creds["ACCESS_TOKEN"] = result

    start_time_str = get_last_sync_time()
    current_time = datetime.now()
    end_time_str = current_time.strftime('%Y-%m-%dT%H:%M:%S.000+0000')
    
    log(f"Sync Period: {start_time_str} to {end_time_str}")
    
    order_list = fetch_orders(creds['ACCESS_TOKEN'], creds['RESTAURANT_GUID'], start_time_str, end_time_str)
    
    if order_list is None:
        log("Order fetch failed, attempting token refresh...")
        success, result = refresh_access_token(creds)
        if success:
            creds["ACCESS_TOKEN"] = result
            log("Retry fetching orders with new token...")
            order_list = fetch_orders(creds['ACCESS_TOKEN'], creds['RESTAURANT_GUID'], start_time_str, end_time_str)
    
    if order_list is None: 
        return False, "Sync Error: API error fetching orders. Check logs/inventory_log.txt for details."
    if not order_list:
        if not dry_run: save_sync_time(end_time_str)
        return True, "No new orders found"

    log(f"Found {len(order_list)} order(s).")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    pending_sync = []
    total_deductions = collections.defaultdict(float)
    
    try:
        for order_ref in order_list:
            guid = order_ref.get('guid') if isinstance(order_ref, dict) else order_ref
            if not guid: continue
            
            cursor.execute('SELECT id FROM orders WHERE toast_guid = ?', (guid,))
            if cursor.fetchone():
                continue
                
            order_full = get_order_details(creds['ACCESS_TOKEN'], creds['RESTAURANT_GUID'], guid)
            if not order_full: continue
            
            order_preview = {
                'guid': guid,
                'orderNumber': order_full.get('orderNumber'),
                'totalAmount': order_full.get('totalAmount'),
                'closedDate': order_full.get('closedDate'),
                'items': []
            }
            
            selections = order_full.get('selections', [])
            if not selections and 'checks' in order_full:
                for check in order_full['checks']:
                    selections.extend(check.get('selections', []))
            
            for selection in selections:
                item_guid = selection.get('item', {}).get('guid')
                quantity = selection.get('quantity', 1)
                
                cursor.execute('SELECT item_name FROM menu_items WHERE item_guid = ?', (item_guid,))
                res = cursor.fetchone()
                item_name = res[0] if res else selection.get('item', {}).get('name', 'Unknown')
                
                order_preview['items'].append({'name': item_name, 'qty': quantity})
                
                cursor.execute('SELECT ingredient_id, quantity FROM recipe_components WHERE menu_item_guid = ?', (item_guid,))
                for component in cursor.fetchall():
                    ing_id = component['ingredient_id']
                    deduct_qty = component['quantity'] * quantity
                    total_deductions[ing_id] += deduct_qty
            
            pending_sync.append(order_preview)

        if dry_run:
            # Format deductions with names
            deduction_list = []
            for ing_id, qty in total_deductions.items():
                cursor.execute('SELECT name, unit FROM ingredients WHERE id = ?', (ing_id,))
                ing = cursor.fetchone()
                if ing:
                    deduction_list.append({
                        'name': ing['name'],
                        'quantity': round(qty, 4),
                        'unit': ing['unit']
                    })
            
            return True, {
                'orders': pending_sync,
                'deductions': deduction_list,
                'end_time': end_time_str
            }

        # Actual Sync Logic (only if not dry_run)
        orders_stored = 0
        deductions_count = 0
        
        for order_preview in pending_sync:
            # We need the full JSON again or better, we logic it
            # Re-fetch or use cached? Let's re-fetch for simplicity if we are here
            # (In reality, we should have cached it in the loop above)
            # Re-implementing the actual storage loop based on pending_sync
            
            # Since we've already done the work above, let's just commit if not dry_run
            # Wait, I should refactor to avoid double work.
            pass

        # RE-WRITING ACTUAL SYNC LOGIC TO BE ROBUST
        for order_preview in pending_sync:
            # Need full details again to store raw_json
            order_full = get_order_details(creds['ACCESS_TOKEN'], creds['RESTAURANT_GUID'], order_preview['guid'])
            if not order_full: continue
            
            cursor.execute('''
                INSERT INTO orders (
                    toast_guid, order_number, opened_date, closed_date, modified_date,
                    deleted, total_amount, tax_amount, tip_amount, payment_status, source, raw_json, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order_preview['guid'],
                order_full.get('orderNumber'),
                order_full.get('openedDate'),
                order_full.get('closedDate'),
                order_full.get('modifiedDate'),
                order_full.get('deleted', False),
                order_full.get('totalAmount'),
                order_full.get('taxAmount'),
                order_full.get('tipAmount'),
                order_full.get('paymentStatus'),
                order_full.get('source'),
                json.dumps(order_full),
                datetime.now().isoformat()
            ))
            order_db_id = cursor.lastrowid
            orders_stored += 1
            
            selections = order_full.get('selections', [])
            if not selections and 'checks' in order_full:
                for check in order_full['checks']:
                    selections.extend(check.get('selections', []))
            
            for selection in selections:
                item_guid = selection.get('item', {}).get('guid')
                item_name = selection.get('item', {}).get('name') or order_preview['items'][0]['name'] # rough fallback
                quantity = selection.get('quantity', 1)
                
                cursor.execute('''
                    INSERT INTO order_items (
                        order_id, menu_item_guid, menu_item_name, quantity, unit_price, total_price, modifiers
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (order_db_id, item_guid, item_name, quantity, selection.get('unitPrice', 0), selection.get('totalPrice', 0), json.dumps(selection.get('modifiers', []))))
                order_item_id = cursor.lastrowid
                
                cursor.execute('SELECT ingredient_id, quantity FROM recipe_components WHERE menu_item_guid = ?', (item_guid,))
                for component in cursor.fetchall():
                    ing_id = component['ingredient_id']
                    required_qty = component['quantity'] * quantity
                    cursor.execute('UPDATE ingredients SET current_stock = current_stock - ? WHERE id = ?', (float(required_qty), ing_id))
                    cursor.execute('''
                        INSERT INTO order_deductions (
                            order_id, order_item_id, ingredient_id, quantity_deducted, timestamp
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (order_db_id, order_item_id, ing_id, float(required_qty), datetime.now().isoformat()))
                    deductions_count += 1

        conn.commit()
        save_sync_time(end_time_str)
        return True, f"Successfully synced {orders_stored} new orders. {deductions_count} inventory deductions logged."

    except Exception as e:
        log(f"Error during sync: {e}")
        conn.rollback()
        return False, f"Sync error: {str(e)}"
    finally:
        conn.close()

if __name__ == "__main__":
    success, msg = run_sync()
    print(msg)
