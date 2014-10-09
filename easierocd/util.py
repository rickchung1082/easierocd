from __future__ import absolute_import

import sys
import os
import errno

class HexDict(dict):
    'Dictionary that prints int members as hex'
    def __repr__(self):
        out = ['{ ']
        for (n, v) in self.items():
            if type(v) is int:
                out.append('%r: 0x%x, ' % (n, v))
            else:
                out.append('%r: %r, ' % (n, v))
        out.append('}')
        return ''.join(out)

    __str__ = __repr__

class Bag(object):
    pass

def waitpid_ignore_echild(pid):
    'waitpid ignore "no such child process" errors'
    try:
        r = os.waitpid(pid, 0)
    except ChildProcessError:
        return None
    else:
        return r

def kill_ignore_echild(pid, sig):
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        pass
