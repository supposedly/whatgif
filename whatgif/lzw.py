from collections.abc import MutableSequence


class CodeTable(MutableSequence):
    def __init__(self, color_table, min_code_size):
        self._li = []
        self.min_code_size = min_code_size
        self.clear = '\x00'
        self.eoi = '\x01'
    
    def __getitem__(self, idx):
        if idx >= len(self._li) and idx < self.min_code_size:
            return (0, 0, 0)
        return self._li.__getitem__(idx)
    
    def __iter__(self):
        yield from self._li
        for _ in range(len(self._li), self.min_code_size):
            yield (0, 0, 0)
        yield self.clear
        yield self.eoi
    
    def __len__(self):
        return self.min_code_size + 2


def compress(data, code_table):
    ret = [code_table.clear]