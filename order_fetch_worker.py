import logging
import queue

from api_client import fetch_orders_chunk
from order_mapper import structure_orders

from config import BATCH_SIZE

def order_fetch_worker(
  worker_id: int,
  jobs: queue.Queue,
  token: str,
  overall_stats: dict,
  overall_stats_lock,
  order_status_lock,
  orders: list[dict],
  orders_lock,
  start_event,
  countdown_event_sim,
  countdown_lock,
  countdown_done
) -> None:
  start_event.wait()
  logging.info("Worker[%s] started", worker_id)
  try:
    while True:
      try:
        chunk_index, order_status, order_status_data, offset = jobs.get_nowait()
      except queue.Empty:
        logging.info("Worker [%s]: No more jobs, exiting", worker_id)
        break

      try:
        logging.info(
          "Worker[%s] processing status=%s offset=%s",
          worker_id,
          order_status,
          offset,
        )
        
        logging.info(
          "Fetching chunk %s/%s status=%s",
          chunk_index + 1,
          order_status_data["chunks"],
          order_status,
        )
        response_orders = fetch_orders_chunk(order_status, offset, token)
        structured_orders = structure_orders(response_orders)
        
        with orders_lock:
          orders.extend(structured_orders)
        
        with overall_stats_lock:
          overall_stats["processed_chunks"] += 1
          overall_stats["processed_orders"] += len(structured_orders)
          
        with order_status_lock:
          order_status_data["processed_chunks"] += 1
          
        logging.info(
          "Worker[%s] finished order status=%s offset=%s orders=%s",
          worker_id,
          order_status,
          offset,
          len(structured_orders),
        )
        
        # Check if last chunk is processed
        with order_status_lock:        
          is_last_chunk = chunk_index + 1 >= order_status_data["chunks"]

          if is_last_chunk:
            if len(structured_orders) == BATCH_SIZE:
              next_i = order_status_data["chunks"]
              next_offset = next_i * BATCH_SIZE

              order_status_data["chunks"] += 1
              jobs.put((next_i, order_status, order_status_data, next_offset))

              logging.info(
                "Added extra chunk %s/%s status=%s offset=%s",
                next_i + 1,
                order_status_data["chunks"],
                order_status,
                next_offset,
              )
            else:
              logging.info(
                "Status finished status=%s fetched_last_chunk=%s",
                order_status,
                len(structured_orders),
              )
        
      except Exception:
        with overall_stats_lock:
          overall_stats["failed_chunks"] += 1
        
        logging.exception(
          "Thread[%s] failed order status=%s offset=%s",
          worker_id,
          order_status,
          offset,
        )
      finally:
        jobs.task_done()
  finally:
    with countdown_lock:
      countdown_event_sim["count"] -= 1
      remaining = countdown_event_sim["count"]

      logging.info("Worker[%s] exited, remaining=%s", worker_id, remaining)

      if remaining == 0:
        countdown_done.set()