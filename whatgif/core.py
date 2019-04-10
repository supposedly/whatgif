import struct
from collections import namedtuple
from collections.abc import MutableSequence

import numpy as np

from . import classes as aux


class GIF(MutableSequence):
    def __init__(self, version='89a', width=None, height=None):
        self.header = aux.Header(version)
        self.logical_screen_descriptor = aux.LogicalScreenDescriptor(width, height)
        self.global_color_table = aux.ColorTable()
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
    def __init__(self, pixels, gif):
        if not isinstance(pixels, np.ndarray):
            pixels = np.array(pixels)
        self.image_descriptor = aux.ImageDescriptor(*pixels.shape[:2])
        self.data = pixels
        self.colors = set(self.data.flat)
        self.gif = gif
    
    def __bytes__(self):
        ...
    
    def update_color_table(self):
        self.gif.global_color_table.extend(
          self.colors.difference(self.gif.global_color_table)
        )
    
    def compress(self):
        ...
    

