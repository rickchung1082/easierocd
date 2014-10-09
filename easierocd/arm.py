from __future__ import absolute_import

import copy

# ARM Debug Interface, ADIv5.0 to ADIv5.2
# See https://silver.arm.com/download/ARM_and_AMBA_Architecture/AR551-DA-70001-r0p0-01rel0/IHI0031C_debug_interface_as.pdf

CORTEX_M_DAPS = {
    0x0bb11477: ('cortex-m0',  'r0p0'),
    0x0bc11477: ('cortex-m0p', 'r0p0-dp1'), # DP Architecture 1
    0x0bc12477: ('cortex-m0p', 'r0p0-dp2'), # DP Architecture 2
    # texan/stlink
    0x1ba00477: ('cortex-m3',  'r1p0'),
    0x4ba00477: ('cortex-m3',  'r2p0'),
    # NOTE: stm32l1 has as SW-DP idcode of 0x2ba01477,
    0x2ba01477: ('cortex-m4',  'r0p0'),
}

def dpidr_decode(v):
    # revision: implementation defined
    revision = (v >> 28) & 0x0f
    # partno: part number of debug port
    partno   = (v >> 20) & 0xff
    reserved0 = (v >> 17) & 0x07
    # mindp: (1: transaction counter, pushed-verify, pushed-find not implemented)
    mindp    = (v >> 16) & 0x01
    # version of DP Architecture implemented (1: DPv1, 2: DPv2)
    version  = (v >> 12) & 0x0f
    # JEDEC designer ID, ARM: 0x23b
    designer = (v >> 1) & 0x7ff
    # always reads as one
    rao      = (v >> 0) & 0x01
    out = copy.copy(locals())
    del out['v']

    if version == 0:
        # "Implementations of DPv0 do not implement DPIDR"
        return {'version': 0}
    try:
        t = CORTEX_M_DAPS[v]
    except KeyError:
        pass
    else:
        out['cortex'] = t[0]
        out['revision_name'] = t[1]
    return out

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
    stm32f0 = 0x0bb11477
    stm32f1 = 0x1ba01477
    stm32f2 = 0x2ba01477
    stm32f3 = 0x2ba01477
    stm32f4 = 0x2ba01477
    stm32vl = 0x1ba01477
    # ST bug, stm32l1's are Cortex-M3's
    stm32l  = 0x2ba01477
    l = copy.copy(locals())

    experiment = True

    if experiment:
        from easierocd.util import HexDict
        import pprint
        items = list(l.items())
        items.sort()
        for (n, v) in items:
            idr = dpidr_decode(v)
            print(n, hex(v), HexDict(idr))

if __name__ == '__main__':
    test()
