import serial
import logging
from pathlib import Path
from time import sleep
import serial.rs485

from .constants         import *
from .aqualink_protocol import *

_LOGGER = logging.getLogger(__name__)

class Aqualink:
    
    PACKET_FOOTER        = bytes([0x10, 0x03])

    def __init__(self, device_path : Path):
        self.device = serial.Serial(device_path,
            baudrate = 9600,
            bytesize = serial.EIGHTBITS,
            parity   = serial.PARITY_NONE, 
            stopbits = serial.STOPBITS_ONE,
            timeout  = 5
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

            timeout_count = 0
            while len(received_data) < 2 or received_data[-2:] != self.PACKET_FOOTER:
                received_byte  = self.device.read(1)
                if len(received_byte) < 1:
                    _LOGGER.warning(f"Timeout waiting for response byte!")
                    timeout_count += 1

                    if timeout_count == TIMEOUT_LIMIT:
                        _LOGGER.error("Communication timed out!")
                        raise TimeoutError()
                else:
                    _LOGGER.debug(f"Received byte: {received_byte.hex()}")
                    received_data += received_byte
            _LOGGER.debug(f"All data received!")
            _LOGGER.debug(f"Received data: {received_data.hex()}")
        
        return received_data

    def send_command(self, command : AqualinkCommand):
        raw_response = self.sendrecv(command.to_bytes())
        return command.process_response(raw_response)

    def loop(self):

        success_probe = True
        while True:
            try:
                response = self.send_command(ProbeCommand())
                assert isinstance(response, ProbeResponse), "Probe reponse incorrect type!"
            except (ResponseMalformedException, TimeoutError):
                _LOGGER.error("Error sending probe, retrying!")
                success_probe = False

            if not success_probe:
                sleep(5)
                continue
            
            sleep(5)

            try:
                response = self.send_command(IdCommand())
                assert isinstance(response, IdResponse), "ID reponse incorrect type!"
            except (ResponseMalformedException, TimeoutError):
                _LOGGER.error("Error sending ID command!")

            # Wait a moment before sending another command.
            sleep(5)
        
        # while(True):
        #     self.sendrecv(self.build_cmd(bytes([0x00])))
        #     sleep(5)
        #     self.sendrecv(self.build_cmd(bytes([0x14, 0x01])))
        #     sleep(5)

        # self.device.write(bytes([0x10, 0x02, 0x50, 0x00, 0x62, 0x10, 0x03]))
        # data = self.device.read(1)
        # print(data)