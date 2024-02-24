import os
import gdb
import struct

# Register addresses
RCC_APB2ENR = 0x40021018
AFIO_MAPR = 0x40010004
# Debug MCU configuration register
DBGMCU_CR = 0xe0042004
# Debud Exception and Monitor Control Register; we need to set the TRCENA bit to enable access to the TPIU
COREDEBUG_DEMCR = 0xe000edfc
# TPIU Acychronous Clock Prescaler Register
TPI_ACPR = 0xe0040010
# TPIO Selected Pin Protocol Register
TPI_SPPR = 0xe00400f0
# Formatter and flush control register
TPI_FFCR = 0xe0040304
# Device ID - if last bit is set, we have ETM enabled - Cortex M4 manual, page 106
TPI_DEV_ID = 0xE0040FC8
# Data Watchpoint and Trace Control Register - defined in ARMv7 Architecture Manual page 879
DWT_CTRL = 0xe0001000
# ITM Lock Access Register
ITM_LAR = 0xe0000fb0
# ITM Trace Control Register
ITM_TCR = 0xe0000e80
# ITM Trace Enable - Each bit corresponds to a stimulus port to enable
ITM_TER = 0xe0000e00
# ITM Trace Privilege Register - enabled various tracing ports
ITM_TPR = 0xE0000E40
ETM_LAR = 0xe0041fb0
ETM_CR = 0xe0041000
ETM_TRACEIDR = 0xe0041200
ETM_TECR1 = 0xe0041024
ETM_FFRR = 0xe0041028
ETM_FFLR = 0xe004102c
# ETM Trigger Event Register
ETM_TER = 0xe0041008
ETM_TEE	= 0xE0041020


def writeInt(address,value):
    target = gdb.inferiors()[0]
    target.write_memory(address,struct.pack("I",value),4)
    return

def writeShort(address,value):
     target = gdb.inferiors()[0]
     target.write_memory(address,struct.pack("H",value),2)
     return

# We are running on a firmware image here, no threading so this _should_ be OK.
def setBit(address,mask):
    target = gdb.inferiors()[0]
    targetVal = target.read_memory(address,4)
    targetVal = struct.unpack("I",targetVal.tobytes())[0]
    print(f"Read memory value 0x{targetVal:08X} at address 0x{address:X}")
    targetVal |= mask
    print(f"Writing memory value 0x{targetVal:08X} at address 0x{address:X}")
    targetVal = target.write_memory(address,struct.pack("I",targetVal),4)
    return

def clearBit(address,mask):
    target = gdb.inferiors()[0]
    targetVal = target.read_memory(address,4)
    targetVal = struct.unpack("I",targetVal.tobytes())[0]
    print(f"Read memory value 0x{targetVal:08X} at address 0x{address:X}")
    targetVal &= ~mask
    print(f"Writing memory value 0x{targetVal:08X} at address 0x{address:X}")
    targetVal = target.write_memory(address,struct.pack("I",targetVal),4)
    return

class enableDBG(gdb.Command):
    def __init__(self):
        super(enableDBG, self).__init__(
            "enableDBG", gdb.COMMAND_USER
        )
    def invoke(self, args, from_tty):
        setBit(DBGMCU_CR,0x20)
        setBit(COREDEBUG_DEMCR,0x1000000)

class configureTPIU(gdb.Command):
    def __init__(self):
        super(configureTPIU, self).__init__(
                "configureTPIU", gdb.COMMAND_USER
                )

    def invoke(self,args,from_tty):
        writeInt(TPI_ACPR, 15) # Trace clock divider HCLK/(x+1)
        # TPIO Reg - Selected pin protocol
        writeInt(TPI_SPPR,2)# Pin protocol: 0 = Sync Trace Port Mode, 1 = NRZ, 2 =USART, 3 = Reserved
        # TPIO Reg: Formatter and flush control
        writeInt(TPI_FFCR,0x102)# Enable TPIU framing (0x100 to disable)

class enableETM(gdb.Command):
    def __init__(self):
        super(enableETM, self).__init__(
                "enableETM", gdb.COMMAND_USER
                )

    def invoke(self,args,from_tty):
        writeInt(DWT_CTRL,0x40011a01)
        # ETM configuration example
        # Write 0xC5AC CE55 to the ETM Lock Access Register to unlock the write accesITM registers
        writeInt(ETM_LAR , 0xC5ACCE55)
        # Write 0x0000 1D1E to the ETM control register (configure the trace)
        #writeInt(ETM_CR , 0x00001D1E 
        writeInt(ETM_CR , 0x00201d0e)
        # Set stream
        writeInt(ETM_TRACEIDR, 1) # TraceBusID 1
        # Write 0x0000 406F to the ETM Trigger Event register (define the trigger event)
        writeInt(ETM_TER , 0x0000406F)
        # Write 0x0000 006F to the ETM Trace Enable Event register (define an event to start/stop)
        writeInt(ETM_TEE, 0x0000006F)
        # Write 0x0000 0001 to the ETM Trace Start/stop register (enable the trace)
        writeInt(ETM_TECR1, 0x00000001)
        # Write 0x0000191E to the ETM Control Register (end of configuration)
        writeInt(ETM_CR , 0x0000191E)

enableDBG()
configureTPIU()
enableETM()
