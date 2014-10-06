from __future__ import absolute_import

# FIXME: make list of supported debug adapters easy and safe to update (maybe turn it into data and not code?)
_DEBUG_ADAPTERS_DATA = [ {
        'name': 'ST-Link/V2-1',
        'usb_vid': 0x0483, 'usb_pid': 0x374b, # ID 0483:374b STMicroelectronics 
        # debug probe built into ST Nucleo boards, or
        # can be used as a stand alone SWD debug probe by removing jumpbers
        'supports_jtag': False, # SWD only
        'default_target_supports_swo': True, # SWO hardware signal is connected and we know the USB bridge protocol
        'openocd_interface_cfg': 'interface/stlink-v2-1.cfg', # for informative purposes only
        'openocd': {'interface': 'hla', 'hla_layout': 'stlink' },
    }, {
        'name': 'ST-Link/V2',
        'usb_vid': 0x0483, 'usb_pid': 0x3748, # ID 0483:3748 STMicroelectronics ST-LINK/V2
        # standalone debug probe (supports JTAG and SWD), or
        # debug probe built into STM32 Discovery boards (SWD only), or
        # debug probe built into STM32 Discovery boards used as a stand alone probe (SWD only)
        'supports_jtag': True,
        'default_target_supports_swo': True, # SWO hardware signal is connected and we know the USB bridge protocol
        'openocd_interface_cfg': 'interface/stlink-v2.cfg', # for informative purposes only
        'openocd': {'interface': 'hla', 'hla_layout': 'stlink' },
    }, {
        'name': 'CMSIS-DAP',
        'usb_product_regex': '.*CMSIS-DAP.*',
        # debug probe built into mbed boards
        'default_target_supports_swo': False, # False for most LPC and Kinetis MBED boards, True for ST Nucleo boards.
        # A lot of MBED boards are Cortex-M{0,0+} and SWO is only supported on Cortex-M3 or newer.
        'supports_jtag': False, # not strictly true but CMSIS-DAP almost always used with SWD only
        # OpenOCD Known vid/pid pairs:
        # VID 0xc251: Keil Software
            # PID 0xf001: LPC-Link-II CMSIS_DAP
            # PID 0xf002: OPEN-SDA CMSIS_DAP (Freedom Board)
            # PID 0x2722: Keil ULINK2 CMSIS-DAP
        # VID 0x0d28: mbed Software
            # PID 0x0204: MBED CMSIS-DAP
        'openocd_interface_cfg': 'interface/cmsis-dap.cfg', # for informative purposes only
        # INFO: there's a 'cmsis_dap_vid_pid ' command
        'openocd': {'interface': 'cmsis-dap' },
    }, {
        'name': 'LPC-Link 2',
        # TODO: detect default firmware or DFU mode, prompt user to flash with CMSIS-DAP version
        # Note that LabTool also has the LPC-Link 2 in DFU mode by default
    }, {
        'name': 'TI ICDI', # see: OpenOCD ti_icdi_usb.c
        # http://e2e.ti.com/support/microcontrollers/tiva_arm/f/908/t/216275.aspx
        # Dexter: "The LM3S3601 on the EK-LM4F232 uses a form of GDB remote serial protocol over a USB Bulk transport layer."
        # "The same solution is also found on the new Stellaris LaunchPad." 
        # JTAG only, can be used as standalone adapter
        'supports_jtag': True, 'supports_swd': False,
        'openocd_interface_cfg': 'interface/ti-icdi.cfg',
        'openocd': {'interface': 'hla', 'hla_layout': 'ti-icdi' },
    }, {
        # OpenOCD contains no jlink SWD board files as of Sep 2014
        # TODO: Verify that OpenOCD-jlink-SWD
        # OpenOCD-jlink-jtag: http://gnuarmeclipse.livius.net/wiki/How_to_use_the_J-Link_probe_with_OpenOCD
        # OpenOCD-jlink-SWD attemps: https://www.mail-archive.com/openocd-development@lists.berlios.de/msg18111.html
        'name': 'J-Link', # see: OpenOCD jlink_usb.c
        'openocd_interface_cfg': 'interface/jlink.cfg', # for informative purposes only
        'openocd': { 'interface', 'jlink' },
        'supports_jtag': True,
    },
]

class DebugAdapter(dict):
    def __repr__(self):
        name = self['name']
        usb_vid = self.get('usb_vid')
        if usb_vid is not None:
            usb_pid = self.get('usb_pid')
            return 'DebugAdapter("%(name)s", usb_vid=%(usb_vid)04x, usb_pid=%(usb_pid)04x)' % locals()
        usb_product_regex = self.get('usb_product_regex')
        if usb_product_regex:
            return 'DebugAdapter("%(name)s", usb_product_regex="%(usb_product_regex)s")' % locals()
        return 'DebugAdapter("%(name)s")' % locals()

DEBUG_ADAPTERS = [ DebugAdapter(x) for x in _DEBUG_ADAPTERS_DATA ]
