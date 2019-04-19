import struct
from collections import namedtuple
from collections.abc import MutableSequence

import numpy as np

from . import classes, lzw


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
    def __init__(self, pixels, gif, *, color_table=None, color_indices=None):
        if not isinstance(pixels, np.ndarray):
            pixels = np.array(pixels)
        if color_table is None:
            color_table = gif.global_color_table
        self.color_table = color_table
        self.pixels = pixels
        self.colors = {tuple(i) for i in self.pixels.reshape((-1, 3))}
        self.update_color_table()
        self.color_indices = np.apply_along_axis(
          lambda color: self.color_table[tuple(color)],
          2,
          pixels
          ) if color_indices is None else color_indices
        self.image_descriptor = classes.ImageDescriptor(*self.color_indices.shape)
        self.gif = gif
    
    def __eq__(self, other):
        if not isinstance(other, Frame):
            return NotImplemented
        return (self.pixels == other.pixels).all(2)
    
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
        self.image_descriptor.left = cols
        self.image_descriptor.top = rows
        return self
    
    def __bytes__(self):
        ...
    
    def update_color_table(self):
        self.color_table.extend(
          self.colors.difference(self.color_table)
        )
    
    def compress(self):
        data = lzw.compress(self.data.flat, self.color_table)
        # XXX: does the data even need to be 2D after height/width are determined??
        # TODO XXX: what to do with compressed data
        raise NotImplementedError
