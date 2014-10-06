from __future__ import absolute_import

# In addition to the standard Cortex-M debug hardware, ST has a DBG_MCU component with IDCODE and debug time clock control functionality
# PPB Bus

# MCU Device ID Code: MCU part number and revision.
# Available even while MCU is under reset
DBGMCU_IDCODE_ADDR = 0xe0042000

def dbgmcu_idcode_decode(v):
    # RM0090 for STM32F4
    # RM0038 for STM32L1, Chp 38 Debug, Section 38.6 ID codes and locking mechanism

    # "MCU device ID code"
    rev_id   = (v >> 16) & 0xffff
    reserved = (v >> 12) & 0x0f
    dev_id   = (v >> 0)  & 0xfff

    device_categories = {
        # RM0090 for STM32F4, p. 1667
        0x413: 'STM32F405xx/07xx and STM32F415xx/17xx',
        0x419: 'STM32F42xxx and STM32F43xxx',
        # RM0038 for STM32L1 
        0x416: 'STM32L1 Cat.1',
        0x429: 'STM32L1 Cat.2',
        0x427: 'STM32L1 Cat.3',
        0x436: 'STM32L1 Cat.4 or Cat.3', # Special Cat.3 devices: STM32L15xxC or STM3216xxC devices with RPN ending with letter 'A', in WLCSP64 packages or with more then 100 pin.
        0x437: 'STM32L1 Cat.5',
    }
    revisions = {}
    # STM32F4
    if dev_id == 0x413 or dev_id == 0x419:
        revisions = { 0x1000: 'Rev A', 0x1001: 'Rev Z', 0x1003: 'Rev Y', 0x1007: 'Rev 1', 0x2001: 'Rev 3' } 
    # STM32L1
    elif dev_id == 0x416:
        revisions = { 0x1000: 'Rev A', 0x1008: 'Rev Y', 0x1038: 'Rev W', 0x1078: 'Rev V' }
    elif dev_id == 0x429:
        revisions = { 0x1000: 'Rev A', 0x1018: 'Rev Z' }
    elif dev_id == 0x427:
        revisions = { 0x1018: 'Rev A', 0x1038: 'Rev X' }
    elif dev_id == 0x436:
        revisions = { 0x1000: 'Rev A', 0x1008: 'Rev Z', 0x1018: 'Rev Y' }
    elif dev_id == 0x437:
        revisions = { 0x1000: 'Rev A' }

    dev = device_categories.get(dev_id)
    rev = revisions.get(rev_id)
    return dict(dev_id=dev_id, rev_id=rev_id, dev=dev, rev=rev)

def test():
    stm32l152re = 0x10006437 # ST Nucleo L152RE board
    stm32f429zit6 = 0x10036419 # STM32F429I DISCOVERY board
    l = locals()

    experiment = True
    if experiment:
        from easierocd.util import HexDict
        import pprint
        for (n, v) in l.items():
            stm32_id = dbgmcu_idcode_decode(v)
            pprint.pprint((n, HexDict(stm32_id)))

    d = dbgmcu_idcode_decode(stm32l152re)
    assert(d == {'dev': 'STM32L1 Cat.5',
                'dev_id': 0x437, 'rev': 'Rev A', 'rev_id': 0x1000})

    d = dbgmcu_idcode_decode(stm32f429zit6)
    assert(d == {'dev_id': 0x419, 'rev': 'Rev Y', 'dev': 'STM32F42xxx and STM32F43xxx', 'rev_id': 0x1003})

if __name__ == '__main__':
    test()