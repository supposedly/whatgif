from functools import reduce
from itertools import repeat

from . import util


class BitStream:
    """
    Represents an LZW bitstream used for compression
    """
    def __init__(self):
        self._buffer = []
        self._out = bytearray()
    
    def __bytes__(self):
        if self._buffer:
            self._consume_byte()
        return bytes(self._out)
    
    def _consume_byte(self):
        """
        Consumes one byte from the buffer and appends it to the output stream
        """
        self._out.append(util.join_bits(self._buffer[7::-1]))
        del self._buffer[:8]
    
    def append(self, n, code_size):
        """
        Appends `n` to buffer bit-by-bit, padding to `code_size`
        """
        fill = code_size - n.bit_length()
        while n:
            self._buffer.append(n % 2)
            n //= 2
        self._buffer.extend(repeat(0, fill))
        if len(self._buffer) >= 8:
            self._consume_byte()


class CodeTable:
    MAX_CODE_SIZE = 12
    
    def __init__(self, color_table):
        self._d = {}
        self.min_code_size = max(2, min(self.MAX_CODE_SIZE, 1 + color_table.size()))
        self._code_size = self._first_code_size = 1 + self.min_code_size
        self._max_code = 2 ** self.min_code_size - 1
        self._clear = 1 + self._max_code
        self._eoi = 1 + self._clear
        self._cur_code = 1 + self._eoi
        self._codes_used = set()
        for color_code in range(self._cur_code):
            self[color_code,] = color_code
        self.out = BitStream()
    
    def __contains__(self, key):
        return self._d.__contains__(key)
    
    def __getitem__(self, key):
        return self._d.__getitem__(key)
    
    def __setitem__(self, key, value):
        self._codes_used.add(value)
        if value == 2 ** self._code_size:
            if self._code_size == self.MAX_CODE_SIZE:
                self.clear()
                self._code_size = self._first_code_size
            else:
                self._code_size += 1
        self._d.__setitem__(key, value)
    
    def add(self, indices):
        self[indices] = self._cur_code
        while self._cur_code in self._codes_used:
            self._cur_code += 1
    
    def output(self, indices):
        code = self[indices]
        self.out.append(code, self._code_size)
    
    def clear(self):
        self.out.append(self._clear, self._code_size)
    
    def eoi(self):
        self.out.append(self._eoi, self._code_size)


def compress(color_indices, color_table, code_table=None) -> bytes:
    """
    color_indices: iterable of `color_table` indices
    color_table: classes.ColorTable object
    code_table: optional, lzw.CodeTable object (automatically created if None)

    LZW-compresses GIF colors
    """
    if code_table is None:
        code_table = CodeTable(color_table)
    # XXX: all this tuple stuff feels really inefficient
    idx_stream = iter(color_indices)
    idx_buffer = next(idx_stream),
    code_table.clear()
    for k in idx_stream:
        if (*idx_buffer, k) in code_table:
            idx_buffer += k,
            continue
        code_table.output(idx_buffer)
        code_table.add((*idx_buffer, k))
        idx_buffer = k,
    code_table.output(idx_buffer)
    code_table.eoi()
    return bytes(code_table.out)
