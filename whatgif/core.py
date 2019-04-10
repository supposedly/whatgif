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
        self.images.__setitem__(idx, value)
    
    def __delitem__(self, idx):
        self.images.__delitem__(idx)
    
    def __len__(self):
        return self.images.__len__()
    
    def insert(self, idx, value):
        self.images.insert(idx, value)


class Frame:
    def __init__(self, ndarray):
        ...
