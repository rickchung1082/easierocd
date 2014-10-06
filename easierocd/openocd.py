from __future__ import absolute_import

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
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((host, port))
        self.msg_iter = None
        self.pid = pid

    def send_msg(self, cmd):
        s = cmd.encode('ascii') + self.SEPARATOR
        logging.debug('OpenOcdRpc <- ' + repr(s))
        self.conn.sendall(s)

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
        r = self.calll('ocd_idcode')
        return None

    def read_word(self, addr):
        r = self.call('ocd_mdw 0x%x' % (addr,))
        # response: '0xe0042000: 10036419 \n'
        try:
            return int(r.split(': ')[1], base=16)
        except IndexError:
            raise OpenOcdError(cmd='ocd_mdw', response=r)

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

    def f():
            import IPython; IPython.embed()
            

def test():
    logging.basicConfig(level=logging.DEBUG)
    s = OpenOcdRpc()
    STM32_DBGMCU_IDCODE = 0xe0042000

    b = bytearray(1*4)
    try:
        s.read_mem_into(0x100000000, b)
    except ValueError:
        pass
    else:
        assert(0)

    s.read_mem_into(STM32_DBGMCU_IDCODE, b)
    idcode = (ctypes.c_int32*1).from_buffer(b)[0]
    print('idcode: 0x%x' % (idcode,))

    b = s.read_mem(STM32_DBGMCU_IDCODE, 4)
    idcode1 = (ctypes.c_int32*1).from_buffer(b)[0]
    assert(idcode == idcode1)

    try:
        s.write_mem(0x100000000, bytearray([0x55]))
    except ValueError:
        pass
    else:
        assert(0)
    
    # STM32F429, RAM: origin: 0x2000_0000, length: 192K
    pattern = [0x55, 0xaa]
    b = bytearray(pattern * (192 * 1024 // len(pattern)))
    s.write_mem(0x2000*0x10000, b)

if __name__ == '__main__':
    test()
