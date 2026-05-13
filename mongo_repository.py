import os
from dotenv import load_dotenv
from datetime import datetime
from pymongo.server_api import ServerApi
from pymongo import MongoClient, errors
import logging
import time

from config import MONGO_CONNECTION_URI
from config import MONGO_DB_NAME

# ENVIRONMENT VARIABLES
load_dotenv()

def connect_to_mongo():
  while True:
    try:
      client = MongoClient(MONGO_CONNECTION_URI, server_api=ServerApi('1'), serverSelectionTimeoutMS=10000)
      client.admin.command('ping')
      return client
    except errors.ServerSelectionTimeoutError as e:
      print("Connection failed (server selection timeout):", e)
    except errors.ConnectionFailure as e:
      print("Connection failed:", e)
    except Exception as e:
      print("Unexpected error:", e)

    print("Retrying in 5 seconds...\n")
    time.sleep(5)
    
def export_to_mongo(orders):
  client = connect_to_mongo()
  if MONGO_DB_NAME is None:
    raise ValueError('Database name is not present')
  
  db = client[MONGO_DB_NAME]

  if 'orders' not in db.list_collection_names():
    print(f"Collection 'orders' does not exist. Creating it now...")
    db.create_collection('orders')
    db['orders'].create_index([("order_id", 1)], unique=True)
    
  collection = db['orders']

  for order in orders:
    order_id = order.get("order_id")

    collection.update_one(
      {"order_id": order_id},
      {"$set": order},
      upsert=True
    )

  logging.info("Uploaded %s orders to MongoDB", len(orders))
  client.close()