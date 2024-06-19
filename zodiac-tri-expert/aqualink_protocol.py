import logging
from abc import ABCMeta, abstractmethod

from .exceptions import *

_LOGGER = logging.getLogger(__name__)

class AqualinkPacket:
    PACKET_HEADER        = bytes([0x10, 0x02])
    PACKET_DEST_AQUALINK = bytes([0xB0])
    PACKET_FOOTER        = bytes([0x10, 0x03])

    # Checksum is calculated as sum of all previous bytes mod 256.
    def _checksum(self, data : bytes) -> bytes:
        return (sum(data) % 256).to_bytes(1, 'little')

class AqualinkResponse(AqualinkPacket):
    def __init__(self, raw_data : bytes):
        _LOGGER.debug(f"Parsing response: {raw_data.hex()}")
        if len(raw_data) < 5:
            _LOGGER.error("Response too short!")
            raise ResponseMalformedException()
        if raw_data[0:2] != self.PACKET_HEADER:
            _LOGGER.error("Reponse header malformed!")
            raise ResponseMalformedException()
        if raw_data[-2:] != self.PACKET_FOOTER:
            _LOGGER.error("Reponse footer malformed!")
            raise ResponseMalformedException()
        if raw_data[-3].to_bytes() != self._checksum(raw_data[0:-3]):
            _LOGGER.error("Reponse checksum malformed!")
            raise ResponseMalformedException()
        
        self.payload = raw_data[2:-3]

class AqualinkCommand(AqualinkPacket):
    def __init__(self, payload : bytes):
        command = bytearray()
        command += self.PACKET_HEADER + self.PACKET_DEST_AQUALINK
        command += payload
        command += self._checksum(command)
        command += self.PACKET_FOOTER
        _LOGGER.debug(f"Built command: {command.hex()}")

        self.command_bytes = command

    def to_bytes(self) -> bytes:
        return self.command_bytes
    
    @abstractmethod
    def process_response(self, raw_data : bytes) -> AqualinkResponse:
        pass

class ProbeCommand(AqualinkCommand):
    def __init__(self):
        super().__init__(bytes([0x00]))

    def process_response(self, raw_data : bytes) -> "ProbeResponse":
        return ProbeResponse(raw_data)

class IdCommand(AqualinkCommand):
    def __init__(self):
        super().__init__(bytes([0x14, 0x01]))

    def process_response(self, raw_data : bytes) -> "IdResponse":
        return IdResponse(raw_data)

class ProbeResponse(AqualinkResponse):
    def __init__(self, raw_data : bytes):
        super().__init__(raw_data)

class IdResponse(AqualinkResponse):
    def __init__(self, raw_data : bytes):
        super().__init__(raw_data)
        self.id = self.payload.decode('ascii')
        _LOGGER.debug(f"Decoded ID: {self.id}")


