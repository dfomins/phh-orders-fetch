from filelock import FileLock, Timeout

import threading
import queue

import math

import logging
from logging_config import setup_logging

from config import BATCH_SIZE
from config import MAX_THREADS

from order_fetch_worker import order_fetch_worker

from api_client import get_token, get_order_count_for_status

def main() -> None:
  mutex = FileLock("orders_fetch.lock", timeout=0)
  
  try:
    with mutex:
      setup_logging()
      
      start_event = threading.Event()
      
      # Countdown event simulation
      countdown_event_sim = {"count": MAX_THREADS}
      countdown_lock = threading.Lock()
      countdown_done = threading.Event()
      
      # Get API token
      token = get_token()
      
      # Lock for synchronizing access to stats
      overall_stats_lock = threading.Lock()
      overall_stats = {
        "processed_chunks": 0,
        "processed_orders": 0,
        "failed_chunks": 0
      }
      
      order_status_lock = threading.Lock()
      order_statuses = {}
      
      jobs = queue.Queue()
      orders = []
      orders_lock = threading.Lock()
      threads = []
      
      for worker_id in range(MAX_THREADS):
        thread = threading.Thread(
          target=order_fetch_worker,
            args=(
              worker_id,
              jobs,
              token,
              overall_stats,
              overall_stats_lock,
              order_status_lock,
              orders,
              orders_lock,
              start_event,
              countdown_event_sim,
              countdown_lock,
              countdown_done
            ),
            name=f"Worker-{worker_id}",
        )
        
        threads.append(thread)
        thread.start()
      
      # Initializations
      for order_status in ['completed']:
        count = get_order_count_for_status(order_status)
        chunks = max(1, math.ceil(count / BATCH_SIZE))
        
        order_statuses[order_status] = {
          'count': count,
          'chunks': chunks,
          'processed_chunks': 0
        }
      
      for order_status, order_status_data in order_statuses.items():
        logging.info("Status=%s data=%s", order_status, order_status_data)
      
        for chunk_index in range(order_status_data['chunks']):
          # Calculate offset for this thread
          offset = chunk_index * BATCH_SIZE
          jobs.put((chunk_index, order_status, order_status_data, offset))
      
      logging.info("Initialization finished. Starting all workers.")
      start_event.set()
      
      jobs.join()
      
      # Countdownevent simulation
      countdown_done.wait()
      logging.info("All threads finished")
      logging.info("Total collected orders=%s", len(orders))
      for status, data in order_statuses.items():
        logging.info(
          "Status=%s data=%s",
          status,
          data,
        )
        
      logging.info("Overall stats=%s", overall_stats)
      
  except Timeout:
    print("Another instance is already running")
  
if __name__ == "__main__":
  main()