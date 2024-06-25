import logging
import sys

from .aqualink   import Aqualink
from .hass       import ZodiacHomeAssistant
from .exceptions import *

_LOGGER = logging.getLogger(__name__)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    print("Setting up Home Assistant integration!")
    try:
        ha = ZodiacHomeAssistant()
    except CantConnectToZodiac:
        print("Can't connect to the Zodiac!")
        sys.exit(1)
    print("All set up!")
    try:
        ha.loop()
    except KeyboardInterrupt:
        print("Interrupted, exiting!")
        sys.exit(130)
    except FatalError:
        print("Fatal error, terminating!")
        sys.exit(1)
