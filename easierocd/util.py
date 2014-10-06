from __future__ import absolute_import

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
