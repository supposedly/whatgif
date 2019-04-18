import struct
from collections import namedtuple
from collections.abc import MutableSequence

import numpy as np

from . import classes


class GIF(MutableSequence):
    def __init__(self, version='89a', width=None, height=None):
        self.header = classes.Header(version)
        self.logical_screen_descriptor = classes.LogicalScreenDescriptor(width, height)
        self.global_color_table = classes.ColorTable()
        self.images = []
    
    def __getitem__(self, idx):
        return self.images.__getitem__(idx)
    
    def __setitem__(self, idx, value):
        if not isinstance(value, Frame):
            value = self.create_frame(value)
        self.images.__setitem__(idx, value)
    
    def __delitem__(self, idx):
        self.images.__delitem__(idx)
    
    def __len__(self):
        return self.images.__len__()
    
    def insert(self, idx, value):
        self.images.insert(idx, value)
    
    def create_frame(self, pixels):
        return Frame(pixels, self)


class Frame:
    def __init__(self, pixels, gif, color_table=None):
        if not isinstance(pixels, np.ndarray):
            pixels = np.array(pixels)
        if color_table is None:
            color_table = gif.global_color_table
        self.color_table = color_table
        self.image_descriptor = classes.ImageDescriptor(*pixels.shape[:2])
        self.data = np.vectorize(self.color_table.__getitem__)(pixels)
        self.colors = set(pixels.flat)
        self.gif = gif
    
    def __imod__(self, other):
        if not isinstance(other, Frame):
            return NotImplemented
        self.data[self == other] = 0
        return self
    
    def __bytes__(self):
        ...
    
    def update_color_table(self):
        self.color_table.extend(
          self.colors.difference(self.color_table)
        )
    
    def compress(self):
        ...
    

