import os
from dotenv import load_dotenv
from datetime import datetime
from pymongo.server_api import ServerApi
from pymongo import MongoClient, errors
import time

# ENVIRONMENT VARIABLES
load_dotenv()
DB_CONNECTION_URI = os.getenv('DB_CONNECTION_URI')

DB_NAME = "orders-invoices"

def connect_to_mongo():
  while True:
    try:
      client = MongoClient(DB_CONNECTION_URI, server_api=ServerApi('1'), serverSelectionTimeoutMS=10000)
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
    
def export_to_mongo(collection_name, orders):
  client = connect_to_mongo()
  db = client[DB_NAME]

  if collection_name not in db.list_collection_names():
    print(f"Collection '{collection_name}' does not exist. Creating it now...")
    db.create_collection(collection_name)
    db[collection_name].create_index([("order_id", 1)], unique=True)
  else:
    print(f"Collection '{collection_name}' already exists.")
    
  collection = db[collection_name]

  for order in orders:
    order_id = order.get("order_id")

    collection.update_one(
      {"order_id": order_id},
      {"$set": order},
      upsert=True
    )

  print(f"Uploaded orders to mongo")
  client.close()