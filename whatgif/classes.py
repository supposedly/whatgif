import struct
from collections import OrderedDict
from itertools import count, repeat

from . import util


class Header:
    """
    Implements the GIF Header block.
    More or less deadweight.
    """
    __slots__ = 'version',
    
    def __init__(self, version: bytes = b'89a'):
        self.version = version
    
    def __bytes__(self):
        return b'GIF' + self.version


class TableColorField:
    """
    Implements the packed field to do with color used by the Logical
    Screen Descriptor block.
    """
    __slots__ = (
      'has_global_color_table',
      'color_resolution',
      'sort',
      'size'
    )
    
    def __init__(self,
      has_global_color_table: bool = True,
      color_resolution: int = 1,
      sort: bool = False,
      size: int = None
    ):
        self.has_global_color_table = has_global_color_table
        self.color_resolution = color_resolution
        self.sort = sort
        self.size = size
    
    def __int__(self):
        util.check_null_slots(self)
        return util.join_bits(
          self.has_global_color_table,
          *util.to_bin(self.color_resolution, 3),
          self.sort,
          *util.to_bin(self.size, 3)
        )


class ImageColorField:
    """
    Implements the packed field to do with color used by the Image
    Descriptor block.
    """
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


class GraphicControlField:
    """
    Implements the packed field used by the Graphic Control Extension.
    NB: "wait_for_user_input" isn't a flag typically paid attention to.
    """
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
    """
    Implements the Logical Screen Descriptor block, used to set various
    attributes of the GIF file as a whole.
    """
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
        util.check_null_slots(self)
        return struct.pack('<HHBBB',
          self.canvas_width,
          self.canvas_height,
          int(self.color_field),
          self.background_color_index,
          self.pixel_aspect_ratio
        )


class ColorTable:
    """
    Implements global and local color tables. Colors are stored
    in order of insertion as (r, g, b) tuples; filler (0, 0, 0)
    tuples are used to pad the table to the nearest po2 length.

    `_ensure_transparent` indicates whether to ensure that there
    is always room for an extra transparent color -- that is, to
    ensure that the table always an unused color slot.
    """
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
    """
    Implements the Image Descriptor block, used for... describing an
    image.
    """
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
    """
    Base class for GIF-format extensions.
    Subclasses must define class variables "LABEL" and "BLOCK_SIZE"
    with the appropriate `bytes` value and int value, respectively.
    """
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


@util.proxy('slots', 'properties', field=GraphicControlField)
class GraphicControlExtension(Extension):
    """
    Implements the Graphic Control extension, used for specifying
    various behaviors/properties of the next frame relating to
    graphics.
    """
    LABEL = b'\xf9'
    BLOCK_SIZE = 4

    __slots__ = 'field', 'delay_time', 'transparent_color_index'
    
    def __init__(self, delay_time, transparent_color_index):
        self.field = GraphicControlField()
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
    """
    Base class for Application extensions, used for implementing
    application-specific extra functionality.
    Subclasses must define class variables IDENTIFIER and AUTH_CODE
    with the appropriate `bytes` values. (Note that there is really
    only one possible subclass, b/c not many Application extensions
    exist besides the Netscape Looping Application Extension below)
    """
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
    """
    Implements the Netscape Looping Application Extension, used to
    set the amount of times a GIF should loop.
    """
    IDENTIFIER = b'NETSCAPE'
    AUTH_CODE = b'2.0'

    __slots__ = 'loop_count',
    
    def __init__(self, loop_count: int = 0):
        self.loop_count = loop_count
    
    def __bytes__(self):
        return b''.join([
          super().__bytes__(),
          b'\x03',  # size of subsequent block
          b'\x01',  # 'subblock identifier', fixed value
          self.loop_count.to_bytes(2, 'little'),
          b'\x00'
        ])


class PlainTextExtension(Extension):
    """
    Implements the Plain Text extension, used for rendering text rather
    than displaying an image on a given frame.
    NB: class included solely for spec-completeness. Not a single one
    of today's popular GIF-viewing apps implements this PT extension.
    """
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
    """
    Implements the Comment Extension, used for including comments
    unseen in the final GIF.
    """
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
