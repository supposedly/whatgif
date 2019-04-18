import struct
from collections import OrderedDict
from itertools import count

from . import misc


class Header:
    __slots__ = 'version',

    def __init__(self, version=b'89a'):
        if version != b'89a':
            raise ValueError('GIF versions other than 89a are unsupported')
        self.version = version
    
    def __bytes__(self):
        return b'GIF' + self.version


class TableColorField:
    __slots__ = (
      'has_global_color_table',
      'color_resolution',
      'sort',
      'size'
    )

    def __init__(self, has_global_color_table=None, color_resolution=None, sort=None, size=None):
        self.has_global_color_table = has_global_color_table
        self.color_resolution = color_resolution
        self.sort = sort
        self.size = size

    def __int__(self):
        return int(''.join(map(str, [
          int(self.has_global_color_table),
          *map(int, bin(self.color_resolution)[2:].zfill(3)),
          int(self.sort),
          *map(int, bin(self.size)[2:].zfill(3))
        ])), 2)


class ImageColorField:
    __slots__ = (
      'has_local_color_table',
      'interlace',
      'sort',
      'local_color_table_size'
    )
    
    def __init__(self, has_local_color_table=False, interlace=False, sort=False, local_color_table_size=0):
        self.has_local_color_table = has_local_color_table
        self.interlace = interlace
        self.sort = sort
        self.local_color_table_size = local_color_table_size
    
    def __int__(self):
        return int(''.join(map(str, [
          int(self.has_local_color_table),
          int(self.interlace),
          int(self.sort),
          0, 0,  # 'reserved for future use'
          *map(int, bin(self.local_color_table_size)[2:].zfill(3))
        ])), 2)


class GraphicsControlField:
    __slots__ = (
      'disposal_method',
      'wait_for_user_input',
      'has_transparency'
    )

    def __init__(self, disposal_method=0, wait_for_user_input=False, has_transparency=True):
        self.disposal_method = disposal_method
        self.wait_for_user_input = wait_for_user_input
        self.has_transparency = has_transparency
    
    def __int__(self):
        return int(''.join(map(str, [
          0, 0, 0,  # 'reserved for future use'
          *map(int, bin(self.disposal_method)[2:].zfill(3)),
          int(self.wait_for_user_input),
          int(self.has_transparency)
        ])), 2)


class LogicalScreenDescriptor:
    __slots__ = (
      'canvas_width',
      'canvas_height',
      'color_field',
      'background_color_index',
      'pixel_aspect_ratio'
    )

    def __init__(self, canvas_width=None, canvas_height=None, color_field=None, background_color_index=None, pixel_aspect_ratio=0):
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.color_field = TableColorField() if color_field is None else color_field
        self.background_color_index = background_color_index
        self.pixel_aspect_ratio = pixel_aspect_ratio
    
    def __bytes__(self):
        return struct.pack(
          '<HHBBB',
          self.canvas_width,
          self.canvas_height,
          int(self.color_field),
          self.background_color_index,
          self.pixel_aspect_ratio
        )


class ColorTable:
    def __init__(self, iterable=()):
        self._od = OrderedDict()
        self._len = count()
        self.extend(iterable)
    
    def __bytes__(self):
        return bytes([component for rgb in self for component in rgb])
    
    def __getitem__(self, color):
        return self._od.__getitem__(color)
    
    def __iter__(self):
        yield from self.underlying
        for _ in range(self.underlying_length(), len(self)):
            yield (0, 0, 0)
    
    def __len__(self):
        underlying = self.underlying_length()
        return underlying if misc.is_po2(underlying) else misc.next_po2(1 + underlying)
    
    def append(self, value):
        if len(value) != 3 or not (0, 0, 0) <= value < (256, 256, 256):
            raise ValueError('Color-table values must be a single-byte-each RGB tuple')
        if value in self:
            raise ValueError('RGB tuple {} already exists in color table with code {}'.format(value, self[value]))
        self._od[value] = next(self._len)
    
    def extend(self, values):
        for v in list(values) if values is self else values:
            self.append(v)
    
    @property
    def underlying(self):
        yield from self._od
    
    def underlying_length(self):
        return len(self._od)
    
    def size(self):
        # invariant: length == 2 ** (size + 1)
        return len(self).bit_length() - 2


class Extension:
    INTRODUCER = b'\x21'
    LABEL = b''

    def __bytes__(self):
        return self.INTRODUCER + self.LABEL


class GraphicsControlExtension(Extension):
    LABEL = b'\xf9'
    
    def __init__(self, delay_time, transparent_color_index):
        self.field = GraphicsControlField()
        self.delay_time = delay_time
        self.transparent_color_index = transparent_color_index
    
    def __bytes__(self):
        return super().__bytes__() + (
          b'\x04'  # XXX: not sure if this should change
          + struct.pack('BBB', int(self.field), self.delay_time, self.transparent_color_index)
          + b'\x00'
        )


class ImageDescriptor:
    __slots__ = (
      'width',
      'height',
      'left',
      'top',
      'color_field'
    )

    def __init__(self, width, height, left=0, top=0):
        self.width = width
        self.height = height
        self.left = left
        self.top = top
        self.color_field = ImageColorField()
    
    def __bytes__(self):
        return struct.pack(
          '<BHHHHB',
          0x2c,  # image-separator
          self.left,
          self.top,
          self.width,
          self.height,
          int(self.color_field)
        )


class ApplicationExtension(Extension):
    LABEL = b'\xff'
    IDENTIFIER = b'NETSCAPE'
    AUTH_CODE = b'2.0'
    
    __slots__ = 'loop_count',
    
    def __init__(self, loop_count=0):
        self.loop_count = loop_count
    
    def __bytes__(self):
        return super().__bytes__() + (
          self.IDENTIFIER + self.AUTH_CODE
          + b'\x03'  # XXX: unclear whether this should change based on loop_count's bit length
          + b'\x01'
          + struct.pack('<H', self.loop_count)
          + b'\x00'
        )

