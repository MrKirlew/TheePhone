import logging, sys

def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    fmt = "[%(asctime)s] %(levelname)s %(name)s :: %(message)s"
    logging.basicConfig(level=logging.INFO, handlers=[handler], format=fmt)
    logging.getLogger("google").setLevel(logging.WARNING)

setup_logging()