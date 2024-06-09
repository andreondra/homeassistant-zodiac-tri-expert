import serial
from pathlib import Path

import serial.rs485

class Aqualink:
    def __init__(self, device_path : Path):
        self.device = serial.rs485.RS485(device_path, baudrate = 9600)
    
    def test(self):
        pass