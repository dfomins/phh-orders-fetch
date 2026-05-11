import logging

def setup_logging():
  logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s",
  )

  logging.getLogger("urllib3").setLevel(logging.WARNING)
  logging.getLogger("pymongo").setLevel(logging.WARNING)