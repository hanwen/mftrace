import re
import sys

# Read some global vars 
class Afm_reader:
	def __init__ (self, lines):
		self.lines = lines

	def get_afm (self):
		afm = Afm_font_metric ()
		for i in self.lines[:20]:
			m = re.match ('([^ \t\n]*)[ \t]*(.*[^ \t\n])', i)
			if m and m.group (1):
				key = m.group (1)
				value = m.group (2)
				if key != 'Comment':
					afm.__dict__[key] = value
		return afm

class Afm_font_metric:
	def __init__ (self):
		pass
	
def read_afm_file (filename):
	reader = Afm_reader (open (filename).readlines ())
	return reader.get_afm ()

if __name__ == '__main__':
	i = read_afm_file  (sys.argv[1])
	print i, i.FullName, i.FontName

