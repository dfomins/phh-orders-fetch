import os
import threading
from dotenv import load_dotenv
import requests
import keyring
from export import export_orders_to_xlsx
from mongo import export_to_mongo

# ENVIRONMENT VARIABLES
load_dotenv()
PMP_USER = os.getenv('PMP_USERNAME')
PMP_PASS = os.getenv('PMP_PASS')
SELLER_ID = os.getenv('SELLER_ID')

# API CONFIGURATION
URL_BASE = 'https://pmpapi.pigugroup.eu/'
VERSION = 'v4'
LIMIT = 100

def get_token():
  token = keyring.get_password('pmp_api', PMP_USER)
  if token:
    return token
  else:
    return refresh_token()
      
def refresh_token():
  keyring.delete_password('pmp_api', PMP_USER)
  auth_url = URL_BASE + f'{VERSION}/login'
    
  headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
  
  payload = {
    'username': PMP_USER,
    'password': PMP_PASS
  }
  
  response = requests.post(auth_url, json=payload, headers=headers)
  
  if response.status_code == 200:
    token = response.json().get('token')
    if token:
      keyring.set_password('pmp_api', PMP_USER, token)
      print("Token stored securely in keyring.")
      return token
    else:
      print("Login successful, but 'token' key was missing from JSON.")
  else:
    print(f"Failed to get token: {response.status_code}")
    print(response.text)
  
def get_orders(token, created_at_from=None, created_at_to=None, type=None, order_status=None):
  url = URL_BASE + f'{VERSION}/sellers/{SELLER_ID}/orders'
  headers = {'Authorization': f'Pigu-mp {token}'}
  
  current_offset = 0
  
  params = {'limit': LIMIT, 'offset': current_offset}
  if created_at_from: params['created_at_from'] = created_at_from
  if created_at_to: params['created_at_to'] = created_at_to
  if type: params['type'] = type
  if order_status: params['order_status'] = order_status
  
  print(f"From: {created_at_from}, To: {created_at_to}, Status: {order_status}, Type: {type}")
  
  all_orders = []
  
  while True:
    response = requests.get(url, headers=headers, params=params)
    print(f"Fetching orders from: {response.url}")
    
    token_lock = threading.Lock()
    
    if response.status_code == 401:
      print("Unauthorized. Attempting to refresh token.")

      with token_lock:
        token = refresh_token()
        headers['Authorization'] = f'Pigu-mp {token}'
      
      continue
    
    if response.status_code != 200:
      print(f"Error {response.status_code}: {response.text}")
      break
    
    data = response.json()
    orders = data.get('orders', [])
    if not orders:
      print("No more orders found.")
      break
    
    all_orders.extend(orders)
    print(f"Fetched {len(orders)} orders. Total: {len(all_orders)}")
    
    current_offset += LIMIT
    params['offset'] = current_offset
  
  return all_orders

def structure_orders(response_orders):
  if not response_orders:
    print("No orders found for the specified date range, type and status.")
    return []
  else:
    orders = []
    for response_order in response_orders:
      order_id = response_order.get('external_id', 'N/A')
      status = response_order.get('order_status', 'N/A')
      type = response_order.get('seller_delivery_type', 'N/A')
      created_at = response_order.get('created_at', 'N/A')
      total_price = response_order.get('total_price', 'N/A')
      
      response_products = response_order.get('products', [])
      products = []
      for response_product in response_products:
        # product_id = response_product.get('product_id', 'N/A')
        modification = response_product.get('modification', None)
        if modification:
          mod_id = modification.get('external_id', 'N/A')
          product_ean = str(modification.get('ean', 'N/A'))
                  
        # 1. Initialize everything as 'N/A'
        price = 'N/A'
        price_without_vat = 'N/A'
        vat = 'N/A'
        amount = 'N/A'

        # 2. Get raw data
        price_raw = response_product.get('price', 'N/A')
        price_without_vat_raw = response_product.get('price_without_vat', 'N/A')
        amount_raw = response_product.get('amount', 'N/A')

        # 3. Convert Price if it exists
        if price_raw != 'N/A' and price_raw is not None:
            price = round(float(price_raw), 2)

        # 4. Convert Price Without VAT if it exists
        if price_without_vat_raw != 'N/A' and price_without_vat_raw is not None:
            price_without_vat = round(float(price_without_vat_raw), 2)

        # 5. Calculate VAT only if both are now numbers (floats)
        if isinstance(price, float) and isinstance(price_without_vat, float):
            vat = round(price - price_without_vat, 2)
            
        if amount_raw != 'N/A' and amount_raw is not None:
          amount = int(amount_raw)
        
        products.append({
          'modification_id': mod_id,
          'ean': product_ean,
          'price': price,
          'price_without_vat': price_without_vat,
          'vat': vat,
          'amount': amount
        })
      
      orders.append({
        'order_id': order_id,
        'order_status': status,
        'type': type,
        'created_at': created_at,
        'total_price': total_price,
        'products': products
      })
    return orders

data_lock = threading.Lock()
unique_rows = {}

def thread_worker(token, status, collection_name):
  response_orders = get_orders(token,
                               created_at_from=start_str,
                                created_at_to=end_str,
                               order_status=status)
  structured_batch = structure_orders(response_orders)
  
  with data_lock:
    for order in structured_batch:
      for product in order['products']:
        composite_key = f"{order['order_id']}_{product['ean']}"
        if composite_key not in unique_rows:
          unique_rows[composite_key] = {
            **order,
            'products': [product] 
          }
          
  export_to_mongo(collection_name, structured_batch)
  print(f"THREAD COMPLETED: {status} ({len(structured_batch)} orders found)")

if __name__ == "__main__":
  token = get_token()
  
  statuses = ['completed', 'shipping', 'confirmed']
  
  all_orders = []
  threads = []
  
  print("STARTING THREADS")
  for status in statuses:
    t = threading.Thread(target=thread_worker, args=(token, status, 'all'))
    t.daemon = True
    threads.append(t)
    t.start()
    print(f"STARTED ALL THREAD FOR STATUS: {status}")
    
  for t in threads:
    t.join()
    
  print(f"ALL THREADS FINISHED. TOTAL UNIQUE ROWS: {len(unique_rows)}")
      
  final_list = list(unique_rows.values())
  export_orders_to_xlsx(final_list, 'all_orders')