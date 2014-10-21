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
from easierocd.util import hex_str_literal_double_quoted

class EasierOcdUsbError(Exception):
    pass

class AdapterNotFound(EasierOcdUsbError):
    pass

class AdapterNotSupported(EasierOcdUsbError):
    pass

class MultipleAdaptersMatchCriteria(EasierOcdUsbError):
    pass

def multiple_adapter_msg(adapters):
    out = []
    for (info, d) in adapters:
        serial = getattr(d, 'serial_number', None)
        adapter_str = ('%(name)s: bus_addr: %(bus)03d:%(addr)03d vid_pid: %(vid)04x:%(pid)04x' %
                   dict(name=info['name'], bus=d.bus, addr=d.address, vid=d.idVendor, pid=d.idProduct))
        if serial is not None:
            adapter_str += ' serial: %(serial)s' % dict(serial=hex_str_literal_double_quoted(serial))
        out.append(adapter_str)
    return '\n'.join(out)

def adapter_by_usb_vid_pid(usb_vid_pid_tuple):
    '-> (adapter_info, adapter_usb_dev)'
    (vid, pid) = (usb_vid_pid_tuple)
    devs = usb.core.find(find_all=True, idVendor=vid, idProduct=pid)
    adapters = [ (adapter_info_find(x), x) for x in devs ]
    supported_adapters = [ x for x in adapters if (x[0] is not None) ]
    if not adapters:
        raise AdapterNotFound
    if not supported_adapters:
        raise AdapetrNotSupported
    if len(supported_adapters) != 1:
        raise MultipleAdaptersMatchCriteria(multiple_adapter_msg(adapters))
    return supported_adapters[0]

def adapter_by_usb_serial(serial):
    '-> (adapter_info, adapter_usb_dev)'
    # Reading USB serial numbers requires higher permissions on Linux and probably more platforms
    adapters = []
    for d in usb.core.find(find_all=True):
        try:
            dev_serial = d.serial_number
        except usb.USBError as e:
            if e.errno != errno.EACCES:
                raise
            continue
        if dev_serial != serial:
            continue
        adapters.append((adapter_info_find(d), d))
    supported_adapters = [ x for x in adapters if (x[0] is not None) ]
    if not adapters:
        raise AdapterNotFound
    if not supported_adapters:
        raise AdapetrNotSupported
    if len(supported_adapters) != 1:
        raise MultipleAdaptersMatchCriteria(multiple_adapter_msg(adapters))
    return supported_adapters[0]

def adapter_by_usb_bus_addr(usb_bus_addr_tuple):
    '-> (adapter_info, adapter_usb_dev)'
    (bus_num, addr_num) = usb_bus_addr_tuple
    devs = usb.core.find(find_all=True, bus=bus_num, address=addr_num)
    adapters = [ (adapter_info_find(x), x) for x in devs ]
    supported_adapters = [ x for x in adapters if (x[0] is not None) ]
    if not adapters:
        raise AdapterNotFound
    if not supported_adapters:
        raise AdapetrNotSupported
    assert(len(supported_adapters) == 1)
    return supported_adapters[0]

def adapter_info_find(usb_dev):
    '-> adapter_info or None'
    d = usb_dev
    for rule in DEBUG_ADAPTERS:
        usb_vid = rule.get('usb_vid')
        if usb_vid is not None:
            usb_pid = rule['usb_pid']
            if (d.idVendor == usb_vid and d.idProduct == usb_pid):
                return rule
        
        usb_product_regex = rule.get('usb_product_regex')
        if usb_product_regex is not None:
            try:
                product_str = d.product
            except usb.USBError as e:
                if e.errno != errno.EACCES:
                    raise
            else:
                m = re.search(usb_product_regex, product_str)
                if m is None:
                    continue
                return rule
    return None

def connected_debug_adapters():
    '-> [ (adapter_info, adapter_usb_device), ...]'
    out = []
    for d in usb.core.find(find_all=True):
        logging.debug('device: USB(0x%04x, 0x%04x)' % (d.idVendor, d.idProduct))
        adapter_info = adapter_info_find(d)
        if adapter_info is not None:
            out.append((adapter_info, d))
    return out

def test():
    adapters = connected_debug_adapters()

if __name__ == '__main__':
    test()
