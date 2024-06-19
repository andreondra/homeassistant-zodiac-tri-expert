import logging
import sys

from .aqualink import Aqualink

_LOGGER = logging.getLogger(__name__)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    al = Aqualink("/dev/ttyUSB0")

    try:
        al.loop()
    except KeyboardInterrupt:
        print("Interrupted, exiting!")
        sys.exit(130)