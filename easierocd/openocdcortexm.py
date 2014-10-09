from __future__ import absolute_import

import sys
import os
import logging

from easierocd.arm import dpidr_decode
import easierocd.stm32 as stm32
from easierocd.openocd import (OpenOcdError, TargetMemoryAccessError, TargetDapError)

class OpenOcdCortexMDetectError(Exception):
    pass

class AdapterDoesntSupportTransport(OpenOcdCortexMDetectError):
    def __init__(self, adapter, transport):
        (self.adapter, self.transport) = (adapter, transport)

    def __str__(self):
        return "debug adapter %r doesn't support transport %r" % (self.adapter, self.transport)

    __repr__ = __str__

class OpenOcdDoesntSupportTransportForAdapter(OpenOcdCortexMDetectError):
    def __init__(self, adapter, transport):
        (self.adapter, self.transport) = (adapter, transport)

    def __str__(self):
        return "debug adapter %r doesn't support transport %r" % (self.adapter, self.transport)

    __repr__ = __str__

class OpenOcdOpenFailedDuringInit(OpenOcdCortexMDetectError):
    pass

def chip_name_from_mcu_info(mcu_info):
    if mcu_info['silicon_vendor'] == 'st':
        return mcu_info['stm32_family']
    else:
        assert(0)

def openocd_low_level_transport_to_trasnport(t):
    # An example of an low level details of OpenOCD that we know and care about
    if t == 'hla_swd':
        return 'swd'
    elif t == 'hla_jtag':
        return 'jtag'
    elif t == 'cmsis-dap':
        # NOTE: revisit when OpenOCD cmsis-dap jtag works
        return 'swd'
    elif t in { 'swd', 'jtag' }:
        return t
    else:
        #import IPython; IPython.embed()
        raise ValueError

class OpenOcdCortexMDetect(object):
    '''
    Try hard to detect the target ARM CPU through OpenOCD
    Knows about the parciluarities of OpenOCD initialization
    Knows about popular ARM Cortex-M silicon
    Knows about common debug adapters

    FIXME: Cortex-M only
    FIXME: Single target CPU, single core only (really single microcontroller boards)
    '''
    def __init__(self, options, adapter, openocd_rpc):
        (self.options, self.adapter_info, self.usb_device, self.orpc) = (
            options, adapter[0], adapter[1], openocd_rpc)
        self.openocd_transport = None # 'swd', 'jtag'
        self.openocd_low_level_transport = None # 'hla', 'cmsis-dap', 'swd', 'jtag'

    def do_openocd_init(self, transport):
        if transport not in set(['swd', 'jtag']):
            raise AdapterDoesntSupportTransport('unsupported transport "%s"' % (transport,))
        
        self.openocd_transport = transport

        # Assume adapters support SWD
        adapter_supports_swd = self.adapter_info.get('supports_swd', True)
        # Assume adapters don't support JTAG
        adapter_supports_jtag = self.adapter_info.get('supports_jtag', False)
        # TODO: query adapter capabilities with things like cmsis-dap DAP_ID_DEVICE_VENDOR

        if (transport == 'swd')  and (not adapter_supports_swd):
            raise AdapterDoesntSupportTransport(self.adapter_info, transport)
        if (transport == 'jtag') and (not adapter_supports_jtag):
            raise AdapterDoesntSupportTransport(self.adapter_info, transport)

        # hard coding limitations for a specific OpenOCD version
        # Change when OpenOCD cmsis_dap_usb jtag support is tested and verified
        if (transport == 'jtag') and (self.adapter_info['openocd']['interface'] == 'cmsis-dap'):
            raise OpenOcdDoesntSupportTransportForAdapter(self.adapter_info, transport)

        # See e.g. documentation/stlink-v2-1-swd.cfg
        orpc = self.orpc
        o = self.adapter_info['openocd']
        ocd_intf = o['interface']

        orpc.command('interface %s' % (ocd_intf,))
        if ocd_intf == 'hla':
            hla_layout = o['hla_layout']
            orpc.command('hla_layout %s' % (hla_layout,))
            orpc.command('hla_device_desc %r' % (self.adapter_info['name'],))
            orpc.command('hla_vid_pid 0x%04x 0x%04x' % (self.usb_device.idVendor, self.usb_device.idProduct))
            # See http://wunderkis.de/stlink-serialno/index.html
            # orpc.command('hla_serial %r' % (self.usb_device.serial_number,))
        else:
            pass

        if ocd_intf == 'hla':
            if transport == 'swd':
                transport = 'hla_swd'
            elif transport == 'jtag':
                transport = 'hla_jtag'
            else:
                assert(0)

        # transport
        r = orpc.call('transport select %s' % (transport,))
        logging.debug('trasnport select -> %r' % (r,))
        self.openocd_low_level_transport = transport

        # adding adapter_khz to make OpenOCD happy, otherwise you'll see
        # Error: 156 6 core.c:1380 adapter_init(): An adapter speed is not selected in the init script. Insert a call to adapter_khz or jtag_rclk to proceed.
        orpc.command('adapter_khz 300')

    def openocd_init_for_detection(self, transport):
        self.do_openocd_init(transport)
        orpc = self.orpc

        # TAP / DAP
        self.newtap('EASIEROCD_DETECT cpu -irlen 0x4 -ircapture 0x1 -irmask 0xf -expected-id 0x00000000')
        # Target CPU
        r = orpc.call('target create EASIEROCD_DETECT.cpu cortex_m -chain-position EASIEROCD_DETECT.cpu')
        logging.debug('target create -> %r' % (r,))

        # assume adapter has the nRST signal
        adapter_has_reset_line = self.adapter_info.get('has_reset_line', True)
        if adapter_has_reset_line:
            r = orpc.command('reset_config srst_only')
        # FIXME: support srst_gate devices like the LPC1xxx
        r = orpc.command('reset_config connect_assert_srst')

        # MCU firmware possibly need to leave JTAG / SWD in usable state for a short time  after reset
        # for OpenOCD to successfully connect.
        # This is basically a race condition between the debug adapter and the firmware after reset.

        r = orpc.call('ocd_init')
        logging.debug('ocd_init -> %r' % (r,))
        responses = r.split(b'\n')
        for r in responses:
            if r == b'open failed':
                raise OpenOcdOpenFailedDuringInit

    def detect_dap(self):
        'Detect ARM CPU core through the Debug Access Port (assume ADI v5+)'
        info = None
        if self.openocd_transport is None:
            t = self.orpc.get_transport()
            if not t:
                raise TargetDapError(self.orpc, t)
            self.openocd_low_level_transport = t
            self.openocd_transport = openocd_low_level_transport_to_trasnport(self.openocd_low_level_transport)

        if self.openocd_transport == 'swd':
            idcode = self.orpc.idcode()
            info = dpidr_decode(idcode)
            info['idcode'] = idcode
        elif self.openocd_transport == 'jtag':
            assert(0)
        else:
            assert(0)
        assert(info is not None)
        return info

    def detect_mcu(self, dap_info):
        'differentiate Cortex-M mcu families'
        # See documentation/cortex-M-autodetection
        o = self.orpc
        try:
            stm32_idcode = o.read_word(stm32.DBGMCU_IDCODE_ADDR)
        except TargetMemoryAccessError:
            raise OpenOcdCortexMDetectError

        if stm32_idcode != 0 and stm32_idcode != 0xffffffff:
            # FIXME: may be too tolerant
            m = stm32.dbgmcu_idcode_decode(stm32_idcode)
            m['silicon_vendor'] = 'st'
            # 'STM32F405xx/07xx and STM32F415xx/17xx',
            m['stm32_family'] = (m['dev'].split()[0][:len('stm32**')]).lower()
            return m

        assert(0)
        # FIXME: handle this failure case, where there will be no flash algorithm
        return None

    def declare_flash_bank(self, dap_info, mcu_info):
        if mcu_info['silicon_vendor'] != 'st':
            assert(0)
        flash_algo = stm32.openocd_stm32_family_flash_algorithm(mcu_info['stm32_family'])
        self.orpc.call('flash bank %(chip_name)s.flash %(flash_algo)s 0 0 0 0 %(chip_name)s.cpu' % 
                      dict(chip_name=chip_name_from_mcu_info(mcu_info), flash_algo=flash_algo))

    def set_target_reset_config(self, dap_info, mcu_info):
        if not self.openocd_low_level_transport.startswith('hla_'):
            # "hla" -> high level adapters accept a "reset" command
            # and don't allow detailed control of how the reset is done
            # TODO: may not be right for multicore chips, e.g. 
            # target/lpc4350.cfg
            r = self.orpc.call('cortex_m reset_config sysresetreq')

        # assume adapter has the nRST signal
        adapter_has_reset_line = self.adapter_info.get('has_reset_line', True)
        reset_line_connected = getattr(self.options, 'reset_line_connected', True)
        if mcu_info['silicon_vendor'] == 'st' and adapter_has_reset_line and reset_line_connected:
            # FIXME: standalone adapters used with custom boards may not have SRST connected
            r = self.orpc.command('reset_config srst_only srst_nogate')

    def newtap(self, cmd_str_after_newdap_part):
        # TAP / DAP, see OpenOCD: target/swj-dp.tcl
        if self.openocd_low_level_transport.startswith('hla_'):
            newdap_cmd = 'hla newtap'
        elif self.openocd_low_level_transport == 'cmsis-dap':
            newdap_cmd = 'cmsis-dap newdap'
        elif self.openocd_low_level_transport == 'swd':
            newdap_cmd = 'swd newdap'
        elif self.openocd_low_level_transport == 'jtag':
            newdap_cmd = 'jtag newtap'
        newdap_cmd = newdap_cmd + ' ' + cmd_str_after_newdap_part
        self.orpc.command(newdap_cmd)

    def configure_reset_handlers(self, dap_info, mcu_info):
        # bin/easierocd-XX -> share/easierocd/
        # TODO: database of whether a chip has helper functions
        data_dir = os.path.realpath(os.path.join(os.path.dirname(sys.argv[0]), '..', 'share', 'easierocd'))
        if mcu_info['silicon_vendor'] == 'st' and mcu_info['stm32_family'] == 'stm32l1':
            self.orpc.call('source %s' % (os.path.join(data_dir, 'stm32l_helpers.cfg')))
            self.orpc.call('set _TARGETNAME %s.cpu' % (chip_name_from_mcu_info(mcu_info)))
            #  reset-start, restart-end handlers only fire on "openocd -c reset" (including 'reset init')
            #  reset-init handlers only fire on "openocd -c 'reset init'"
            self.orpc.call('source %s' % (os.path.join(data_dir, 'stm32l_handlers.cfg')))

    def openocd_init_for_cortex_m(self, transport, dap_info, mcu_info):
        # see documentation/stlink-v2-1-swd-stm32l.cfg
        self.do_openocd_init(transport)
        orpc = self.orpc

        # TAP / DAP
        chip_name = chip_name_from_mcu_info(mcu_info)
        self.newtap('%(chip_name)s cpu -irlen 0x4 -ircapture 0x1 -irmask 0xf -expected-id 0x00000000' % dict(chip_name=chip_name))

        # Target CPU
        r = orpc.call('target create %(chip_name)s.cpu cortex_m -chain-position %(chip_name)s.cpu' % dict(chip_name=chip_name))
        logging.debug('target create -> %r' % (r,))
        # Work Area
        # FIXME: hard coding work_area_length
        r = orpc.call('%(chip_name)s.cpu configure -work-area-phys 0x%(ram_origin)x -work-area-size 0x%(work_area_size)x '
                      '-work-area-backup 0' % 
                      dict(chip_name=chip_name, ram_origin=0x2*0x1000*0x10000, work_area_size=10*1024))

        # Declaring flash regsions effectively determines the memory map for single MCU boards
        # with no external memory.
        # gdb's 'load', 'break' commands need to differentiate between flash and ram to work 
        self.declare_flash_bank(dap_info, mcu_info)
        # TODO: boards like STM32F429Discover have builtin debug adapters and external RAM.
        # We should detect the board somehow (USB IDs?) and declare external RAM bank.
        # For other boards with external memory but no way to ID the board,
        # give the user a way to provide an OpenOCD "init_board" procedure.

        self.set_target_reset_config(dap_info, mcu_info)
        self.configure_reset_handlers(dap_info, mcu_info)

        r = orpc.call('ocd_init')
        logging.debug('ocd_init -> %r' % (r,))
        responses = r.split(b'\n')
        for r in responses:
            if r == b'open failed':
                raise OpenOcdOpenFailedDuringInit
