import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
