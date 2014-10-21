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
import glob

import easierocd.usb
from easierocd.usb import (AdapterNotFound,
                           AdapterNotSupported,
                           MultipleAdaptersMatchCriteria,
                           multiple_adapter_msg)
import easierocd.openocd
from easierocd.openocd import (OpenOcdError,
                               TargetCommunicationError,
                               TargetDapError,
                               OpenOcdResetError)
import easierocd.arm
from easierocd.util import (Bag,
                            HexDict,
                            waitpid_ignore_echild,
                            kill_ignore_echild,
                            hex_str_literal_double_quoted)
from easierocd.openocdcortexm import (OpenOcdCortexMDetect,
                           OpenOcdCortexMDetectError,
                           OpenOcdOpenFailedDuringInit,
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

def pid_files_cleanup(connected_adapters):
    tdir = tempfile.gettempdir()
    pid_files = glob.glob(os.path.join(tdir, 'easierocd-*'))
    connected_adapter_pid_filenames = {
        os.path.basename(pid_file_path(x)) for x in connected_adapters }
    for i in pid_files:
        if os.path.basename(i) not in connected_adapter_pid_filenames:
            logging.debug('pid_files_cleanup: removing %r' % (i,))
            try:
                os.unlink(i)
            except (PermissionError):
                pass

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
    openocd_exe = os.environ.get('OPENOCD', 'openocd')
    while 1:
        openocd_cmd = [openocd_exe,
                       # '-l', '/tmp/easierocd-openocd.log',
                       '-c', 'tcl_port %d' % (tcl_port,),
                       '-c', 'gdb_port %d' % (gdb_port,),
                       '-c', 'telnet_port %d' % (telnet_port,),
                       '-c', 'noinit']
        # openocd_stderr = tempfile.TemporaryFile(mode='w+')
        openocd_process = subprocess.Popen(openocd_cmd,
                                           stdin=tmux_pty_fd, stdout=tmux_pty_fd, stderr=tmux_pty_fd,
                                          start_new_session=True)
        time.sleep(0.01)
        r = openocd_process.poll()
        if r is None:
            break
        # TODO: make OpenOCD support local sockets and Windows Named Pipes
        tcl_port = random.randrange(1025, 65535)
        (gdb_port, telnet_port) = (tcl_port + 1, tcl_port + 2)

    logging.debug('openocd_start: pid: %d, tcl_port: %d' % (openocd_process.pid, tcl_port))
    return (openocd_process.pid, tcl_port)

def _start_openocd_rpc_write_pid(fd, adapter):
    '-> openocd_rpc'

    while 1:
        (pid, tcl_port) = openocd_start(adapter)

        # OpenOcdRpc isn't immediately ready to accept connections on the tcl_port
        # make 'n_tries' large enough so that "gdb -x utils/debug-eocd-multi-process.gdb"
        # (eocd-gdb. openocd, multi process debugging) works
        n_tries = 30
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

        # The process that responds on tcl_port isn't necessarily the openocd process
        # we started
        if o.getpid() != pid:
            o.close()
            continue

        break

    ctrl_data = dict(openocd_pid=pid, tcl_port=tcl_port)
    os.write(fd, json.dumps(ctrl_data).encode('ascii'))
    os.write(fd, b'\n')
    os.close(fd)
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

            # The OpenOCD process we're connected to could in fact be started by someone else and 
            # driving a different debug adapter.
            try:
                openocd_pid = orpc.getpid()
            except OpenOcdError:
                openocd_pid = None

            if openocd_pid != pid:
                # tcl_port taken over by another OpenOCD process
                # which may not be driving the debug adapter we want
                orpc.close()
                os.unlink(pid_fname)
                fd = os.open(pid_fname, os.O_EXCL|os.O_CREAT|os.O_RDWR)
                return (_start_openocd_rpc_write_pid(fd, adapter), OPENOCD_NEWLY_STARTED)
            else:
                return (orpc, OPENOCD_ALREADY_STARTED)

    (info, device) = adapter
    # TODO: patch OpenOCD to use local sockets and Windows named pipes.
    # Use localhost TCP for now
    pid_fname = pid_file_path(adapter)
    try:
        fd = os.open(pid_fname, os.O_EXCL|os.O_CREAT|os.O_RDWR)
    except FileExistsError:
        return _pid_file_exists()
    else:
        return (_start_openocd_rpc_write_pid(fd, adapter), OPENOCD_NEWLY_STARTED)

def print_adapters_list(adapters):
    out = []
    for (i, (info, d)) in enumerate(adapters):
        serial = getattr(d, 'serial_number', None)
        adapter_str = ('[%(index)d] %(name)s: bus_addr: %(bus)03d:%(addr)03d vid_pid: %(vid)04x:%(pid)04x' %
                       dict(index=i, name=info['name'], bus=d.bus, addr=d.address, vid=d.idVendor, pid=d.idProduct))
        if serial is not None:
            adapter_str += (' serial: %(serial)s' % dict(serial=hex_str_literal_double_quoted(serial)))
        out.append(adapter_str)
    print('\n'.join(out))

def interactive_choose_adapter(options, adapters):
    # Possible design to improve UX:
    # (Remember last choice) select the last used adapter by default ('cursor' moved by up/down key) so the user could just press <Enter>
    # (Remember last choice per pty) Users tend to use the same debug adapter from the same Terminal tab
    # (Default to the first free debug adapter) 
    # (Change gdb prompt to contain adapter/board name)
    assert(not options.non_interactive)
    print_adapters_list(adapters)

    while True:
        choice_str = input('Which debug adapter? [0-%d] ' % (len(adapters)-1,))
        try:
            choice = int(choice_str)
            adapter = adapters[choice]
        except (ValueError, IndexError):
            print('Invalid adapter index %r' % (choice_str,))
        else:
            break
    return adapter

def intrusive_cortex_m_probe_and_setup(options, adapter, openocd_rpc):
    '-> (dap_info, mcu_info, openocd_rpc)'
    o = openocd_rpc
    mdetect = OpenOcdCortexMDetect(options, adapter, o)

    # Try SWD first (read IDCODE), if that fails falllback to JTAG
    # Use adapter_info and querying the adapters (e.g. cmsis-dap INFO_ID_CAPS command)
    # to know whether the adapter supports SWD/JTAG
    openocd_transport = 'swd'
    try:
        mdetect.openocd_init_for_detection(openocd_transport)
    except (OpenOcdOpenFailedDuringInit,) as e:
        logging.error("can't open adapter: %r" % (e.args[0],))
        sys.exit(3)
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
    # So declare_flash_bank is called afer openocd_init_for_detection() and before openocd_init_for_cortex_m()

    try:
        o.reset_halt()
    except OpenOcdResetError as e:
        sys.stderr.write("Can't reset the target CPU. Check debug connection wiring, "
                         "target power and hardware reset signals. Aborting.\n")
        sys.exit(4)

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
            o.reset_init()
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
        o.openocd_shutdown()
        waitpid_ignore_echild(o.pid)
        raise

    logging.info('mcu_info: %r' % (HexDict(mcu_info),))

    # Don't attempt to 'init' OpenOCD twice, shutdown then re-launch instead
    o.openocd_shutdown()
    waitpid_ignore_echild(o.pid)

    (o, openocd_newly_started_or_not) = openocd_rpc_for_adapter(adapter)
    mdetect = OpenOcdCortexMDetect(options, adapter, o)
    mdetect.openocd_init_for_cortex_m(openocd_transport, dap_info, mcu_info)
    # OpenOCD gdbserver is up after 'init'
    return (dap_info, mcu_info, o)

class OpenOcdSetupError(Exception):
    pass

def openocd_setup(options):
    '-> (adapter, dap_info, mcu_info, openocd_rpc)'

    if options.adapter_usb_vid_pid is not None:
        # VID:PID (hexadecimal)
        try:
            (usb_vid, usb_pid) = options.adapter_usb_vid_pid.split(':')
            (usb_vid, usb_pid) = (int(usb_vid, base=16), int(usb_pid, base=16))
        except (IndexError, ValueError):
            raise OpenOcdSetupError('%r is not a valid USB VID:PID' % (options.adapter_usb_vid_pid,))
        try:
            adapter = easierocd.usb.adapter_by_usb_vid_pid((usb_vid, usb_pid))
        except AdapterNotFound:
            raise OpenOcdSetupError("Can't find adapter with specified VID:PID")
        except AdapterNotSupported:
            raise OpenOcdSetupError('Specified adapter is not supported')
        except MultipleAdaptersMatchCriteria as e:
            raise OpenOcdSetupError(('More than one adapter has the specified USB VID:PID (%s)!\n' % (options.adapter_usb_vid_pid,))
                                    + e.args[0])
    elif options.adapter_usb_serial is not None:
        # support non-ASCII USB serial numbers with "\xFF" syntax
        try:
            serial = options.adapter_usb_serial.encode('ascii').decode('unicode-escape')
        except ValueError:
            raise OpenOcdSetupError('%r is not a valid USB serial number' % (options.adapter_usb_serial,))
        try:
            adapter = easierocd.usb.adapter_by_usb_serial(serial)
        except AdapterNotFound:
            raise OpenOcdSetupError("Can't find adapter with specified serial number")
        except AdapterNotSupported:
            raise OpenOcdSetupError('Specified adapter is not supported')
        except MultipleAdaptersMatchCriteria as e:
            raise OpenOcdSetupError(('More than one adapter has the specified USB serial number (%s)!\n' % (options.adapter_usb_serial,))
                                    + e.args[0])
    elif options.adapter_usb_bus_addr is not None:
        # BUS:DEV (decimal)
        try:
            (bus_num, addr_num) = options.adapter_usb_bus_addr.split(':')
            (bus_num, addr_num) = (int(bus_num), int(addr_num))
        except (IndexError, ValueError):
            raise OpenOcdSetupError('%r is not a valid USB BUS:ADDR specifier' % (options.adapter_usb_bus_addr,))
        try:
            adapter = easierocd.usb.adapter_by_usb_bus_addr((bus_num, addr_num))
        except AdapterNotFound:
            raise OpenOcdSetupError("Can't find adapter with specified bus and device number")
        except AdapterNotSupported:
            raise OpenOcdSetupError('Specified adapter is not supported')
    else:
        adapters = easierocd.usb.connected_debug_adapters()
        if not adapters:
            raise OpenOcdSetupError('no supported debug adapters found')

        if len(adapters) == 1:
            adapter = adapters[0]
        else:
            if options.non_interactive is False:
                try:
                    adapter = interactive_choose_adapter(options, adapters)
                except EOFError:
                    raise OpenOcdSetupError('Exiting due to user action')
            else:
                raise OpenOcdSetupError("Multiple supported debug adapters exist. "
                                        "Use command line options or environment variables to choose one from:\n" +
                                        multiple_adapter_msg(adapters))

    # Doing pid file and tmux session cleanups here is bit hackish
    adapters = easierocd.usb.connected_debug_adapters()
    pid_files_cleanup(adapters)
    tmux_sessions_cleanup(adapters)
    
    (o, openocd_newly_started_or_not) = openocd_rpc_for_adapter(adapter)
    logging.debug('openocd_newly_started_or_not: %d' % (openocd_newly_started_or_not,))

    openocd_connnection_unusable = False

    openocd_initialized = o.initialized()
    if not openocd_initialized:
        openocd_connnection_unusable = True

    target_names = []
    if not openocd_connnection_unusable:
        target_names = o.target_names()
        if not target_names:
            openocd_connnection_unusable = True
        elif not target_names or 'EASIEROCD_DETECT.cpu' in target_names:
            openocd_connnection_unusable = True

    # Mostly for USB cable or SWD/JTAG wire unplugs
    poll_info = None
    if not openocd_connnection_unusable:
        try:
            # OpenOCD's poll() detects the CPU state
            poll_info = o.poll()
        except TargetCommunicationError:
            logging.debug('openocd_setup: poll: OpenOcdCortexMDetectError')
            openocd_connnection_unusable = True

    dap_info = None
    if not openocd_connnection_unusable:
        assert(poll_info is not None)
        mdetect = OpenOcdCortexMDetect(options, adapter, o)
        try:
            dap_info = mdetect.detect_dap()
        except OpenOcdCortexMDetectError:
            logging.debug('openocd_setup: detect_dap: OpenOcdCortexMDetectError')
            openocd_connnection_unusable = True

    mcu_info = None
    if not openocd_connnection_unusable:
        assert(dap_info is not None)
        try:
            mcu_info = mdetect.detect_mcu(dap_info)
        except OpenOcdCortexMDetectError:
            logging.debug('openocd_setup: detect_mcu: OpenOcdCortexMDetectError')
            openocd_connnection_unusable = True

    logging.debug('target_names: %r, poll_info: %r, dap_info: %r, mcu_info: %r' % (target_names, poll_info, dap_info, mcu_info))
    if openocd_connnection_unusable:
        logging.debug('Restarting OpenOCD to re-do all the config including probing')
        o.openocd_shutdown()
        waitpid_ignore_echild(o.pid)
        (o, openocd_newly_started_or_not) = openocd_rpc_for_adapter(adapter)
        do_intrusive_probe = True
    else:
        do_intrusive_probe = False

    if not do_intrusive_probe:
        assert(poll_info is not None)
        assert(dap_info is not None)
        assert(mcu_info is not None)
        logging.debug('Reusing OpenOCD daemon config, skipping probe')
        return (adapter, dap_info, mcu_info, o)
    else:
        # hard coding assumption that ARM Cortex-M is debug target
        logging.debug('Attempting OpenOCD intrusive Cotex-M probe')
        (dap_info, mcu_info, o) = intrusive_cortex_m_probe_and_setup(options, adapter, o)

    return (adapter, dap_info, mcu_info, o)

@main_function
def eocd_setup(args):
    '''
    # easierocd-setup 
    Interactively choose and save which 
    '''
    pass

@main_function
def eocd_gdb(args):
    '# Start gdb session already connected to the debug adapter'
    logging.basicConfig(level=logging.DEBUG)

    def print_usage_exit():
        sys.stderr.write('easierocd-gdb [OPTIONS] GDB_ARUGMENTS...\n'
                         'OPTIONS:\n'
                         '\t--eocd-gdb-file ELF\n'
                         '\t--eocd-adapter-usb-serial   SERIAL\n'
                         '\t--eocd-adapter-usb-bus-addr BUS:ADDR\n'
                         '\t--eocd-adapter-usb-vid-pid  VID:PID\n'
                         '\t--eocd-non-interactive\n'
                         'Any unkown options are passed to GDB\n'
                         'Option names start with "eocd-" to avoid clashes with GDB\n'
                         'Environemnt Variables\n'
                         '\tGDB: use "$GDB" as the gdb executable\n'
                         '\tHOST: use "$HOST-gdb" as the GDB executable\n'
                         '\tEOCD_ADAPTER_USB_SERIAL: use debug adapter with specified USB serial\n'
                         '\tEOCD_ADAPTER_USB_BUS_ADDR: use debug adapter with" specified USB bus and adddress number\n'
                         '\tEOCD_ADAPTER_USB_VID_PID: use debug adapter with" specified USB vendor and product ID\n'
                         '\tEOCD_NON_INTERACTIVE: non-interactive mode. Never prompt\n'
                         )
        sys.exit(2)

    options = Bag()
    options.gdb_file = None
    options.adapter_usb_serial = os.environ.get('EOCD_ADAPTER_USB_SERIAL')
    options.adapter_usb_bus_addr = os.environ.get('EOCD_ADAPTER_USB_BUS_ADDR')
    options.adapter_usb_vid_pid = os.environ.get('EOCD_ADAPTER_USB_VID_PID')
    options.non_interactive = os.environ.get('EOCD_NON_INTERACTIVE', False)

    (i, gdb_args) = (0, [])

    while i < len(args):
        a = args[i]
        if a in set(['-h', '--help']):
            print_usage_exit()
        elif a == '--eocd-non-interactive':
            options.non_interactive = True
        elif a == '--eocd-gdb-file':
            try:
                options.gdb_file = args[i+1]
            except IndexError:
                sys.stderr.write('%s: --eocd-gdb-file requires an argument\n' % (program_name(),))
                sys.exit(2)
            i += 1
        elif a == '--eocd-adapter-usb-bus-addr':
            try:
                options.adapter_usb_bus_addr = args[i+1]
            except IndexError:
                sys.stderr.write('%s: --eocd-adapter-usb-bus-addr requires an argument\n' % (program_name(),))
                sys.exit(2)
            i += 1
        elif a == '--eocd-adapter-usb-serial':
            try:
                options.adapter_usb_serial = args[i+1]
            except IndexError:
                sys.stderr.write('%s: --eocd-adapter-usb-serial requires an argument\n' % (program_name(),))
                sys.exit(2)
            i += 1
        elif a == '--eocd-adapter-usb-vid-pid':
            try:
                options.adapter_usb_vid_pid = args[i+1]
            except IndexError:
                sys.stderr.write('%s: --eocd-adapter-usb-vid-pid requires an argument\n' % (program_name(),))
                sys.exit(2)
            i += 1
        else:
            gdb_args.append(a)
        i += 1

    if isinstance(options.non_interactive, str):
        options.non_interactive = bool(ast.literal_eval(options.non_interactive))
    assert(isinstance(options.non_interactive, bool))
            
    try:
        (adapter, dap_info, mcu_info, o) = openocd_setup(options)
    except OpenOcdSetupError as e:
        sys.stderr.write(e.args[0])
        sys.stderr.write('\n')
        sys.exit(3)

    o.set_arm_semihosting(True)
    # TODO: Free up TCL port? Think about concurrent debug & program
    # o.close()

    gdb_cmd = os.environ.get('GDB')
    if gdb_cmd is None:
        t = os.environ.get('HOST')
        if t is not None:
            # e.g. 'arm-none-eabi' + '-gdb'
            gdb_cmd = '%s-gdb' % (t,)

    if gdb_cmd is None:
        logging.warning('Can your "gdb" command really debug ARM Cortex-M targets? Export GDB or HOST environment variables if this fails')
        gdb_cmd = 'gdb'
    
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
        gdb_process = subprocess.Popen([gdb_cmd] + gdb_args)
    except FileNotFoundError:
        sys.stderr.write('%s: gdb command %r not found\n' % (program_name(), gdb_cmd))
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
def eocd_program(args):
    help_msg = 'program flash memory'
    options = Bag()
    o = OpenOcdRpc() # FIXME: ...
    # run reset-init handlers which might to switch the MCU to a higher clock
    # to speed up flash programming
    (adapter, dap_info, mcu_info, o) = openocd_setup(options)
    o.reset_init()
    # OpenOCD's 'program' command terminates the daemon when done so we can't use it

@main_function
def eocd_stop(args):
    help_msg = 'stop all background processes'

@main_function
def eocd_list(args):

    def print_usage_exit():
        sys.stderr.write('%s\nLists connected debug adapters' % (program_name(),))
        sys.exit(2)

    if args:
        print_usage_exit()

    adapters = easierocd.usb.connected_debug_adapters()
    print_adapters_list(adapters)

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
