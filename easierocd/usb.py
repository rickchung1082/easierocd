from __future__ import absolute_import

# Abstract USB access under different operating systems like
# "Dependencies" in https://github.com/mbedmicro/pyOCD
# Hard coding pyUSB (https://github.com/walac/pyusb) for now.

import logging
import errno
import re

import usb.core
import usb.util

from easierocd.debugadapters import DEBUG_ADAPTERS

class UnsupportedAdapter(Exception):
    pass

def adapter_by_usb_id(usb_id):
    assert(0)

def connected_debug_adapters():
    out = []
    for d in usb.core.find(find_all=True):
        logging.debug('device: USB(0x%04x, 0x%04x)' % (d.idVendor, d.idProduct))
        for rule in DEBUG_ADAPTERS:
            usb_vid = rule.get('usb_vid')
            if usb_vid:
                usb_pid = rule.get('usb_pid')
                if (d.idVendor == usb_vid and d.idProduct == usb_pid):
                    out.append((rule, d))
                    continue

            usb_product_regex = rule.get('usb_product_regex')
            if usb_product_regex:
                try:
                    product_str = usb.util.get_string(d, 256, d.iProduct)
                except usb.USBError as e:
                    if e.errno != errno.EACCES:
                        raise
                else:
                    m = re.match(usb_product_regex, product_str)
                    if not m:
                        continue
                    out.append((rule, d))
                    continue

    return out

def test():
    adapters = connected_debug_adapters()

if __name__ == '__main__':
    test()
