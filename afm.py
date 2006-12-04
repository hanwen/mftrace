# this file is part of mftrace - a tool to generate scalable fonts from bitmaps  
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2
# as published by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,

# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA 

# Copyright (c)  2001--2006 by
#  Han-Wen Nienhuys, Jan Nieuwenhuizen



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

