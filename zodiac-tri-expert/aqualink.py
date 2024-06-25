import serial
import logging
from pathlib import Path
from time import sleep
import serial.rs485
from dataclasses import dataclass

from .constants         import *
from .aqualink_protocol import *
from .exceptions        import *

_LOGGER = logging.getLogger(__name__)

class Aqualink:

    PACKET_FOOTER        = bytes([0x10, 0x03])

    @dataclass
    class OperationalStatus:
        ph_setpoint  : float
        ph_current   : float
        acl_setpoint : int
        acl_current  : int

    def __init__(self, device_path : Path):
        self.device = serial.Serial(device_path,
            baudrate = 9600,
            bytesize = serial.EIGHTBITS,
            parity   = serial.PARITY_NONE, 
            stopbits = serial.STOPBITS_ONE,
            timeout  = 2
        )

        self.device.reset_output_buffer()
        self.device.reset_input_buffer()

        _LOGGER.debug(f"Is open: {self.device.is_open}")
        _LOGGER.debug(f"Device name: {self.device.name}")
        _LOGGER.debug(f"Baudrate: {self.device.baudrate}")

    # Sends a packet and receives data until a '0x10 0x03' sequence is received,
    # or skips recv phase if no_recv is true.
    # Raises TimeoutError on timeout.
    def sendrecv(self, data : bytes, no_recv = False):
        self.device.reset_output_buffer()
        self.device.reset_input_buffer()
    
        self.device.write(data)
        self.device.flush()
        _LOGGER.debug(f"Sent data: {data.hex()}")

        received_data = bytearray()
        if not no_recv:
            _LOGGER.debug(f"Waiting for response...")

            header_received = False
            timeout_count = 0
            invalid_recv  = 0
            while len(received_data) < 2 or received_data[-2:] != AqualinkPacket.PACKET_FOOTER:
                received_byte  = self.device.read(1)
                if len(received_byte) < 1:
                    _LOGGER.warning(f"Timeout waiting for response byte!")
                    timeout_count += 1

                    if timeout_count == TIMEOUT_LIMIT:
                        _LOGGER.error("Communication timed out!")
                        raise TimeoutError()
                # This is to sync with packet start.
                elif not header_received:
                    _LOGGER.debug(f"Received byte: {received_byte.hex()}")
                    if received_byte == 0x10.to_bytes():
                        header_received = True
                        received_data += received_byte
                    else:
                        invalid_recv += 1
                else:
                    _LOGGER.debug(f"Received byte: {received_byte.hex()}")
                    received_data += received_byte

                if len(received_data) > AqualinkPacket.MAX_PACKET_LEN:
                    raise ResponseMalformedException()
                if invalid_recv > 20: # Twenty leading zeroes should be enough.
                    _LOGGER.debug("Too many invalid bytes!")
                    raise ResponseMalformedException()

            _LOGGER.debug(f"All data received!")
            _LOGGER.debug(f"Received data: {received_data.hex()}")
        
        return received_data

    def send_command(self, command : AqualinkCommand):
        raw_response = self.sendrecv(command.to_bytes())
        return command.process_response(raw_response)

    # Try to probe the device.
    # Raises NoResponseException if timed out or response was malformed.
    def probe(self):
        try:
            response = self.send_command(ProbeCommand())
            assert isinstance(response, ProbeResponse), "Probe reponse incorrect type!"
        except (ResponseMalformedException, TimeoutError):
            _LOGGER.error("Error sending probe!")
            raise NoResponseException

    # Try to get ID of the device.
    # Raises NoResponseException if timed out or response was malformed.
    def get_id(self) -> str:
        try:
            response = self.send_command(IdCommand())
            assert isinstance(response, IdResponse), "Get ID reponse incorrect type!"
        except (ResponseMalformedException, TimeoutError):
            _LOGGER.error("Error sending get ID!")
            raise NoResponseException
        return response.id

    # Try to set chlorinator output power % and receive operational information.
    # Output power has to be in range [0, 101] (101 for boost).
    # Raises NoResponseException if timed out or response was malformed.
    def set_output_get_info(self, output_power : int) -> OperationalStatus:
        assert 0 <= output_power <= 101, "Output power out of range!"
        try:
            response = self.send_command(SetOutputCommand(output_power))
            assert isinstance(response, SetOutputResponse), "Set output reponse incorrect type!"
        except (ResponseMalformedException, TimeoutError):
            _LOGGER.error("Error sending output command!")
            raise NoResponseException

        return self.OperationalStatus(
            response.ph_setpoint,
            response.ph_current,
            response.acl_setpoint,
            response.acl_current
        )
