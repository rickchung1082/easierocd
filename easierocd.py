#!/usr/bin/env python3

import re
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
from easierocd.usb import UnsupportedAdapter
import easierocd.openocd
from easierocd.openocd import (OpenOcdError, TargetCommunicationError, TargetDapError)
import easierocd.arm
from easierocd.util import (Bag, HexDict, waitpid_ignore_echild, kill_ignore_echild)
from easierocd.openocdcortexm import (OpenOcdCortexMDetect,
                           OpenOcdCortexMDetectError,
                           AdapterDoesntSupportTransport,
                           OpenOcdDoesntSupportTransportForAdapter)

class EasierOcdError(Exception):
    pass

main_function_map = {}

def main_function(func):
    global main_function_map
    main_function_map[func.__name__.replace('_','-')] = func
    return func

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

def tmux_sessions_cleanup(connected_adapters):
    p = subprocess.Popen(['tmux', 'list-sessions'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    response = p.stdout.read()
    if not response:
        return

    connected_usb_bus_addr = { (a_dev.bus, a_dev.address) for (a_info, a_dev) in connected_adapters }

    # b'openocd-ST-LinkV2-1-usb-2-109: 1 windows (created Thu Oct  9 15:37:00 2014) [140x41] (attached)\n'
    l = response.split(b'\n')
    for i in l:
        try:
            session_name = i.split()[0][:-1].decode('ascii') # strip ':' at end
        except IndexError:
            continue

        m = re.search(r'-usb-(?P<bus>[\d]*)-(?P<addr>[\d]*)', session_name)
        if m:
            d = m.groupdict()
            session_bus_addr = (int(d['bus']), int(d['addr']))
            if session_bus_addr not in connected_usb_bus_addr:
                r = subprocess.call(['tmux', 'kill-session', '-t', session_name])
                if r != 0:
                    logging.warning('tmux kill-session -t %s failed' % (session_name,))
                continue

# OpenOCD control: one process per debug adapter

def openocd_start(adapter):
    '-> (pid, tcl_port)'
    (info, device) = adapter
    logging.debug('openocd_start: USB 0x%04x:0x%04x' % (device.idVendor, device.idProduct))
    sname = tmux_session_name_for_adapter(adapter)

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

    (gdb_port, telnet_port, tcl_port) = (3333, 4444, 6666)
    while 1:
        openocd_cmd = ['openocd', 
                       # '-l', '/tmp/easierocd-openocd.log',
                       '-c', 'tcl_port %d' % (tcl_port,),
                       '-c', 'gdb_port %d' % (gdb_port,),
                       '-c', 'telnet_port %d' % (telnet_port,),
                       '-c', 'noinit']
        # openocd_stderr = tempfile.TemporaryFile(mode='w+')
        openocd_process = subprocess.Popen(openocd_cmd,
                                           stdin=tmux_pty_fd, stdout=tmux_pty_fd, stderr=tmux_pty_fd,
                                          start_new_session=True)
        time.sleep(0.001)
        r = openocd_process.poll()
        if r is None:
            break
        # TODO: make OpenOCD support local sockets and Windows Named Pipes
        tcl_port = random.randrange(1025, 65535)
        (gdb_port, telnet_port) = (tcl_port + 1, tcl_port + 2)

    logging.debug('openocd_start: pid: %d, tcl_port: %d' % (openocd_process.pid, tcl_port))
    return (openocd_process.pid, tcl_port)

def _start_openocd_rpc_write_pid(fd, adapter):
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
    if o is None:
        raise conn_refused
    return o

(OPENOCD_ALREADY_STARTED,
 OPENOCD_NEWLY_STARTED) = range(2)

def openocd_rpc_for_adapter(adapter):
    '-> (openodc_rpc, openocd_already_started_or_not)'

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
            # TODO: wrap os.unlink failtures (e.g. EPERM) in custom exception
            os.unlink(pid_fname)
            fd = os.open(pid_fname, os.O_EXCL|os.O_CREAT|os.O_RDWR)
            return (_start_openocd_rpc_write_pid(fd, adapter), OPENOCD_NEWLY_STARTED)
        else:
            (pid, tcl_port) = (ctrl_data['openocd_pid'], ctrl_data['tcl_port'])
            try:
                orpc = easierocd.openocd.OpenOcdRpc(port=tcl_port, pid=pid)
            except (ConnectionRefusedError, ConnectionResetError):
                # FIXME: check if process with 'pid' is openocd, if true, kill
                os.unlink(pid_fname)
                fd = os.open(pid_fname, os.O_EXCL|os.O_CREAT|os.O_RDWR)
                return (_start_openocd_rpc_write_pid(fd, adapter), OPENOCD_NEWLY_STARTED)
            else:
                return (orpc, OPENOCD_ALREADY_STARTED)

    (info, device) = adapter
    # TODO: patch OpenOCD to use local sockets and
    # Windows named pipes. Use localhost TCP for now
    pid_fname = pid_file_path(adapter)
    try:
        fd = os.open(pid_fname, os.O_EXCL|os.O_CREAT|os.O_RDWR)
    except FileExistsError:
        return _pid_file_exists()
    else:
        return (_start_openocd_rpc_write_pid(fd, adapter), OPENOCD_NEWLY_STARTED)

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

def openocd_setup(options):
    '-> (adapter, dap_info, mcu_info, openocd_rpc)'

    if options.adapter_usb_id is not None:
        try:
            adapter = easierocd.usb.adapter_by_usb_id(options.adapter_usb_id)
        except UnsupportedAdapter:
            sys.stderr.write('%s: specified adapter is not supported\n' % (program_name(),))
            sys.exit(3)
    else:
        adapters = easierocd.usb.connected_debug_adapters()
        if not adapters:
            sys.stderr.write('%s: no supported debug adapters found\n' % (program_name(),))
            sys.exit(3)

        if len(adapters) == 1:
            adapter = adapters[0]
        else:
            adapter = interactive_choose_adapter(adapters)

    tmux_sessions_cleanup(adapters)
    (o, openocd_newly_started_or_not) = openocd_rpc_for_adapter(adapter)
    logging.debug('openocd_newly_started_or_not: %d' % (openocd_newly_started_or_not,))
    openocd_initialized = o.initialized()
    target_names = o.target_names()

    # Mostly for USB cable or SWD/JTAG wire unplugs
    try:
        poll_info = o.poll()
    except TargetCommunicationError:
        poll_info = None
    mdetect = OpenOcdCortexMDetect(options, adapter, o)
    try:
        dap_info = mdetect.detect_dap()
    except OpenOcdCortexMDetectError:
        logging.debug('detect_dap: OpenOcdCortexMDetectError')
        dap_info = None

    if poll_info is None or dap_info is None:
        o.shutdown()
        waitpid_ignore_echild(o.pid)
        (o, openocd_newly_started_or_not) = openocd_rpc_for_adapter(adapter)

    logging.debug('target_name: %r, poll_info: %r, dap_info: %r' % (target_names, poll_info, dap_info))
    if (openocd_initialized and len(target_names) >= 1  and target_names[0] != 'EASIEROCD_DETECT.cpu' and
        poll_info is not None and dap_info is not None):
        # reuse existing OpenOCD daemon
        mcu_info = mdetect.detect_mcu(dap_info)
    else:
        logging.debug('Attempting OpenOCD Cotex-M probe')
        if openocd_newly_started_or_not == OPENOCD_ALREADY_STARTED:
            o.shutdown()
            waitpid_ignore_echild(o.pid)
            (o, openocd_newly_started_or_not) = openocd_rpc_for_adapter(adapter)
        
        # hard coding assumption that ARM Cortex-M is debug target
        mdetect = OpenOcdCortexMDetect(options, adapter, o)

        # Try SWD first (read IDCODE), if that fails falllback to JTAG
        # Use adapter_info and querying the adapters (e.g. cmsis-dap INFO_ID_CAPS command)
        # to know whether the adapter supports SWD/JTAG
        openocd_transport = 'swd'
        try:
            mdetect.openocd_init_for_detection(openocd_transport)
        except (AdapterDoesntSupportTransport, OpenOcdDoesntSupportTransportForAdapter) as e:
            try_jtag = True
        except ConnectionError:
            # protocol or connection error
            assert(o.pid is not None)
            kill_ignore_echild(o.pid, signal.SIGTERM)
            subprocess.call(['tmux', 'kill-session', '-t', tmux_session_name_for_adapter(adapter)])
            time.sleep(0.01)
            (o, openocd_newly_started_or_not) = openocd_rpc_for_adapter(adapter)
            mdetect = OpenOcdCortexMDetect(options, adapter, o)
            mdetect.openocd_init_for_detection(openocd_transport)

        # OpenOCD limits 'flash bank' to config stage
        # So declare_flash_bank is called afer openocd_init_for_detection before openocd_init_for_cortex_m
        dap_info = None
        try:
            dap_info = mdetect.detect_dap()
        except OpenOcdCortexMDetectError as e:
            #FIXME: if the target voltage is too low, we should give up here
            try_jtag = True
        else:
            try_jtag = False

        if try_jtag:
            openocd_transport = 'jtag'
            try:
                mdetect.openocd_init_for_detection(openocd_transport)
            except (AdapterDoesntSupportTransport, OpenOcdDoesntSupportTransportForAdapter):
                dap_info = None
            else:
                # protocol or connection error
                assert(o.pid is not None)
                kill_ignore_echild(o.pid, signal.SIGTERM)
                subprocess.call(['tmux', 'kill-session', '-t', tmux_session_name_for_adapter(adapter)])
                mdetect.openocd_init_for_detection(openocd_transport)
                try:
                    dap_info = mdetect.detect_dap()
                except OpenOcdCortexMDetectError:
                    dap_info = None

        if dap_info is None:
            sys.stderr.write('%s: failed to detect ARM Debug Access Port, aborting\n' % (program_name(),))
            sys.exit(3)

        logging.info('dap_info: %r' % (HexDict(dap_info),))

        # mcu_info: silicon vendor, MCU family, make, revision etc
        try:
            mcu_info = mdetect.detect_mcu(dap_info)
        except OpenOcdCortexMDetectError:
            o.shutdown()
            waitpid_ignore_echild(o.pid)
            raise

        logging.info('mcu_info: %r' % (HexDict(mcu_info),))

        # Don't attempt to 'init' OpenOCD twice, shutdown then re-launch instead
        o.shutdown()
        waitpid_ignore_echild(o.pid)

        (o, openocd_newly_started_or_not) = openocd_rpc_for_adapter(adapter)
        mdetect = OpenOcdCortexMDetect(options, adapter, o)
        mdetect.openocd_init_for_cortex_m(openocd_transport, dap_info, mcu_info)
        # OpenOCD gdbserver is up after 'init'

    return (adapter, dap_info, mcu_info, o)

@main_function
def easierocd_gdb(args):
    '# Start gdb session already connected to the debug adapter'
    logging.basicConfig(level=logging.DEBUG)

    def print_usage_exit():
        sys.stderr.write('easierocd-gdb [OPTIONS] GDB_ARUGMENTS...\n'
                         'OPTIONS:\n'
                         '\t--easierocd-gdb-file ELF\n'
                         '\t--easierocd-adapter USB_BUS:USB_ADDR\n'
                         'option names are prefixed to avoid clashes with GDB\n'
                         'Environemnt Variables\n'
                         '\tGDB: use "$GDB" as the gdb executable\n'
                         '\tHOST: use "$HOST-gdb" as the GDB executable\n'
                         )
        sys.exit(2)

    options = Bag()
    options.gdb_file = None
    options.adapter_usb_id = None

    (i, gdb_args) = (0, [])
    while i < len(args):
        a = args[i]
        if a in set(['-h', '--help']):
            print_usage_exit()
        elif a == '--easierocd-gdb-file':
            try:
                options.gdb_file = args[i+1]
            except IndexError:
                sys.stderr.write('%s: --easierocd-gdb-file requires an argument\n' % (program_name(),))
                sys.exit(2)
            i += 1
        elif a == '--easierocd-adapter':
            try:
                options.adapter_usb_id = args[i+1]
            except IndexError:
                sys.stderr.write('%s: --easierocd-adapter requires an argument\n' % (program_name(),))
                sys.exit(2)
            i += 1
        else:
            gdb_args.append(a)
        i += 1
            
    o = None
    try:
        (adapter, dap_info, mcu_info, o) = openocd_setup(options)
    except OpenOcdCortexMDetectError:
        pass
    if o is None:
        # ST DBGMCU_IDCODE reads often fail right after plugging the board in
        # where openocd's "poll" also failed
        (adapter, dap_info, mcu_info, o) = openocd_setup(options)

    o.set_arm_semihosting(True)

    # TODO: Free up TCL port? Think about concurrent debug & program
    # o.disconnect()

    gdb_name = os.environ.get('GDB')
    if gdb_name is None:
        t = os.environ.get('HOST')
        if t is not None:
            # e.g. 'arm-none-eabi' + '-gdb'
            gdb_name = '%s-gdb' % (t,)

    if gdb_name is None:
        logging.warning('Can your "gdb" command really debug ARM Cortex-M targets? Export GDB or HOST environment variables if this fails')
        gdb_name = 'gdb'
    
    if options.gdb_file is not None:
        # gdb -ex 'file ELF'
        # $(GDB) -q -x preferences.gdb -x openocd.gdb -ex "file $(PROJ_NAME).elf"
        gdb_args = ['-ex', 'file %s' % (options.gdb_file,)] + gdb_args

    gdb_args = ['-q',
                '-ex', 'set pagination 0',
                '-ex', 'set confirm 0',
                # OpenOCD doesn't support gdb nonstop mode yet
                # set non-stop 1
                # set target-async 1
                '-ex', 'target extended-remote :%d' % (o.gdb_port(),),
                # TODO: implement gdb non-stop mode in OpenOCD
                '-ex', 'monitor halt',
               ] + gdb_args

    try:
        gdb_process = subprocess.Popen([gdb_name] + gdb_args)
    except FileNotFoundError as e:
        print('%s: "%s" not found' % (program_name(), gdb_name), file=sys.stderr)
        sys.exit(1)

    # GDB uses SIGINT to interrupt its blocking commands.
    # see http://www.cons.org/cracauer/sigint.html
    sigint_received = False
    while True:
        try:
            r = gdb_process.wait()
        except KeyboardInterrupt:
            sigint_received = True
        else:
            if sigint_received:
                if os.WIFSIGNALED(r):
                    if os.WTERMSIG(r) == signal.SIGINT:
                        # SIGINT self
                        os.kill(os.getpid(), SIGINT)
            break

    if os.WIFEXITED(r):
        sys.exit(r)
    else:
        sys.exit(3)

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
