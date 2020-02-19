import logging
import threading
import time

from media_server import config
from .SIPWavePlayer import SIPWavePlayer


def main():
    logging.basicConfig(level=config.LOGLEVEL, format='%(asctime)s [%(levelname)s] %(message)s')

    run_event = threading.Event()
    run_event.set()

    application = SIPWavePlayer(run_event)
    application.next_call()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received. Attempting to close SIP application...")
        run_event.clear()
        application.stop()
        logging.info("SIP application closed successfully")


if __name__ == '__main__':
    main()
