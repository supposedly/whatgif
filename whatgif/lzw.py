import struct

from . import misc


class _BitStream:
    def __init__(self):
        self._buffer = []
    
    def append(self, bits):
        ...


class CodeTable:
    MAX_CODE_SIZE = 12

    def __init__(self, color_table):
        self._d = {}
        self.min_code_size = max(self.MAX_CODE_SIZE, 1 + color_table.size())
        self._code_size = 1 + self.min_code_size  # initialize to 'first code size'
        self._max_code = 2 ** self.min_code_size - 1
        self.clear = 1 + self._max_code
        self.eoi = 1 + self.clear
        self._cur_code = 0
        self._codes_used = set()
        self.out = _BitStream()
    
    def __contains__(self, key):
        return self._d.__contains__(key)
    
    def __getitem__(self, key):
        return self._d.__getitem__(key)
    
    def __setitem__(self, key, value):
        self._codes_used.add(value)
        self._d.__setitem__(key, value)
    
    def add(self, indices):
        self[indices] = self._cur_code
        self._codes_used.add(self._cur_code)
        self._cur_code += 1
    
    def output(self, indices):
        code = self[indices]
        self.out.append(code)
        if code.bit_length() == self._code_size:
            if self._code_size == self.MAX_CODE_SIZE:
                self.out.append(self.clear)
                self._code_size = 1 + self.min_code_size  # reset to 'first code size'
            else:
                self._code_size += 1


def compress(data, color_table, color_indices):
    code_table = CodeTable(color_table)
    # XXX: all this tuple stuff feels really inefficient
    idx_stream = iter(color_indices)
    idx_buffer = next(idx_stream),
    for k in idx_stream:
        if (*idx_buffer, k) in code_table:
            idx_buffer += k,
            continue
        code_table.add((*idx_buffer, k))
        code_table.output(idx_buffer)
        idx_buffer = k,
    code_table.output(idx_buffer)
    code_table.output(code_table.eoi)
    return code_table.out
