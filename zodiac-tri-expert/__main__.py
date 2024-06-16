import logging

from .aqualink import Aqualink

_LOGGER = logging.getLogger(__name__)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    al = Aqualink("/dev/ttyNS0")
    # al.test()