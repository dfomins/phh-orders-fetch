import pandas as pd
import xlsxwriter
from datetime import datetime

def export_orders_to_xlsx(orders, filename):
  flattened_data = []

  for order in orders:
    for product in order.get('products', []):
      # Get amount and price, ensure they are numbers
      amount = pd.to_numeric(product.get('amount'), errors='coerce') or 0
      unit_price = pd.to_numeric(product.get('price'), errors='coerce') or 0
          
      # Calculate total for this specific line item
      line_total = round(amount * unit_price, 2)

      row = {
        'Order ID': order.get('external_id'),
        'Status': order.get('order_status'),
        'Type': order.get('type'),
        'Created At': order.get('created_at'),
        'Order Total Price': order.get('total_price'), # Total for the whole order
        'Modification ID': product.get('modification_id'),
        'EAN': product.get('ean'),
        'Unit Price': unit_price,
        'Amount': amount,
        'Line Total': line_total, # New: Amount * Unit Price
        'Price (no VAT)': product.get('price_without_vat'),
        'VAT': product.get('vat')
      }
      flattened_data.append(row)

  df_orders = pd.DataFrame(flattened_data)
  df_counts = pd.DataFrame()

  if not df_orders.empty:
    # Date Handling
    df_orders['Created At'] = pd.to_datetime(df_orders['Created At'], errors='coerce', utc=True)
    if pd.api.types.is_datetime64_any_dtype(df_orders['Created At']):
      df_orders['Created At'] = df_orders['Created At'].dt.tz_localize(None)
      df_orders = df_orders.sort_values(by='Created At', ascending=True)
        
    # Numeric ID handling
    df_orders['Order ID'] = pd.to_numeric(df_orders['Order ID'], errors='coerce').astype('Int64')
    df_orders['Modification ID'] = pd.to_numeric(df_orders['Modification ID'], errors='coerce').astype('Int64')
    df_orders['EAN'] = df_orders['EAN'].astype(str)

    # Price column cleaning
    float_cols = ['Order Total Price', 'Unit Price', 'Line Total', 'Price (no VAT)', 'VAT']
    for col in float_cols:
      df_orders[col] = pd.to_numeric(df_orders[col], errors='coerce')

    # SUMMARY SHEET: Summing Amount and the calculated Line Total
    df_counts = df_orders.groupby(['EAN']).agg({
      'Modification ID': 'first',
      'Amount': 'sum',
      'Line Total': 'sum'
    }).rename(columns={
      'Amount': 'Total Units Sold', 
      'Line Total': 'Total Revenue'
    }).reset_index()
    
    df_counts = df_counts.sort_values(by='Total Units Sold', ascending=False)

  timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
  output_file = f"{filename}_{timestamp}.xlsx"

  with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    df_orders.to_excel(writer, sheet_name='All Orders', index=False)
    df_counts.to_excel(writer, sheet_name='Product Summary', index=False)

    workbook = writer.book
    num_fmt = workbook.add_format({'num_format': '0'})
    price_fmt = workbook.add_format({'num_format': '#,##0.00'})
    date_fmt = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm'})

    # Sheet 1 Formatting (Letters adjusted for new columns)
    ws1 = writer.sheets['All Orders']
    ws1.set_column('A:A', 15, num_fmt)    # Order ID (A)
    ws1.set_column('C:C', 10)             # Type (C)
    ws1.set_column('D:D', 18, date_fmt)   # Created At (D)
    ws1.set_column('E:E', 12, price_fmt)  # Order Total (E)
    ws1.set_column('F:G', 20, num_fmt)    # Mod ID & EAN (F, G)
    ws1.set_column('H:H', 12, price_fmt)  # Unit Price (H)
    ws1.set_column('I:I', 10, num_fmt)    # Amount (I)
    ws1.set_column('J:L', 12, price_fmt)  # Line Total, No VAT, VAT (J, K, L)

    # Sheet 2 Formatting
    ws2 = writer.sheets['Product Summary']
    ws2.set_column('A:A', 20, num_fmt)    # EAN
    ws2.set_column('B:B', 15, num_fmt)    # Quantity Sold
    ws2.set_column('C:C', 15, price_fmt)  # Total Revenue
  
  print(f"Export done! Created {output_file}")