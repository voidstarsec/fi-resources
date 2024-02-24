import serial
import struct
import time
import sys
import logging

# Configure and create the serial connection
port="/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A5XK3RJT-if00-port0"
baud_rate = 115200  # Set the baud rate to match your STM32 bootloader configuration
timeout = .2  # Set the timeout value as needed
ser = serial.Serial(port, baud_rate, parity="E", timeout=timeout)


# Helper function to send a bootloader command and receive the response
def send_command(command, cmd_response=2, more_dat=False):
    ser.write(command.to_bytes())  # Send the command
    time.sleep(0.01)  # Wait for a short delay to allow the response to be processed
    response = ser.read(command.read_len)
    return response

class BootloaderCommand:
    def __init__(self, command_byte):
        self.command_byte = command_byte
        self.checksum = 0
        self.read_len = 2
        if self.command_byte != 0x7F:
            self.get_checksum()

    def to_bytes(self):
        if self.command_byte != 0x7F:
            return bytes([self.command_byte, self.checksum])
        else:
            return bytes([self.command_byte])

    def get_checksum(self):
        self.checksum = (~self.command_byte) & 0xFF


class SetBaudRate(BootloaderCommand):
    def __init__(self):
        super().__init__(0x7F)


class GetCommand(BootloaderCommand):
    def __init__(self):
        super().__init__(0x00)


class GetVersionCommand(BootloaderCommand):
    def __init__(self):
        super().__init__(0x01)


class GetIDCommand(BootloaderCommand):
    def __init__(self):
        super().__init__(0x02)


class ReadMemoryCommand(BootloaderCommand):
    def __init__(self, ):
        super().__init__(0x11)


class MemoryAddrCommand():
    def __init__(self, address):
        self.address = address
        self.xsum = 0
        self.read_len = 2
        self.calculate_checksum()

    def to_bytes(self):
        addr_str = b''
        addr_str += struct.pack(">I", self.address)
        addr_str += struct.pack("B", self.xsum)
        return addr_str

    def calculate_checksum(self):
        self.xsum = 0
        for x in range(0, 32, 8):
            val = (self.address >> x) & 0xFF
            self.xsum ^= val


class MemoryLenCommand(BootloaderCommand):
    def __init__(self, length):
        super().__init__(length)
        self.read_len = length + 3


class GoCommand(BootloaderCommand):
    def __init__(self, address):
        super().__init__(0x21)
        self.address = address

    def to_bytes(self):
        command_bytes = super().to_bytes()
        address_bytes = self.address.to_bytes(4, 'little')
        return command_bytes + address_bytes


class EraseMemoryCommand(BootloaderCommand):
    def __init__(self, address, num_pages):
        super().__init__(0x43)
        self.address = address
        self.num_pages = num_pages

    def to_bytes(self):
        command_bytes = super().to_bytes()
        address_bytes = self.address.to_bytes(4, 'little')
        num_pages_bytes = self.num_pages.to_bytes(2, 'little')
        return command_bytes + address_bytes + num_pages_bytes


class WriteMemoryCommand(BootloaderCommand):
    def __init__(self, address, data):
        super().__init__(0x31)
        self.address = address
        self.data = data

    def to_bytes(self):
        command_bytes = super().to_bytes()
        address_bytes = self.address.to_bytes(4, 'little')
        data_length_bytes = len(self.data).to_bytes(2, 'little')
        return command_bytes + address_bytes + data_length_bytes + self.data

def read_memory(address, size,scope):
    logger = logging.getLogger('GDBG')
    logger.setLevel(logging.DEBUG)
    response = None
    read_sequence = [
        ReadMemoryCommand(),
        MemoryAddrCommand(address),
        MemoryLenCommand(size),
    ]
    for cmd in read_sequence:
        response = send_command(cmd)
        time.sleep(.01)
        if len(response) == 0:
            return None
        if response[0] == '\x1f':
            logger.debug(f"NACK CMD: {cmd.to_bytes()} Resp: {response}")
            return None
        logger.debug(f"CMD: {cmd.to_bytes()} Resp: {response}")
    return response

