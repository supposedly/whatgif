def next_po2(n):
    return 1 << (n - 1).bit_length() if n else 1
