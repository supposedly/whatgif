def next_po2(n) -> int:
    if not n:
        return 1
    if is_po2(n):
        # n is a power of 2
        return n
    return 1 << (n - 1).bit_length()


def is_po2(n) -> bool:
    return not (n & (n - 1))


def join_bytes(args) -> int:
        ret = 0
        for i, v in enumerate(reversed(args)):
            if int(v):
                ret += 2 ** i
        return ret


def to_bin(n, pad=3) -> str:
    return bin(n)[2:].zfill(pad)
