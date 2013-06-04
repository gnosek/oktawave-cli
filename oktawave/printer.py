import sys
from prettytable import PrettyTable

class Printer:
	def __init__(self, output = sys.stdout):
		self.output = output
	def _print(self, text):
		print >> self.output, text
	def offset_print(self, text, offset = 1):
		self._print(offset * ' ' + text)
	def print_table(self, data, hmarg = 1):
		for i in xrange(hmarg):
			self._print('')
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
			self._print('')
	def _swift_object_type(self, data):
		if data['content_type'] == 'application/directory':
			return 'directory'
		if data['content_type'] == 'application/object':
			return 'object'
		return 'file'
	def print_hash_table(self, data, headers = [], order = False):
		def ext(k):
			res = [k if not order else k.partition(' ')[2]]
			res.extend(data[k])
			return res
		data_array = [headers] if len(headers) > 0 else []
		keys = data.keys()
		if order:
			keys = [i[0] + ' ' + i[2] for i in sorted([k.partition(' ') for k in keys], key = lambda x : int(x[0]))]
		data_array.extend(map(ext, keys))
		self.print_table(data_array)
	def list_swift_objects(self, container, path = None, cname = ''):
		if path == None:
			path = ''
		elif not path.endswith('/'):
			path = path + '/'
		if str(container.__class__) == "<type 'tuple'>":
			container = container[1]
		data = container
		if len([1 for d in data if d['content_type'] == 'application/directory' and d['name'] + '/' == path]) == 0 and path != '':
			print "No such container/directory!"
			return
		print ('Container' if path == '' else 'Directory') + " content:"
		self.print_table(
			[['Name', 'Type', 'Size in bytes', 'Full path']] +
			[
				[(row[0][len(path):].count('/') * '  ') + row[0].rpartition('/')[2]] + row[1:]
				for row in sorted([[o['name'], self._swift_object_type(o), o['bytes'], cname + '/' + o['name']] for o in data], key = lambda row : row[0]) if row[0].startswith(path)
			]
		)
	def print_swift_file(self, data):
		if str(data.__class__) == "<type 'tuple'>" and len(data) == 2:
			d = data[0]
			attrs = dict((key[14:], d[key]) for key in d.keys() if key[0:13] == 'x-object-meta')
			data = (d['content-type'], d['content-length'], d['last-modified'], d['etag'], attrs, data[1])
		(ctype, size, date, etag, attrs, content) = data
		if ctype == 'application/directory':
			print '<DIRECTORY>'
		elif ctype == 'application/object':
			self.print_table([['Key', 'Value']] + [[
				key,
				attrs[key]
			] for key in sorted(attrs.keys(), key = lambda x : x.lower())]);
		else:
			print content
	def print_swift_container(self, data):
		print "<CONTAINER>"
	
# a small test	
if __name__ == '__main__':
	p = Printer()
	p.print_table([
		['', 'B', 'C', 'D'],
		['1', '2', '3', '4'],
		['aaa', 'bb', 'a', 'aaaaaa']
	])
	p.print_hash_table({'a' : ['b'], 'c' : ['d']}, ['key', 'value'])
