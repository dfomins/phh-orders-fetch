import requests
import keyring
from keyring.errors import PasswordDeleteError
import logging
from logging_config import setup_logging
from config import SELLER_ID
from config import PMP_USERNAME
from config import PMP_PASS
from config import URL_BASE
from config import BATCH_SIZE

def get_token() -> str:
  if PMP_USERNAME is None:
    raise ValueError('Username is not present')
  
  token = keyring.get_password('pmp_api', PMP_USERNAME)
  if token:
    return token
  else:
    return refresh_token()


def refresh_token() -> str:
  setup_logging()
  
  # Try to delete existing token from keyring, but ignore if it doesn't exist
  try:
    if PMP_USERNAME is None:
      logging.exception('Username is not present')
      exit(1)

    keyring.delete_password('pmp_api', PMP_USERNAME)
  except PasswordDeleteError:
    logging.exception('Failed to delete existing token from keyring. Please check keyring configuration.')
  
  auth_url = URL_BASE + 'login'
    
  headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
  
  payload = {
    'username': PMP_USERNAME,
    'password': PMP_PASS
  }
  
  response = requests.post(auth_url, json=payload, headers=headers)
  
  response.raise_for_status()
  
  token = response.json().get('token')
  
  if not token:
    raise ValueError(
      "Login successful but token missing from response"
    )
    
  keyring.set_password('pmp_api', PMP_USERNAME, token)
  
  logging.info("Token stored securely in keyring")
  
  return token


def get_order_count_for_status(status: str) -> int:
  token = get_token()
  
  headers = {
    'Authorization': f'Pigu-mp {token}',
    'Accept': 'application/json'
  }
  
  url = URL_BASE + f'sellers/{SELLER_ID}/orders'
  
  while True:
    response = requests.get(url,
      headers=headers,
      timeout=30,
      params={'order_status': status, 'limit': 1}
    )
    
    if response.status_code == 200:
      break
    
    if response.status_code == 401:
      logging.info("Unauthorized. Attempting to refresh token.")
      token = refresh_token()
      continue
    
    if response.status_code != 200:
      logging.error("Error %s: %s", response.status_code, response.text)
      exit(1)
    
  data = response.json()
  total_orders = data.get('meta', {}).get('total_count', 0)
  return int(total_orders)


def fetch_orders_chunk(status: str, offset: int, token: str) -> list[dict]:
  logging.info("START chunk status=%s offset=%s", status, offset)
  
  url = URL_BASE + f'sellers/{SELLER_ID}/orders'
  headers = {'Authorization': f'Pigu-mp {token}'}
  
  current_offset = offset
  end_offset = offset + BATCH_SIZE
  limit = 100
  
  all_orders = []
  
  while current_offset < end_offset:
    params = {
      'order_status': status,
      'limit': limit,
      'offset': current_offset
    }
    
    response = requests.get(url,
      headers=headers,
      params=params,
      timeout=30
    )
    
    logging.debug("Fetching orders from: %s", response.url)
    
    response.raise_for_status()
        
    data = response.json()
    orders = data.get('orders', [])
    
    if not orders:
      logging.info(
        "No more orders found status=%s offset=%s",
        status,
        current_offset,
      )
      break
    
    all_orders.extend(orders)
    
    logging.info(
      "status=%s offset=%s fetched=%s chunk_total=%s",
      status,
      current_offset,
      len(orders),
      len(all_orders),
    )
    
    current_offset += limit

  logging.info(
    "END chunk status=%s offset=%s total_fetched=%s",
    status,
    offset,
    len(all_orders),
  )

  return all_orders