from __future__ import absolute_import

# DID1
# DID0

def did1_decode(v):
    '''
    > tm4c123gh6pm_did1 = 0x10A1606e
    > did1_decode(tm4c123gh6pm_did1)
    None
    '''
    # tm4c123gh6pm.pdf p.240
    # See also: OpenOCD: stellaris_read_part_info()

    # 0: register format 0, implies a Stellaris LM3Snn device
    # 0: register format 1
    ver = (v >> 28) & 0xf
    # 0: TM4C, LM4F, LM3S
    fam = (v >> 24) & 0xf
    # 
    partno = (v >> 16) & 0xff
    pincount = (v >> 13) & 0x7
    reserved = (v >> 8) & 0x1f
    temp = (v >> 5) & 0x7
    pkg = (v >> 3) & 0x3
    rohs = (v >> 2) & 0x1
    qual = (v >> 0) & 0x3
    return locals()
