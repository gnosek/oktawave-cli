import sys

from prettytable import PrettyTable


class Printer:
    def __init__(self, output=sys.stdout):
        self.output = output

    def print_str(self, text):
        print >> self.output, text

    def offset_print(self, text, offset=1):
        self.print_str(offset * ' ' + text)

    def print_table(self, data, hmarg=1):
        for i in xrange(hmarg):
            self.print_str('')
        x = PrettyTable(data[0])
        if hasattr(x, 'set_field_align'):
            for f in data[0]:
                x.set_field_align(f, 'l')
        if hasattr(x, 'align'):
            x.align = 'l'
        for row in data[1:]:
            x.add_row(row)
        print unicode(x)
        for i in xrange(hmarg):
            self.print_str('')

    def print_hash_table(self, data, headers=None, order=False):
        if headers is None:
            headers = []

        def ext(key):
            res = [key if not order else key.partition(' ')[2]]
            res.extend(data[key])
            return res

        data_array = [headers] if len(headers) > 0 else []
        keys = data.keys()
        if order:
            keys = [i[0] + ' ' + i[2]
                    for i in sorted([k.partition(' ') for k in keys], key=lambda x: int(x[0]))]
        data_array.extend(map(ext, keys))
        self.print_table(data_array)


# a small test
if __name__ == '__main__':
    p = Printer()
    p.print_table([
        ['', 'B', 'C', 'D'],
        ['1', '2', '3', '4'],
        ['aaa', 'bb', 'a', 'aaaaaa']
    ])
    p.print_hash_table({'a': ['b'], 'c': ['d']}, ['key', 'value'])
