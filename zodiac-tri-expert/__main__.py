import logging
import sys

from .aqualink import Aqualink
from .hass     import ZodiacHomeAssistant

_LOGGER = logging.getLogger(__name__)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("Setting up Home Assistant integration!")
    ha = ZodiacHomeAssistant()
    print("All set up!")
    try:
        ha.loop()
    except KeyboardInterrupt:
        print("Interrupted, exiting!")
        sys.exit(130)