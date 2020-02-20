import logging
import threading
import time

from media_server import config
from .SIPWavePlayer import SIPWavePlayer


def main():
    """
    Main function that starts the application and listens for keyboard interrupts that will stop the application.
    """
    logging.basicConfig(level=config.LOGLEVEL, format='%(asctime)s [%(levelname)s] %(message)s')

    run_event = threading.Event()
    run_event.set()

    application = SIPWavePlayer(run_event)
    application.next_call()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received - attempting to stop application")
        run_event.clear()
        application.stop()
        logging.info("Application stopped successfully")


if __name__ == '__main__':
    main()
