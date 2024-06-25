import logging
from abc import ABCMeta, abstractmethod

from .exceptions import *

_LOGGER = logging.getLogger(__name__)

######################################################################
# Generic (command/response) packet
######################################################################
class AqualinkPacket:
    PACKET_HEADER        = bytes([0x10, 0x02])
    PACKET_DEST_AQUALINK = bytes([0xB0])
    PACKET_FOOTER        = bytes([0x10, 0x03])
    MAX_PACKET_LEN       = 40 # A little headroom for possible longer IDs.

    # Checksum is calculated as sum of all previous bytes mod 256.
    def _checksum(self, data : bytes) -> bytes:
        return (sum(data) % 256).to_bytes(1, 'little')

######################################################################
# Responses
######################################################################

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

class ProbeResponse(AqualinkResponse):
    def __init__(self, raw_data : bytes):
        super().__init__(raw_data)

class IdResponse(AqualinkResponse):
    def __init__(self, raw_data : bytes):
        super().__init__(raw_data)
        raw_string = self.payload[1:].decode('ascii')
        self.id = ''.join(c for c in raw_string if c.isprintable())
        _LOGGER.debug(f"Decoded ID: '{self.id}'")

class SetOutputResponse(AqualinkResponse):
    def __init__(self, raw_data : bytes):
        super().__init__(raw_data)
        if len(raw_data) < 15:
            raise ResponseMalformedException
        
        self.ph_setpoint  = float(raw_data[8]) / 10
        self.acl_setpoint = raw_data[9] * 10
        self.ph_current   = float(raw_data[10]) / 10
        self.acl_current  = raw_data[11] * 10

        _LOGGER.debug(f"pH setpoint/current: {self.ph_setpoint}/{self.ph_current}")
        _LOGGER.debug(f"acl setpoint/current: {self.acl_setpoint}/{self.acl_current}")

######################################################################
# Commands
######################################################################

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
    
class SetOutputCommand(AqualinkCommand):
    def __init__(self, output_percent : int):
        assert 0 <= output_percent <= 101, "Output percent not in range!" # 101 for Boost mode.
        output_bytes = output_percent.to_bytes(1, 'little')
        super().__init__(bytes([0x11]) + output_bytes)

    def process_response(self, raw_data : bytes) -> "SetOutputResponse":
        return SetOutputResponse(raw_data)

