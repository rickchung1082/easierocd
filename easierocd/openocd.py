from __future__ import absolute_import

import re
import ctypes
import logging
import socket
import tempfile
import sys

class OpenOcdError(Exception):
    # FIXME: when the debug adapter is disconnecte
    # OpenOCD often responds with '' to commands
    # add logic to differentiate this
    def __init__(self, cmd, response):
        (self.cmd, self.response) = (cmd, response)
        super(OpenOcdError, self).__init__()
    
    def __str__(self):
        return 'OpenOcdError(cmd=%r, response=%r)' % (
            self.cmd, self.response)

    __repr__ = __str__

class TargetDapError(OpenOcdError):
    pass

class TargetCommunicationError(OpenOcdError):
    pass

class TargetMemoryAccessError(OpenOcdError):
    pass

class OpenOcdValueError(ValueError, OpenOcdError):
    def __init__(self, *args):
        super(ValueError, self).__init__(*args)

    def __str__(self):
        return '%s' % (self.args,)

    __repr__ = __str__

class OpenOcdRpc(object):
    SEPARATOR = b'\x1a'
    BUFSIZE = 4096

    def __init__(self, host='127.0.0.1', port=6666, pid=None):
        logging.debug('OpenOcdRrc connect: host: %s, port: %d' % (host, port))
        (self.host, self.port) = (host, port)
        self.msg_iter = None
        self.pid = pid
        self.ocd_transport = None # 'jtag', 'swd', 'hla_swd' etc
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((host, port))

    def send_msg(self, cmd):
        if isinstance(cmd, str):
            cmd = cmd.encode('ascii')
        logging.debug('OpenOcdRpc <- ' + repr(cmd))
        self.conn.sendall(cmd + self.SEPARATOR)

    def _gen_msg(self):
        out = []
        while 1:
            t = self.conn.recv(self.BUFSIZE)
            if t == b'':
                return
            while 1:
                try:
                    i = t.index(self.SEPARATOR)
                except ValueError:
                    out.append(t)
                    break
                else:
                    out.append(t[:i])
                    logging.debug('OpenOcdRpc -> ' + repr(b''.join(out)))
                    yield b''.join(out)
                    (out, t) = ([], t[i+1:])
                    if not t:
                        break

    def recv_msg(self):
        if self.msg_iter is None:
            self.msg_iter = self._gen_msg()
        try:
            d = next(self.msg_iter)
        except StopIteration:
            raise ConnectionError
        else:
            return d

    def command(self, cmd):
        'commands expected to return an empty string'
        # logging.debug('orpc.command: %r' % (cmd,))
        self.send_msg(cmd)
        r = self.recv_msg()
        if r != b'':
            raise OpenOcdError(cmd=cmd, response=r)

    def call(self, cmd):
        self.send_msg(cmd)
        return self.recv_msg()

    def idcode(self):
        if self.ocd_transport is None:
            self.ocd_transport = self.get_transport()
        if self.ocd_transport.startswith('hla_'):
            cmd = 'capture hla_idcode'
        else:
            cmd = 'capture dap_idcode'

        r = self.call(cmd)
        try:
            idcode = int(r, base=16)
        except ValueError:
            raise TargetDapError(cmd, r)
        return idcode

    def read_word(self, addr):
        r = self.call('ocd_mdw 0x%x' % (addr,))
        # response: b'0xe0042000: 10036419 \n'
        # response: b''
        try:
            return int(r.split(b': ')[1], base=16)
        except IndexError:
            raise TargetMemoryAccessError(cmd='ocd_mdw', response=r)

    def read_mem_into(self, addr, bytearray_out):
        with tempfile.NamedTemporaryFile(mode='rb') as tf:
            r = self.call('ocd_dump_image %(tfile)s 0x%(addr)x %(n)d' % dict(tfile=tf.name, addr=addr, n=len(bytearray_out)))
            # response: address option value ('0x100000000') is not valid
            if ('address option value ' in r) and (' is not valid' in r):
                raise OpenOcdValueError(r)
            # response: 'dumped 4 bytes in 0.000724s (5.395 KiB/s)\n'
            if not r.startswith('dumped '):
                raise OpenOcdError(cmd='ocd_dump_image', response=r)

            tf.readinto(bytearray_out)

    def read_mem(self, addr, byte_count):
        '''
        # Exapmle: unpack one int32 in native byte order

        # ba = read_mem()
        import ctypes
        int_array_1 = (ctypes.c_int32*1)
        a = int_array_1.from_buffer(ba)

        # int32 in native byte order
        print(a[0])

        # Change 'a' and 'ba' changes as well
        a[0] = 0x01020304
        print(repr(ba))
        # This implies that the caller needs to pass in and
        # hold on to the bytearray
        '''
        b = bytearray(byte_count)
        self.read_mem_into(addr, b)
        return b

    def write_mem(self, addr, bytearray_in):
        with tempfile.NamedTemporaryFile(mode='wb+') as tf:
            tf.write(bytearray_in)
            r = self.call('ocd_load_image %(tfile)s 0x%(addr)x bin' % dict(tfile=tf.name, addr=addr))
            # response: address option value ('0x100000000') is not valid
            if ('addr option value ' in r) and (' is not valid' in r):
                raise OpenOcdValueError(r)

            # response: '196608 bytes written at address 0x20000000\n'
            # 'downloaded 196608 bytes in 4.008617s (47.897 KiB/s)\n'
            if ('downloaded ' not in r) or (' bytes in ' not in r):
                raise OpenOcdError(cmd='ocd_load_image', response=r)

    def shutdown(self):
        try:
            r = self.call('ocd_shutdown')
        except ConnectionResetError:
            return

        if r.strip() != b'shutdown command invoked':
            raise OpenOcdError(cmd='ocd_shutdown', response=r)

    def declare_flash_bank(self):
        assert(0)
        self.call('ocd_flash_bank')

    def tcl_port(self):
        # same info should be available in 'self.port' but you never know
        r = self.call('ocd_tcl_port')
        return int(r)

    def gdb_port(self):
        r = self.call('ocd_gdb_port')
        return int(r)

    def telnet_port(self):
        r = self.call('ocd_telnet_port')
        return int(r)

    def get_transport(self):
        '-> "hla_swd", "swd", "jtag" etc'
        r = self.call('ocd_transport select')
        return r.decode('ascii')

    def initialized(self):
        '-> bool'
        r = self.call('initialized')
        return bool(int(r))

    def target_names(self):
        ' -> [ NAME...]'
        r = self.call('ocd_target names')
        return [ x.decode('ascii') for x in r.split() if x ]

    def poll(self):
        'poll target CPU'

        # Success
        # <- b'ocd_poll'
        # -> b'background polling: on\nTAP: stm32l1.cpu (enabled)\ntarget state: halted\ntarget halted due to breakpoint, current mode: Thread \nxPSR: 0x81000000 pc: 0x08000ede msp: 0x20014000\n'
        # Failture
        # <- b'ocd_poll'
        # -> b'background polling: on\nTAP: stm32l1.cpu (enabled)\nPrevious state query failed, trying to reconnect\njtag status contains invalid mode value - communication failure\n'

        r = self.call('ocd_poll')
        r_str = r.decode('ascii')
        #import IPython; IPython.embed()
        if re.search(r'[\s]communication failure[\s]', r_str):
            #assert(0)
            logging.debug('ocd_poll: communication error')
            raise TargetCommunicationError('ocd_poll', r)
        
        # s = b'target halted due to breakpoint, current mode: Thread '
        out = {}

        current_mode_re = r'[\s]current mode: ([\w]*)'
        m = re.search(current_mode_re, r_str, re.DOTALL)
        if m:
            out['current_mode'] = m.groups()[0].lower()

        pc_regs_re = r'.*[\s]xPSR: 0x(?P<xPSR>[\w]*) pc: 0x(?P<pc>[\w]*) msp: 0x(?P<msp>[\w]*)'
        m = re.search(pc_regs_re, r_str, re.DOTALL)
        if m:
            out.update(m.groupdict())
        return out

    def set_arm_semihosting(self, enable):
        if enable:
            enable_str = 'enable'
        else:
            enable_str = 'disable'
        r = self.call('arm semihosting %s' % (enable_str,))

    def f():
            import IPython; IPython.embed()
            

def test():
    logging.basicConfig(level=logging.DEBUG)
    o = OpenOcdRpc(port=6666)

    if 1:
        o.poll()

    if 0:
        o.target_names()

    if 0:
        print(o.get_transport())
        print(o.tcl_port(), o.gdb_port(), o.telnet_port())
        print('0x%x' % (o.idcode(),))

    if 0:
        STM32_DBGMCU_IDCODE = 0xe0042000

        b = bytearray(1*4)
        try:
            o.read_mem_into(0x100000000, b)
        except ValueError:
            pass
        else:
            assert(0)

        o.read_mem_into(STM32_DBGMCU_IDCODE, b)
        stm32_idcode = (ctypes.c_int32*1).from_buffer(b)[0]
        print('sTM32 idcode: 0x%x' % (stm32_idcode,))

        b = o.read_mem(STM32_DBGMCU_IDCODE, 4)
        stm32_idcode1 = (ctypes.c_int32*1).from_buffer(b)[0]
        assert(stm32_idcode == stm32_idcode1)

        try:
            o.write_mem(0x100000000, bytearray([0x55]))
        except ValueError:
            pass
        else:
            assert(0)
        
        # STM32F429, RAM: origin: 0x2000_0000, length: 192K
        pattern = [0x55, 0xaa]
        b = bytearray(pattern * (192 * 1024 // len(pattern)))
        o.write_mem(0x2000*0x10000, b)

if __name__ == '__main__':
    test()
