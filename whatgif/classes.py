import struct
from collections import OrderedDict
from itertools import count, repeat

from . import util


class Header:
    __slots__ = 'version',
    
    def __init__(self, version: str = b'89a'):
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

    def __init__(self,
      has_global_color_table: bool = None,
      color_resolution: int = None,
      sort: bool = None,
      size: int = None
    ):
        self.has_global_color_table = has_global_color_table
        self.color_resolution = color_resolution
        self.sort = sort
        self.size = size
    
    def __int__(self):
        return util.join_bits(
          self.has_global_color_table,
          *util.to_bin(self.color_resolution, 3),
          self.sort,
          *util.to_bin(self.size, 3)
        )


class ImageColorField:
    __slots__ = (
      'has_local_color_table',
      'interlace',
      'sort',
      'local_color_table_size'
    )
    
    def __init__(self,
      has_local_color_table: bool = False,
      interlace: bool = False,
      sort: bool = False,
      local_color_table_size: int = 0
    ):
        self.has_local_color_table = has_local_color_table
        self.interlace = interlace
        self.sort = sort
        self.local_color_table_size = local_color_table_size
    
    def __int__(self):
        return util.join_bits(
          self.has_local_color_table,
          self.interlace,
          self.sort,
          0, 0,  # 'reserved for future use'
          *util.to_bin(self.local_color_table_size, 3)
        )


class GraphicsControlField:
    __slots__ = (
      '_disposal_method',
      'wait_for_user_input',
      'has_transparency'
    )
    
    DISPOSAL_METHODS = [None, 'accumulate', 'replace', 'restore']
    _DISPOSAL_MAP = dict(map(reversed, enumerate(DISPOSAL_METHODS)))
    
    def __init__(self,
      disposal_method: str = None,
      wait_for_user_input: bool = False,
      has_transparency: bool = True
    ):
        self._disposal_method = None
        self.disposal_method = disposal_method
        self.wait_for_user_input = wait_for_user_input
        self.has_transparency = has_transparency
    
    @property
    def disposal_method(self):
        return self._DISPOSAL_MAP[self._disposal_method]
    
    @disposal_method.setter
    def disposal_method(self, value):
        try:
            self._disposal_method = self.DISPOSAL_METHODS[value]
        except KeyError:
            raise ValueError("Invalid disposal method {}".format(value))
    
    def __int__(self):
        return util.join_bits(
          0, 0, 0,  # 'reserved for future use'
          *util.to_bin(self._disposal_method, 3),
          self.wait_for_user_input,
          self.has_transparency
        )


@util.proxy('slots', color_field=TableColorField)
class LogicalScreenDescriptor:
    __slots__ = (
      'canvas_width',
      'canvas_height',
      'color_field',
      'background_color_index',
      'pixel_aspect_ratio'
    )
    
    def __init__(self,
      canvas_width: int = None,
      canvas_height: int = None,
      color_field: TableColorField = None,
      background_color_index: int = None,
      pixel_aspect_ratio: int = 0
    ):
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.color_field = TableColorField() if color_field is None else color_field
        self.background_color_index = background_color_index
        self.pixel_aspect_ratio = pixel_aspect_ratio
    
    def __bytes__(self):
        return struct.pack('<HHBBB',
          self.canvas_width,
          self.canvas_height,
          int(self.color_field),
          self.background_color_index,
          self.pixel_aspect_ratio
        )


class ColorTable:
    TRANSPARENT = object()

    __slots__ = '_ensure_transparent', '_od', '_li', '_len'

    def __init__(self, iterable=()):
        self._ensure_transparent = False
        self._od = OrderedDict()
        self._li = []
        self._len = count()
        self.extend(iterable)
    
    def __bytes__(self):
        return bytes([component for rgb in self for component in rgb])
    
    def __getitem__(self, value):
        if isinstance(value, int):
            if value == -1:
                return ColorTable.TRANSPARENT
            elif value < 0:
                raise ValueError('ColorTables do not hold negative indices such as {}'.format(value))
            return self._li.__getitem__(value)
        if value is ColorTable.TRANSPARENT:
            return -1
        return self._od.__getitem__(value)
    
    def __iter__(self):
        yield from self.underlying
        yield from repeat((0, 0, 0), len(self) - self.underlying_length())
    
    def __len__(self):
        return int(2 ** (1 + self.size()))
    
    def _length(self):
        length = self.underlying_length()
        return length if util.is_po2(length) else util.next_po2(1 + length)
    
    @property
    def _size_offset(self):
        return int(self._ensure_transparent and self.underlying_length() == self._length())
    
    def size(self):
        # self._length() == (2 ** size + 1)
        # _size_offset is there to ensure there will be a transparent color
        # which is accounted for by __len__()
        return self._length().bit_length() - 2 + self._size_offset
    
    def underlying_length(self):
        assert len(self._od) == len(self._li)
        return len(self._od)
    
    def append(self, color):
        if color is ColorTable.TRANSPARENT:
            self.ensure_transparent_color()
            return
        if len(color) != 3 or not (0, 0, 0) <= color < (256, 256, 256):
            raise ValueError('Color-table values must be a single-byte-each RGB tuple')
        if color in self:
            raise ValueError('Color {} already exists with code {}'.format(
              color, self[color]
            ))
        self._od[color] = next(self._len)
        self._li.append(color)
    
    def extend(self, colors):
        for v in list(colors) if colors is self else colors:
            self.append(v)
    
    @property
    def transparent_color_index(self):
        self.ensure_transparent_color()
        return len(self) - 1
    
    @property
    def underlying(self):
        yield from self._od
    
    def ensure_transparent_color(self):
        self._ensure_transparent = True


@util.proxy('slots', color_field=ImageColorField)
class ImageDescriptor:
    __slots__ = (
      'width',
      'height',
      'left',
      'top',
      'color_field'
    )

    def __init__(self,
      width: int,
      height: int,
      left: int = 0,
      top: int = 0
    ):
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


class Extension:
    INTRODUCER = b'\x21'
    LABEL = b''
    BLOCK_SIZE = 0

    __slots__ = ()
    
    def __bytes__(self):
        return b''.join([
          self.INTRODUCER,
          self.LABEL,
          b'' if self.BLOCK_SIZE == 0 else self.BLOCK_SIZE.to_bytes(1, 'little')
        ])


@util.proxy('slots', 'properties', field=GraphicsControlField)
class GraphicsControlExtension(Extension):
    LABEL = b'\xf9'
    BLOCK_SIZE = 4

    __slots__ = 'field', 'delay_time', 'transparent_color_index'
    
    def __init__(self, delay_time, transparent_color_index):
        self.field = GraphicsControlField()
        self.delay_time = delay_time
        self.transparent_color_index = transparent_color_index
    
    def __bytes__(self):
        return super().__bytes__() + bytearray([
          0x04,
          int(self.field),
          self.delay_time,
          self.transparent_color_index,
          0x00
        ])


class ApplicationExtension(Extension):
    LABEL = b'\xff'
    BLOCK_SIZE = 11

    IDENTIFIER = b''
    AUTH_CODE = b''
    
    __slots__ = ()
    
    def __bytes__(self):
        return b''.join([
          super().__bytes__(),
          (len(self.IDENTIFIER) + len(self.AUTH_CODE)).to_bytes(1, 'little'),
          self.IDENTIFIER,
          self.AUTH_CODE
        ])


class NetscapeApplicationExtension(ApplicationExtension):
    IDENTIFIER = b'NETSCAPE'
    AUTH_CODE = b'2.0'

    __slots__ = 'loop_count',
    
    def __init__(self, loop_count: int = 0):
        self.loop_count = loop_count
    
    def __bytes__(self):
        return b''.join([
          super().__bytes__(),
          b'\x03',
          b'\x01',
          self.loop_count.to_bytes(2, 'little'),
          b'\x00'
        ])


class PlainTextExtension(Extension):
    LABEL = b'\x01'
    BLOCK_SIZE = 12
    
    __slots__ = (
      'text_left',
      'text_right',
      'grid_width',
      'grid_height',
      'char_cell_width',
      'char_cell_height',
      'text_fg_color_index',
      'text_bg_color_index',
      '_data'
    )

    def __init__(self,
      text_left: int,
      text_right: int,
      grid_width: int,
      grid_height: int,
      char_cell_width: int,
      char_cell_height: int,
      text_fg_color_index: int,
      text_bg_color_index: int,
      data: str = None
    ):
      self.text_left = text_left
      self.text_right = text_right
      self.grid_width = grid_width
      self.grid_height = grid_height
      self.char_cell_width = char_cell_width
      self.char_cell_height = char_cell_height
      self.text_fg_color_index = text_fg_color_index
      self.text_bg_color_index = text_bg_color_index
      self._data = data
    
    @property
    def data(self):
        return self._data.encode('ascii')
    
    @data.setter
    def data(self, value):
        if isinstance(value, (bytes, bytearray)):
            self._data = value.decode('ascii')
        elif isinstance(value, str):
            self._data = value
        else:
            raise TypeError("Value must be bytes, bytearray, or str, not '{}'".format(type(value)))
    
    def __bytes__(self):
        return b''.join([
          super().__bytes__(),
          struct.pack(
            '<HHHHBBBB',
            self.text_left,
            self.text_right,
            self.grid_width,
            self.grid_height,
            self.char_cell_width,
            self.char_cell_height,
            self.text_fg_color_index,
            self.text_bg_color_index
          ),
          util.subblockify(self.data),
          b'\x00'
        ])


class CommentExtension(Extension):
    LABEL = b'\xfe'
    
    __slots__ = '_data',
    
    def __init__(self, data: str):
        self._data = data
    
    @property
    def data(self):
        return self._data.encode('ascii')
    
    @data.setter
    def data(self, value):
        if isinstance(value, (bytes, bytearray)):
            self._data = value.decode('ascii')
        elif isinstance(value, str):
            self._data = value
        else:
            raise TypeError("Value must be bytes, bytearray, or str, not '{}'".format(type(value)))
    
    def __bytes__(self):
        return super().__bytes__() + util.subblockify(self.data) + b'\x00'
