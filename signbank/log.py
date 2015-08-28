
import logging
import sys
from django.conf import settings

def init_logging():
    if settings.DO_LOGGING:
        logging.basicConfig(filename=settings.LOG_FILENAME, level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

def debug(msg):
    logging.debug(msg)

logInitDone=False
if not logInitDone:
    logInitDone = True
    init_logging()
