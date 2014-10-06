#!/usr/bin/env python3

import sys
import os
import errno
import doctest
import tempfile
import json
import subprocess
import time
import random
import signal
import logging

import easierocd.usb
import easierocd.openocd
import easierocd.arm
from easierocd.arm import (ArmCpuDetection, ArmCpuDetectionError,
                           AdapterDoesntSupportTransport, OpenOcdDoesntSupportTransportForAdapter)

class EasierOcdError(Exception):
    pass

main_function_map = {}

def main_function(func):
    global main_function_map
    main_function_map[func.__name__.replace('_','-')] = func
    return func

# OpenOCD control: one process per debug adapter

def path_safe_str(s):
    '''
    >>> path_safe_str('ST-Link/V2-1')
    'ST-LinkV2-1'
    >>> path_safe_str('TI ICDI')
    'TIICDI'
    >>> path_safe_str('LPC-Link 2')
    'LPC-Link2'
    '''
    safe_chrs = set('-_.'
                    'abcdefghijklmnopqrstuvwxyz'
                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                    '0123456789')
    out = []
    for c in s:
        if c in safe_chrs:
            out.append(c)
        else:
            pass
    return ''.join(out)

def pid_file_path(adapter):
    (info, device) = adapter
    adapter_name = path_safe_str(info['name'])
    tdir = tempfile.gettempdir()
    return os.path.join(tdir, 'easierocd-%s-usb-%d-%d' % (
        adapter_name, device.bus, device.address))

def tmux_session_name_for_adapter(adapter):
    (info, device) = adapter
    return 'openocd-%s-usb-%d-%d' % (path_safe_str(info['name']), device.bus, device.address)

def tmux_pane_get_pty(tmux_target):
    # $ tmux lsp -F '#{pane_tty}'
    # /dev/pts/6
    p = subprocess.Popen(['tmux', 'list-pane', '-t', tmux_target, '-F', '#{pane_tty}'], stdout=subprocess.PIPE)
    out = []
    while 1:
        t = p.stdout.read().decode('ascii')
        if t == '':
            break
        out.append(t)
    # strip '\n' at end
    return (''.join(out))[:-1]

def openocd_start(adapter):
    '-> (pid, tcl_port)'
    (info, device) = adapter
    sname = tmux_session_name_for_adapter(adapter)
    tcl_port = 6666

    tmux_stderr = tempfile.TemporaryFile(mode='w+')
    # The pause helper is just a program for tmux to wait on that doesn't touch STDIN/STDOUT/STDERR
    # what I really want is for tmux to have a 'reptyr -l' like "just wait on the pty" mode
    # bin/easiocd -> libexec/pause
    pause_helper_exe = os.path.join(os.path.split(os.path.split(sys.argv[0])[0])[0], 'libexec', 'pause')
    r = subprocess.call(['tmux', 'new-session', '-d', '-s', sname, pause_helper_exe], stderr=tmux_stderr)
    tmux_stderr.seek(0)
    m = tmux_stderr.read()

    if r != 0 and r != 1:
        raise EasierOcdError('tmux: "%s"\n' % (m,))
    if r == 1:
        # 'duplicate session: T'
        if m.startswith('duplicate session: '):
            # since we don't shutdown tmux explicitly, just assume this tmux session is usable
            pass
        else:
            raise EasierOcdError('tmux: "%s"\n' % (m,))

    tmux_pty_fd = os.open(tmux_pane_get_pty(sname), os.O_RDWR)

    while 1:
        openocd_cmd = ['openocd', '-c', 'tcl_port %d' % (tcl_port,), '-c', 'noinit']
        openocd_stderr = tempfile.TemporaryFile(mode='w+')
        openocd_process = subprocess.Popen(openocd_cmd, stderr=openocd_stderr, stdin=tmux_pty_fd, stdout=tmux_pty_fd)
        time.sleep(0.001)
        r = openocd_process.poll()
        if r is None:
            break
        tcl_port = random.randrange(1025, 65535)
    return (openocd_process.pid, tcl_port)

def _get_openocd_rpc_write_pid(fd, adapter):
    (pid, tcl_port) = openocd_start(adapter)
    ctrl_data = dict(openocd_pid=pid, tcl_port=tcl_port)
    os.write(fd, json.dumps(ctrl_data).encode('ascii'))
    os.write(fd, b'\n')
    os.close(fd)

    # OpenOcdRpc isn't immediately ready to accept connections on the tcl_port
    n_tries = 3
    conn_refused = None
    o = None
    for i in range(n_tries):
        try:
            o = easierocd.openocd.OpenOcdRpc(port=tcl_port, pid=pid)
        except ConnectionRefusedError as e:
            conn_refused = e
            time.sleep(0.01)
        else:
            break
    if i == n_tries:
        raise conn_refused
    assert(o)
    return o

def openocd_rpc_for_adapter(adapter):
    def _pid_file_exists():
        # check if daemon is running, if not, cleanup
        # TODO: wrap other os.open failtures (e.g. PERM) in custom exception
        # for better error messages intead of tracebacks
        fd = os.open(pid_fname, os.O_RDONLY)
        data = os.read(fd, 4096)
        os.close(fd)
        try:
            ctrl_data = json.loads(data.decode('ascii'))
        except ValueError:
            # TODO: wrap os.unlink failtures (e.g. PERM) in custom exception
            os.unlink(pid_fname)
            fd = os.open(pid_fname, os.O_EXCL|os.O_CREAT|os.O_RDWR)
            return _get_openocd_rpc_write_pid(fd, adapter)
        else:
            (pid, tcl_port) = (ctrl_data['openocd_pid'], ctrl_data['tcl_port'])
            try:
                orpc = easierocd.openocd.OpenOcdRpc(port=tcl_port, pid=pid)
            except ConnectionRefusedError:
                # FIXME: check if process with 'pid' is openocd, if true, kill
                os.unlink(pid_fname)
                fd = os.open(pid_fname, os.O_EXCL|os.O_CREAT|os.O_RDWR)
                return _get_openocd_rpc_write_pid(fd, adapter)
            else:
                return orpc

    (info, device) = adapter
    # TODO: patch OpenOCD to use local sockets and
    # Windows named pipes. Use localhost TCP for now
    pid_fname = pid_file_path(adapter)
    try:
        fd = os.open(pid_fname, os.O_EXCL|os.O_CREAT|os.O_RDWR)
    except FileExistsError:
        return _pid_file_exists()
    else:
        return _get_openocd_rpc_write_pid(fd, adapter)

def interactive_choose_adapter(adapters):
    # Check last choice in $HOME/.easierocd-last.ini
    # If it stil makes sense, use it, otherwise prompt
    assert(0)

@main_function
def easierocd_setup(args):
    '''
    # easierocd-setup 
    Interactively choose and save which 
    '''
    pass

@main_function
def easierocd_gdb(args):
    '# Start gdb session already connected to the debug adapter'
    logging.basicConfig(level=logging.DEBUG)

    def print_usage_exit():
        sys.stderr.write('easierocd-gdb [OPTIONS] GDB_OPTIONS...\n'
                         'OPTIONS:\n'
                         '\t--easierocd-gdb-file ELF\n'
                         '\t--adapter USB_BUS:USB_ADDR\n'
                         'Environemnt Variables\n'
                         '\tGDB: use "$GDB" as the gdb executable\n'
                         '\tHOST: use "$HOST-gdb" as the GDB executable\n'
                         )
        sys.exit(2)

    for a in args:
        if a in set(['-h', '--help']):
            print_usage_exit()

    adapters = easierocd.usb.connected_debug_adapters()
    if not adapters:
        sys.stderr.write('%s: no supported debug adapters found\n' % (program_name(),))
        sys.exit(3)

    if len(adapters) == 1:
        adapter = adapters[0]
    else:
        adapter = interactive_choose_adapters(adapters)

    o = openocd_rpc_for_adapter(adapter)
    # hard coding ARM CPU as debug target
    mdetect = ArmCpuDetection(adapter, o)

    # Try SWD first (read IDCODE), if that fails falllback to JTAG
    # Use adapter_info and querying the adapters (e.g. cmsis-dap INFO_ID_CAPS command)
    # to know whether the adapter supports SWD/JTAG
    try:
        mdetect.openocd_init_for_detection('swd')
    except (AdapterDoesntSupportTransport, OpenOcdDoesntSupportTransportForAdapter) as e:
        try_jtag = True
    except ConnectionError:
        # protocol or connection error
        assert(o.pid is not None)
        os.kill(o.pid, signal.SIGTERM)
        time.sleep(0.01)
        o = openocd_rpc_for_adapter(adapter)
        mdetect = ArmCpuDetection(adapter, o)
        mdetect.openocd_init_for_detection('swd')

    # TODO: OpenOCD limits 'flash bank' to init phase
    # this design kills autodetection
    try:
        cpu_variant = mdetect.detect_dap()
    except ArmCpuDetectionError as e:
        #FIXME:
        try_jtag = True
    else:
        try_jtag = False

    if try_jtag:
        try:
            mdetect.openocd_init_for_detection('jtag')
        except (AdapterDoesntSupportTransport, OpenOcdDoesntSupportTransportForAdapter) as e:
            sys.stderr.write("%s: can't reach debug access port through either SWD and JTAG. abortign\n" % (program_name(),))
            sys.exit(3)
        else:
            # protocol or connection error
            assert(o.pid is not None)
            os.kill(o.pid, signal.SIGTERM)
            mdetect.openocd_init_for_detection('jtag')

    mcu_info = mdetect.detect_mcu()
    # shutdown then relaunch OpenOCD
    o.shutdown()
    o = openocd_rpc_for_adapter(adapter)
    mdetect = ArmCpuDetection(adapter, o)
    # declaring flash regsions effectively determines the memory map
    # gdb's 'load', 'break' commands need to differentiate between flash and ram to work 
    mdetect.declare_flash_bank(mcu)
    mdetect.set_target_reset_method(adapter, cortex_m_variant)
    mdetect.openocd_init()
    # OpenOCD gdbserver is up after 'init'

    gdb_name = os.environ.get('GDB')
    if gdb_name is None:
        gdb_name = os.environ.get('HOST')
    if gdb_name is None:
        gdb_name = 'gdb'
    else:
        # e.g. 'arm-none-eabi' + '-gdb'
        gdb_name = '%s-gdb' % (gdb_name,)
    
    if options.gdb_file is not None:
        # gdb -ex 'file ELF'
        # $(GDB) -q -x preferences.gdb -x openocd.gdb -ex "file $(PROJ_NAME).elf"
        gdb_args = '-ex "file %s"' % (options.gdb_file,)
    try:
        r = subprocess.call([gdb_name] + gdb_args) 
    except NoSuchFileError as e:
        print('%s: "%s" not found' % (program_name(), gdb_name), file=sys.stderr)
        sys.exit(1)

@main_function
def easierocd_program(args):
    pass

@main_function
def easierocd_stop_all(args):
    help_msg = 'stop all background processes'

def main_function_dispatch(name, args):
    try:
        f = main_function_map[name]
    except KeyError:
        sys.stderr.write('%s is not a valid command name\n' % (name,))
        sys.exit(2)
    sys.exit(f(args))

def program_name():
    return os.path.basename(sys.argv[0])

if __name__ == '__main__':
    main_function_dispatch(program_name(), sys.argv[1:])
