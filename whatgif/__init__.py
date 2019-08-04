__version__ = '0.0.0'

# XXX: make sure classes is ALWAYS imported before core
# for the sake of preserving the util.proxy()-ing order
from . import classes
from . import core, lzw, util
