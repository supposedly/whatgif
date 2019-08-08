import inspect
from functools import partial, reduce, wraps
from operator import attrgetter


def next_po2(n) -> int:
    """
    Returns least power of 2 that is >= n
    """
    if not n:
        return 1
    if is_po2(n):
        # n is a power of 2
        return n
    return 1 << (n - 1).bit_length()


def is_po2(n) -> bool:
    """
    Returns true iff n is a power of 2
    """
    return not (n & (n - 1))


def join_bits(byteseq) -> int:
    """
    Given a sequence of 0/1 or True/False bits altogether representing a
    single byte, joins said bits into an int of the same magnitude

    >>> join_bits([1, 1, 0, 1])
    13
    """
    return reduce(lambda acc, bit: (acc << 1) | int(bit), byteseq)


def to_bin(n, pad=3) -> str:
    """
    Converts `n` to a binary-number string, padded with `pad` no. of zeroes
    """
    return bin(n)[2:].zfill(pad)


def subblockify(data: bytes) -> bytes:
    """
    Properly segments data into 255-byte-max sub-blocks.
    """
    # TODO: make less inefficient.
    ba = bytearray()
    # insert 0xff byte before every 255-byte run
    for idx in range(255, len(data), 255):
        ba.append(255)
        ba.extend(data[idx-255:idx])
    # insert amount of remaining bytes
    ba.append(len(data) if len(data) < 255 else len(data) - idx)
    ba.extend(data[idx:])
    return bytes(ba)


def check_null_slots(obj) -> None:
    for attr in obj.__slots__:
        if getattr(obj, attr) is None:
            raise ValueError('Please set {} attribute of {.__class__.__name__}'.format(attr, obj))


def proxy(*what, **kwargs):
    """
    Class decorator that adds property getter/setters corresponding
    to the slots of a given class.
    Kwargs must be in this format:
        {attr name : attr's expected type}
    Positional args consist of the strings 'properties' and 'slots',
    whose presence indicates that they should be proxied.
    """
    what = set(map(str.casefold, what))
    slots, properties = 'slots' in what, 'properties' in what
    def inner(cls):
        for attr_name, attr_cls in kwargs.items():
            if properties:
                for proxied_prop_name, proxied_prop in inspect.getmembers(attr_cls, property.__instancecheck__):
                    setattr(cls, proxied_prop_name, property(
                        transformative_partial(proxied_prop.__get__, attrgetter(attr_name)),
                        transformative_partial(proxied_prop.__set__, attrgetter(attr_name), None),
                        transformative_partial(proxied_prop.__delete__, attrgetter(attr_name))
                    ))
            if slots:
                for proxied_attr in getattr(attr_cls, '__slots__', ()):
                    setattr(cls, proxied_attr, property(
                      partial(_proxy_getf, attr_name, proxied_attr),
                      partial(_proxy_setf, attr_name, proxied_attr),
                      partial(_proxy_delf, attr_name, proxied_attr),
                    ))
        return cls
    return inner


def transformative_partial(func, *transformers, **kw_transformers):
    """
    Each argument given should line up with a parameter of `func`. If not None,
    it will be called on the corresponding argument of `func` before said argument
    is passed to it.
    
    After I wrote this I realized it was basically a worse (but syntactically
    less-hacky) version of the typehint transformer I use in ergo. May replace
    this with that later.
    """
    if not callable(func):
        raise TypeError('First argument must be callable')
    if not all(map(callable, {*transformers, *kw_transformers.values()} - {None})):
        raise ValueError('All transformers must be callable or None')
    #TODO: check varargs' lengths against number of params func takes
    @wraps(func)
    def wrapper(*args, **kwargs):
        args = [
          arg if transformer is None else transformer(arg)
          for transformer, arg in zip(transformers, args)
        ]
        kwargs = {
          name: arg if transformer is None else transformer(arg)
          for transformer, name, arg in zip(kw_transformers, kwargs.keys(), kwargs.values())
        }
        return func(*args, **kwargs)
    return wrapper


def _proxy_getf(attr_name, proxied_attr, self):
    return getattr(getattr(self, attr_name), proxied_attr)


def _proxy_setf(attr_name, proxied_attr, self, value):
    setattr(getattr(self, attr_name), proxied_attr)


def _proxy_delf(attr_name, proxied_attr, self):
    delattr(getattr(self, attr_name), proxied_attr)
