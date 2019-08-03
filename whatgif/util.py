from functools import partial, reduce


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


def proxy_slots_of(**kwargs):
    """
    Class decorator that adds property getter/setters corresponding
    to the slots of a given class. Kwargs must be in this format:
        {attr name : attr's expected type}
    """
    def inner(cls):
        for attr_name, attr_cls in kwargs.items():
            for proxied_attr in getattr(attr_cls, '__slots__', ()):
                setattr(cls, proxied_attr, property(
                  partial(_proxy_getf, attr_name, proxied_attr),
                  partial(_proxy_setf, attr_name, proxied_attr),
                  partial(_proxy_delf, attr_name, proxied_attr),
                ))
        return cls
    return inner


def _proxy_getf(attr_name, proxied_attr, self):
    return getattr(getattr(self, attr_name), proxied_attr)


def _proxy_setf(attr_name, proxied_attr, self, value):
    setattr(getattr(self, attr_name), proxied_attr)


def _proxy_delf(attr_name, proxied_attr, self):
    delattr(getattr(self, attr_name), proxied_attr)
