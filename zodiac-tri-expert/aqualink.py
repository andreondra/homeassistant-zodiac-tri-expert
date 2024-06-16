import serial
import logging
from pathlib import Path
from time import sleep
import serial.rs485

_LOGGER = logging.getLogger(__name__)

class Aqualink:
    
    PACKET_HEADER        = bytes([0x10, 0x02])
    PACKET_DEST_AQUALINK = bytes([0x50])
    PACKET_FOOTER        = bytes([0x10, 0x03])
        
    def __init__(self, device_path : Path):
        self.device = serial.Serial(device_path,
            baudrate = 9600,
            bytesize = serial.EIGHTBITS,
            parity   = serial.PARITY_NONE, 
            stopbits = serial.STOPBITS_ONE
        )

        # self.device.rs485_mode = serial.rs485.RS485Settings(
        #     rts_level_for_tx = False,
        #     rts_level_for_rx = True,
        #     delay_before_tx  = None,
        #     delay_before_rx  = None
        # )

        self.device.reset_output_buffer()
        self.device.reset_input_buffer()

        _LOGGER.debug(f"Is open: {self.device.is_open}")
        _LOGGER.debug(f"Device name: {self.device.name}")
        _LOGGER.debug(f"Baudrate: {self.device.baudrate}")
        _LOGGER.debug(f"RTS/CTS: {self.device.rtscts}")
        _LOGGER.debug(f"xonxoff: {self.device.xonxoff}")
    
    # Checksum is calculated as sum of all previous bytes mod 256.
    def checksum(self, data : bytes) -> bytes:
        return (sum(data) % 256).to_bytes(1, 'little')

    def build_cmd(self, payload : bytes) -> bytes:
        command = bytearray()
        command += self.PACKET_HEADER + self.PACKET_DEST_AQUALINK
        command += payload
        command += self.checksum(command)
        command += self.PACKET_FOOTER

        _LOGGER.debug(f"Built command: {command.hex()}")

        return command

    # Sends a packet and receives data until a '0x10 0x03' sequence is received,
    # or skips recv phase if no_recv is true.
    def sendrecv(self, data : bytes, no_recv = False):
        self.device.write(data)
        self.device.flush()

        received_data = bytearray()
        if not no_recv:
            while len(received_data) < 2 or received_data[-2:] != self.PACKET_FOOTER:
                _LOGGER.debug(f"In waiting: {self.device.in_waiting}")
                received_byte  = self.device.read(1)
                _LOGGER.debug(f"Received byte: {received_byte.hex()}")
                received_data += received_byte
        
            _LOGGER.debug(f"Received data: {received_data.hex()}")

    def test(self):
        while(True):
            self.sendrecv(self.build_cmd(bytes([0x00])), no_recv = False)
            sleep(10)
        # self.sendrecv(self.build_cmd(bytes([0x14, 0x01])))
        # self.device.write(bytes([0x10, 0x02, 0x50, 0x00, 0x62, 0x10, 0x03]))
        # data = self.device.read(1)
        # print(data)