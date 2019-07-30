from functools import reduce


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
