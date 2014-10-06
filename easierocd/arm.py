from __future__ import absolute_import

import logging

# ARM Debug Interface, ADIv5.0 to ADIv5.2
# See https://silver.arm.com/download/ARM_and_AMBA_Architecture/AR551-DA-70001-r0p0-01rel0/IHI0031C_debug_interface_as.pdf

def dpidr_decode(v):
    # revision: implementation defined
    revision = (v >> 28) & 0x0f
    # partno: part number of debug port
    partno   = (v >> 20) & 0xff
    reserved = (v >> 17) & 0x03
    # mindp: (1: transaction counter, pushed-verify, pushed-find not implemented)
    mindp    = (v >> 16) & 0x01
    # version of DP Architecture implemented (1: DPv1, 2: DPv2)
    version  = (v >> 12) & 0x0f
    # JEDEC designer ID, ARM: 0x23b
    designer = (v >> 1) & 0x7ff
    # always reads as one
    rao      = (v >> 0) & 0x01
    out = locals()
    del out['v']
    return out

class ArmCpuDetectionError(Exception):
    pass

class AdapterDoesntSupportTransport(ArmCpuDetectionError):
    def __init__(self, adapter, transport):
        (self.adapter, self.transport) = (adapter, transport)

    def __str__(self):
        return "debug adapter %r doesn't support transport %r" % (self.adapter, self.transport)

    __repr__ = __str__

class OpenOcdDoesntSupportTransportForAdapter(ArmCpuDetectionError):
    def __init__(self, adapter, transport):
        (self.adapter, self.transport) = (adapter, transport)

    def __str__(self):
        return "debug adapter %r doesn't support transport %r" % (self.adapter, self.transport)

    __repr__ = __str__


class ArmCpuDetection(object):
    '''
    Try hard to detect the target ARM CPU through OpenOCD
    Knows about the parciluarities of OpenOCD initialization
    Knows about popular ARM Cortex-M silicon
    Knows about common debug adapters

    FIXME: Cortex-M only
    FIXME: Single target CPU, single core only
    '''
    def __init__(self, adapter, openocd_rpc):
        (self.adapter_info, self.usb_device, self.orpc) = (
            adapter[0], adapter[1], openocd_rpc)

    def openocd_init_for_detection(self, transport):
        if transport not in set(['swd', 'jtag']):
            raise AdapterDoesntSupportTransport('unsupported transport "%s"' % (transport,))

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
            orpc.command('hla_serial %r' % (self.usb_device.serial_number,))
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

        # adding adapter_khz to make OpenOCD happy, otherwise you'll see
        # Error: 156 6 core.c:1380 adapter_init(): An adapter speed is not selected in the init script. Insert a call to adapter_khz or jtag_rclk to proceed.
        orpc.command('adapter_khz 300')

        # TAP (doesn't really make sense for SWD)
        orpc.command('hla newtap EASIEROCD_CHIP cpu -irlen 0x4 -ircapture 0x1 -irmask 0xf -expected-id 0x00000000')
        # Target
        r = orpc.call('target create EASIEROCD_CHIP.cpu cortex_m -chain-position EASIEROCD_CHIP.cpu')
        logging.debug('target create -> %r' % (r,))

    def detect_dap(self):
        'Detect ARM CPU core through the Debug Access Port (assume ADI v5+)'
        pass

    def detect_mcu(self):
        # TODO: differentiate Cortex-M mcu families
        # See documentation/cortex-m-autodetection
        pass

def test():
    # http://infocenter.arm.com/help/index.jsp?topic=/com.arm.doc.faqs/ka16088.html
    cortex_m0_r0p0 = 0x0bb11477
    cortex_m0p_r0p0_dp1 = 0x0bc11477 # DP Architecture 1
    cortex_m0p_r0p0_dp2 = 0x0bc12477 # DP Architecture 2
    # texan/stlink
    cortex_m3_r1 = 0x1ba00477
    cortex_m3_r2 = 0x4ba00477
    cortex_m4_r0 = 0x2ba01477

    # texan/stlink & OpenOCD
    energy_micro_m3m4 = 0x2ba01477
    lpc4350 = 0x2ba01477
    kl46 = 0x0bc11477
    stm32f1 = 0x1ba01477
    stm32f2 = 0x2ba01477
    stm32vl = 0x1ba01477
    stm32l  = 0x2ba01477
    stm32f3 = 0x2ba01477
    stm32f4 = 0x2ba01477
    stm32f0 = 0x0bb11477
    l = locals()

    experiment = True

    if experiment:
        from easierocd.util import HexDict
        import pprint
        items = l.items()
        items.sort()
        for (n, v) in items:
            idr = dpidr_decode(v)
            pprint.pprint((n, HexDict(idr)))

if __name__ == '__main__':
    test()
