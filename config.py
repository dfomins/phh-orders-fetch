from dotenv import load_dotenv
import os

load_dotenv()

URL_BASE = 'https://pmpapi.pigugroup.eu/v4/'
PMP_USERNAME = os.getenv('PMP_USERNAME')
PMP_PASS = os.getenv('PMP_PASS')
SELLER_ID = os.getenv('SELLER_ID')

BATCH_SIZE = 1000
MAX_THREADS = 8

MONGO_CONNECTION_URI = os.getenv('DB_CONNECTION_URI')
MONGO_DB_NAME = os.getenv('DB_NAME')