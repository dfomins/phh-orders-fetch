def structure_orders(response_orders) -> list[dict]:
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
      mod_id = 'N/A'
      product_ean = 'N/A'
      
      modification = response_product.get('modification')
      if modification:
        mod_id = modification.get('external_id', 'N/A')
        product_ean = str(modification.get('ean', 'N/A'))
                
      price = 'N/A'
      price_without_vat = 'N/A'
      vat = 'N/A'
      amount = 'N/A'

      price_raw = response_product.get('price', 'N/A')
      price_without_vat_raw = response_product.get('price_without_vat', 'N/A')
      amount_raw = response_product.get('amount', 'N/A')

      if price_raw != 'N/A' and price_raw is not None:
        price = round(float(price_raw), 2)

      if price_without_vat_raw != 'N/A' and price_without_vat_raw is not None:
        price_without_vat = round(float(price_without_vat_raw), 2)

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