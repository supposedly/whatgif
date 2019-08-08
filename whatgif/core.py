import struct
from collections import namedtuple
from collections.abc import MutableSequence

import numpy as np

from . import classes, lzw, util


@util.proxy('slots', 'properties', logical_screen_descriptor=classes.LogicalScreenDescriptor)
class GIF(MutableSequence):
    """
    Represents an animated GIF.
    
    This is an opinionated class. It assumes a lot of things about
    the GIF to be created: that it'll be animated, that it'll have
    both a global color table and delay time, etc.
    All assumed values are manually resettable, however.
    """
    def __init__(self,
      loop_count: int = 0,
      *,
      delay_time: int = 0,
      canvas_width: int = None,
      canvas_height: int = None
    ):
        self.header = classes.Header()
        self.logical_screen_descriptor = classes.LogicalScreenDescriptor(canvas_width, canvas_height)
        self.global_color_table = classes.ColorTable()
        self.netscape_looping_extension = classes.NetscapeApplicationExtension(loop_count)
        
        self.images = []
        self.global_delay_time = delay_time
    
    def __bytes__(self):
        if self:
            self[0].use_graphic_control_extension = True
        return b''.join(map(bytes, [
          self.header,
          self.logical_screen_descriptor,
          self.global_color_table,
          self.netscape_looping_extension,
          *self,
          b'\x3b'
        ]))
    
    def __getitem__(self, idx):
        return self.images.__getitem__(idx)
    
    def __setitem__(self, idx, value):
        if not isinstance(value, Frame):
            value = self.create_frame(value)
        self.update_dims(value.image_descriptor)
        self.images.__setitem__(idx, value)
    
    def __delitem__(self, idx):
        self.images.__delitem__(idx)
    
    def __len__(self):
        return self.images.__len__()
    
    def insert(self, idx, value):
        if not isinstance(value, Frame):
            value = self.create_frame(value)
        self.update_dims(value.image_descriptor)
        self.images.insert(idx, value)
    
    def create_frame(self, pixels, delay_time=None, *, transparent_color_index=None):
        use_graphic_control_extension = False
        
        if delay_time is None:
            delay_time = self.global_delay_time
        elif delay_time != self.global_delay_time:
            use_graphic_control_extension = True
        if transparent_color_index is None:
            transparent_color_index = self.global_color_table.transparent_color_index
        elif transparent_color_index != self.global_color_table.transparent_color_index:
            use_graphic_control_extension = True
        
        return Frame(
          pixels,
          self,
          delay_time=delay_time,
          transparent_color_index=transparent_color_index,
          use_graphic_control_extension=use_graphic_control_extension
        )
    
    def update_dims(self, image_descriptor):
        self.canvas_width = image_descriptor.width
        self.canvas_height = image_descriptor.height
    
    def update_color_table_size(self):
        self.global_color_table_size = self.global_color_table.size()


@util.proxy('slots', image_descriptor=classes.ImageDescriptor)
@util.proxy('slots', 'properties', _graphic_control_extension=classes.GraphicControlExtension)
class Frame:
    def __init__(self,
      pixels,
      gif,
      *,
      use_graphic_control_extension=False,
      color_table=None,
      color_indices=None,
      delay_time=None,
      transparent_color_index=None,
    ):
        self.gif = gif
        if not isinstance(pixels, np.ndarray):
            pixels = np.array(pixels)
        self._color_table = color_table
        self.pixels = pixels
        self.colors = set(map(tuple, np.unique(self.pixels.reshape(-1, 3), axis=0)))
        self.update_color_table()
        if color_indices is None:
            _ctable = self.color_table
            color_indices = np.apply_along_axis(
              lambda color: _ctable[tuple(color)],
              2,
              pixels
            )
        self.color_indices = color_indices
        self.image_descriptor = classes.ImageDescriptor(*self.color_indices.shape)
        self._graphic_control_extension = classes.GraphicControlExtension(
          self.gif.global_delay_time if delay_time is None else delay_time,
          transparent_color_index
        )
        self.use_graphic_control_extension = use_graphic_control_extension or color_table is not None
    
    def __eq__(self, other):
        if not isinstance(other, Frame):
            return NotImplemented
        return (self.pixels == other.pixels).all(2)
    
    '''
    def __imod__(self, other):
        if not isinstance(other, Frame):
            return NotImplemented
        # TODO: use self.pixels and classes.ColorTable.TRANSPARENT here instead
        transparent = self.color_table.transparent_color_index
        self.color_indices[self == other] = transparent
        eq = self.color_indices == transparent
        # argmin() gets the first False value's index,
        # aka the number of starting Trues to erase
        cols, rows = eq.all(0).argmin(), eq.all(1).argmin()
        self.color_indices = self.color_indices[rows:, cols:]
        self.pixels = self.pixels[rows:, cols:]
        self.left = cols
        self.top = rows
        return self
    '''
    
    def __bytes__(self):
        ba = bytearray()
        if self.use_graphic_control_extension:
            ba.extend(bytes(self._graphic_control_extension))
        ba.extend(bytes(self.image_descriptor))
        ba.extend(lzw.compress(self.color_indices.flat, self.color_table))
        return bytes(ba)
    
    @property
    def color_table(self):
        if self._color_table is None:
            return self.gif.global_color_table
        return self._color_table
    
    @color_table.setter
    def color_table(self, value):
        self._color_table = value
    
    def update_color_table(self):
        self.color_table.extend(self.colors.difference(self.color_table.underlying))
        if self._color_table is None:
            self.gif.update_color_table_size()
        else:
            self.local_color_table_size = self.color_table.size
