#!@PYTHON@

#
# this file is part of mftrace - a tool to generate scalable fonts from MF sources  
#

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

import string
import os
import optparse
import sys
import re
import tempfile
import shutil

prefix = '@prefix@'
bindir = '@bindir@'
datadir = '@datadir@'
localedir = datadir + '/locale'
libdir = '@libdir@'
exec_prefix = '@exec_prefix@'

def interpolate (str):
    str = string.replace (str, '{', '(')
    str = string.replace (str, '}', ')s')
    str = string.replace (str, '$', '%')
    return str

if prefix != '@' + 'prefix@':
    exec_prefix = interpolate (exec_prefix) % vars ()
    bindir = interpolate (bindir) % vars ()
    datadir = os.path.join (interpolate (datadir) % vars (), 'mftrace')
    libdir = interpolate (libdir) % vars ()

if datadir == '@' + "datadir" + "@":
    datadir = os.getcwd ()
    bindir =  os.getcwd ()
    
sys.path.append (datadir)

import afm
import tfm

errorport = sys.stderr

################################################################
# lilylib.py -- options and stuff
#
# source file of the GNU LilyPond music typesetter

try:
    import gettext
    gettext.bindtextdomain ('mftrace', localedir)
    gettext.textdomain ('mftrace')
    _ = gettext.gettext
except:
    def _ (s):
        return s

def shell_escape_filename (str):
    str = re.sub ('([\'" ])', r'\\\1', str)
    return str

def identify (port):
    port.write ('%s %s\n' % (program_name, program_version))

def warranty ():
    identify (sys.stdout)
    sys.stdout.write ('\n')
    sys.stdout.write (_ ('Copyright (c) %s by' % ' 2001--2004'))
    sys.stdout.write ('\n')
    sys.stdout.write ('  Han-Wen Nienhuys')
    sys.stdout.write ('  Jan Nieuwenhuizen')
    sys.stdout.write ('\n')
    sys.stdout.write (_ (r'''
Distributed under terms of the GNU General Public License.  It comes with
NO WARRANTY.'''))
    sys.stdout.write ('\n')

def progress (s):
    errorport.write (s)

def warning (s):
    errorport.write (_ ("warning: ") + s)

def error (s):
    '''Report the error S and exit with an error status of 1.

    RETURN VALUE

    None

    '''

    errorport.write (_ ("error: ") + s + '\n')
    errorport.write (_ ("Exiting ...") + '\n')
    sys.exit(1)

temp_dir = None
class TempDirectory:
    def __init__ (self, name=None):
        import tempfile
        if name:
            if not os.path.isdir (name):
                os.makedirs (name)
            self.dir = name
        else:
            self.dir = tempfile.mkdtemp ()

        os.chdir (self.dir)
        
    def clean (self):
        import shutil
        shutil.rmtree (self.dir)
    def __del__ (self):
        self.clean ()
    def __call__ (self):
        return self.dir
    def __repr__ (self):
        return self.dir
    def __str__ (self):
        return self.dir

def setup_temp  (name):
    global temp_dir
    if not temp_dir:
        temp_dir = TempDirectory (name)
    return temp_dir ()

def popen (cmd, mode = 'r', ignore_error = 0):
    if options.verbose:
        progress (_ ("Opening pipe `%s\'") % cmd)
    pipe = os.popen (cmd, mode)
    if options.verbose:
        progress ('\n')
    return pipe

def system (cmd, ignore_error = 0):
    """Run CMD. If IGNORE_ERROR is set, don't complain when CMD returns non zero.

    RETURN VALUE

    Exit status of CMD
    """

    if options.verbose:
        progress (_ ("Invoking `%s\'\n") % cmd)
    st = os.system (cmd)
    if st:
        name = re.match ('[ \t]*([^ \t]*)', cmd).group (1)
        msg = name + ': ' + _ ("command exited with value %d") % st
        if ignore_error:
            warning (msg + ' ' + _ ("(ignored)") + ' ')
        else:
            error (msg)
    if options.verbose:
        progress ('\n')
    return st

def strip_extension (f, ext):
    (p, e) = os.path.splitext (f)
    if e == ext:
        e = ''
    return p + e


################################################################
# END Library



options = None 
exit_value = 0
backend_options = ''
program_name = 'mftrace'
temp_dir = None
program_version = '@VERSION@'
origdir = os.getcwd ()

coding_dict = {

    # from TeTeX
    'TeX typewriter text': '09fbbfac.enc', # cmtt10
    'TeX math symbols': '10037936.enc', # cmbsy
    'ASCII caps and digits': '1b6d048e', # cminch
    'TeX math italic': 'aae443f0.enc', # cmmi10
    'TeX extended ASCII': 'd9b29452.enc',
    'TeX text': 'f7b6d320.enc',
    'TeX text without f-ligatures': '0ef0afca.enc',
    'Extended TeX Font Encoding - Latin': 'tex256.enc',

    # LilyPond.
    'fetaBraces': 'feta-braces-a.enc',
    'fetaNumber': 'feta-nummer10.enc',
    'fetaMusic': 'feta20.enc',
    'parmesanMusic': 'parmesan20.enc',
    }


def find_file (nm):
    for d in include_dirs:
        p = os.path.join (d, nm)
        try:
            open (p)
            return os.path.abspath (p)
        except IOError:
            pass

    p = popen ('kpsewhich %s' % shell_escape_filename (nm)).read ()
    p = p.strip ()
    
    if options.dos_kpath:
        orig = p
        p = string.lower (p)
        p = re.sub ('^([a-z]):', '/cygdrive/\\1', p)
        p = re.sub ('\\\\', '/', p)
        sys.stderr.write ("Got `%s' from kpsewhich, using `%s'\n" % (orig, p))
    return p


def flag_error ():
    global exit_value
    exit_value = 1
            
################################################################
# TRACING.
################################################################

def autotrace_command (fn, opts):
    opts = " " + opts + " --background-color=FFFFFF --output-format=eps --input-format=pbm "
    return options.trace_binary + opts + backend_options \
       + " --output-file=char.eps %s " % fn

def potrace_command (fn, opts):
    return options.trace_binary + opts \
        + ' -u %d ' % options.grid_scale \
        + backend_options \
        + " -q -c --eps --output=char.eps %s " % (fn)

trace_command = None
path_to_type1_ops = None

def trace_one (pbmfile, id):
    """
    Run tracer, do error handling
    """

    status = system (trace_command (pbmfile, ''), 1)

    if status == 2:
        sys.stderr.write ("\nUser interrupt. Exiting\n")
        sys.exit (2)

    if status == 0 and options.keep_temp_dir:
        shutil.copy2 (pbmfile, '%s.pbm' % id)
        shutil.copy2 ('char.eps', '%s.eps' % id)

    if status != 0:
        error_file = os.path.join (origdir, 'trace-bug-%s.pbm' % id)
        shutil.copy2 (pbmfile, error_file)
        msg = """Trace failed on bitmap.  Bitmap left in `%s\'
Failed command was:

    %s

Please submit a bugreport to %s development.""" \
        % (error_file, trace_command (error_file, ''), options.trace_binary)

        if options.keep_trying:
            warning (msg)
            sys.stderr.write ("\nContinuing trace...\n")
            flag_error ()
        else:
            msg = msg + '\nRun mftrace with --keep-trying to produce a font anyway\n'
            error (msg)
    else:
        return 1

    if status != 0:
        warning ("Failed, skipping character.\n")
        return 0
    else:
        return 1

def make_pbm (filename, outname, char_number):
    """ Extract bitmap from the PK file FILENAME (absolute) using `gf2pbm'.
    Return FALSE if the glyph is not valid.
    """

    command = "%s/gf2pbm -n %d -o %s %s" % (bindir, char_number, outname, filename)
    status = system (command, ignore_error = 1)
    return (status == 0)

def read_encoding (file):
    sys.stderr.write (_ ("Using encoding file: `%s'\n") % file)

    str = open (file).read ()
    str = re.sub ("%.*", '', str)
    str = re.sub ("[\n\t \f]+", ' ', str)
    m = re.search ('/([^ ]+) \[([^\]]+)\] def', str)
    if not m:
        error ("Encoding file is invalid")

    name = m.group (1)
    cod = m.group (2)
    cod = re.sub ('[ /]+', ' ', cod)
    cods = string.split (cod)

    return (name, cods)

def zip_to_pairs (xs):
    r = []
    while xs:
        r.append ((xs[0], xs[1]))
        xs = xs[2:]
    return r

def unzip_pairs (tups):
    lst = []
    while tups:
        lst = lst + list (tups[0])
        tups = tups[1:]
    return lst

def autotrace_path_to_type1_ops (at_file, bitmap_metrics, tfm_wid, magnification):
    inv_scale = 1000.0 / magnification

    (size_y, size_x, off_x, off_y) = map (lambda m, s = inv_scale: m * s,
                       bitmap_metrics)
    ls = open (at_file).readlines ()
    bbox = (10000, 10000, -10000, -10000)

    while ls and ls[0] != '*u\n':
        ls = ls[1:]

    if ls == []:
        return (bbox, '')

    ls = ls[1:]

    commands = []


    while ls[0] != '*U\n':
        ell = ls[0]
        ls = ls[1:]

        toks = string.split (ell)

        if len (toks) < 1:
            continue
        cmd = toks[-1]
        args = map (lambda m, s = inv_scale: s * float (m),
              toks[:-1])
        if options.round_to_int:
            args = zip_to_pairs (map (round, args))
        else:
            args = zip_to_pairs (args)
        commands.append ((cmd, args))

    expand = {
        'l': 'rlineto',
        'm': 'rmoveto',
        'c': 'rrcurveto',
        'f': 'closepath',
        }

    cx = 0
    cy = size_y - off_y - inv_scale

    # t1asm seems to fuck up when using sbw. Oh well.
    t1_outline =  '  %d %d hsbw\n' % (- off_x, tfm_wid)
    bbox = (10000, 10000, -10000, -10000)

    for (c, args) in commands:

        na = []
        for a in args:
            (nx, ny) = a
            if c == 'l' or c == 'c':
                bbox = update_bbox_with_point (bbox, a)

            na.append ((nx - cx, ny - cy))
            (cx, cy) = (nx, ny)

        a = na
        c = expand[c]
        if options.round_to_int:
            a = map (lambda x: '%d' % int (round (x)),
                unzip_pairs (a))
        else:
            a = map (lambda x: '%d %d div' \
                % (int (round (x * options.grid_scale/inv_scale)),
                  int (round (options.grid_scale/inv_scale))),
                unzip_pairs (a))

        t1_outline = t1_outline + ' %s %s\n' % (string.join (a), c)

    t1_outline = t1_outline + ' endchar '
    t1_outline = '{\n %s } |- \n' % t1_outline

    return (bbox, t1_outline)

# FIXME: Cut and paste programming
def potrace_path_to_type1_ops (at_file, bitmap_metrics, tfm_wid, magnification):
    inv_scale = 1000.0 / magnification

    (size_y, size_x, off_x, off_y) = map (lambda m,
                       s = inv_scale: m * s,
                       bitmap_metrics)
    ls = open (at_file).readlines ()
    bbox =  (10000, 10000, -10000, -10000)

    while ls and ls[0] != '0 setgray\n':
        ls = ls[1:]

    if ls == []:
        return (bbox, '')
    ls = ls[1:]
    commands = []

    while ls and ls[0] != 'grestore\n':
        ell = ls[0]
        ls = ls[1:]

        if ell == 'fill\n':
            continue

        toks = string.split (ell)

        if len (toks) < 1:
            continue
        cmd = toks[-1]
        args = map (lambda m, s = inv_scale: s * float (m),
              toks[:-1])
        args = zip_to_pairs (args)
        commands.append ((cmd, args))

    # t1asm seems to fuck up when using sbw. Oh well.
    t1_outline = '  %d %d hsbw\n' % (- off_x, tfm_wid)
    bbox =  (10000, 10000, -10000, -10000)

    # Type1 fonts have relative coordinates (doubly relative for
    # rrcurveto), so must convert moveto and rcurveto.

    z = (0.0, size_y - off_y - 1.0)
    for (c, args) in commands:
        args = map (lambda x: (x[0] * (1.0 / options.grid_scale),
                   x[1] * (1.0 / options.grid_scale)), args)

        if c == 'moveto':
            args = [(args[0][0] - z[0], args[0][1] - z[1])]

        zs = []
        for a in args:
            lz = (z[0] + a[0], z[1] + a[1])
            bbox = update_bbox_with_point (bbox, lz)
            zs.append (lz)

        if options.round_to_int:
            last_discr_z = (int (round (z[0])), int (round (z[1])))
        else:
            last_discr_z = (z[0], z[1])
        args = []
        for a in zs:
            if options.round_to_int:
                a = (int (round (a[0])), int (round (a[1])))
            else:
                a = (a[0], a[1])
            args.append ((a[0] - last_discr_z[0],
                   a[1] - last_discr_z[1]))

            last_discr_z = a

        if zs:
            z = zs[-1]

        c = {
            'closepath': 'closepath',
            'moveto': 'rmoveto',
            'rcurveto': 'rrcurveto',
            # Potrace 1.9 
            'restore': '',
            'rlineto': 'rlineto',
            '%%EOF': '',
	}[c]

        if c == 'rmoveto':
            t1_outline += ' closepath '

        if options.round_to_int:
            args = map (lambda x: '%d' % int (round (x)),
                  unzip_pairs (args))
        else:
            args = map (lambda x: '%d %d div' \
                  % (int (round (x*options.grid_scale/inv_scale)),
                   int (round (options.grid_scale/inv_scale))),
                  unzip_pairs (args))

        t1_outline = t1_outline + '  %s %s\n' % (string.join (args), c)

    t1_outline = t1_outline + ' endchar '
    t1_outline = '{\n %s } |- \n' % t1_outline

    return (bbox, t1_outline)

def read_gf_dims (name, c):
    str = popen ('%s/gf2pbm -n %d -s %s' % (bindir, c, name)).read ()
    m = re.search ('size: ([0-9]+)+x([0-9]+), offset: \(([0-9-]+),([0-9-]+)\)', str)

    return tuple (map (int, m.groups ()))

def trace_font (fontname, gf_file, metric, glyphs, encoding,
        magnification, fontinfo):
    t1os = []
    font_bbox = (10000, 10000, -10000, -10000)

    progress (_ ("Tracing bitmaps..."))

    if options.verbose:
        progress ('\n')
    else:
        progress (' ')

    # for single glyph testing.
    # glyphs = []
    for a in glyphs:
        if encoding[a] == ".notavail":
            continue
        valid = metric.has_char (a)
        if not valid:
            encoding[a] = ".notavail"
            continue

        valid = make_pbm (gf_file, 'char.pbm', a)
        if not valid:
            encoding[a] = ".notavail"
            continue

        (w, h, xo, yo) = read_gf_dims (gf_file, a)

        if not options.verbose:
            sys.stderr.write ('[%d' % a)
            sys.stderr.flush ()

        # this wants the id, not the filename.
        success = trace_one ("char.pbm", '%s-%d' % (options.gffile, a))
        if not success:
            sys.stderr.write ("(skipping character)]")
            sys.stderr.flush ()
            encoding[a] = ".notavail"
            continue

        if not options.verbose:
            sys.stderr.write (']')
            sys.stderr.flush ()
        metric_width = metric.get_char (a).width
        tw = int (round (metric_width / metric.design_size * 1000))
        (bbox, t1o) = path_to_type1_ops ("char.eps", (h, w, xo, yo),
                        tw, magnification)

        if t1o == '':
            encoding[a] = ".notavail"
            continue

        font_bbox = update_bbox_with_bbox (font_bbox, bbox)

        t1os.append ('\n/%s %s ' % (encoding[a], t1o))

    if not options.verbose:
        progress ('\n')
    to_type1 (t1os, font_bbox, fontname, encoding, magnification, fontinfo)

def ps_encode_encoding (encoding):
    str = ' %d array\n0 1 %d {1 index exch /.notdef put} for\n' \
       % (len (encoding), len (encoding)-1)

    for i in range (0, len (encoding)):
        if encoding[i] != ".notavail":
            str = str + 'dup %d /%s put\n' % (i, encoding[i])

    return str


def gen_unique_id (dict):
    nm = 'FullName'
    return 4000000 + (hash (nm) % 1000000)

def to_type1 (outlines, bbox, fontname, encoding, magnification, fontinfo):
    
    """
    Fill in the header template for the font, append charstrings,
    and shove result through t1asm
    """
    template = r"""%%!PS-AdobeFont-1.0: %(FontName)s %(VVV)s.%(WWW)s
13 dict begin
/FontInfo 16 dict dup begin
/version (%(VVV)s.%(WWW)s) readonly def
/Notice (%(Notice)s) readonly def
/FullName (%(FullName)s) readonly def
/FamilyName (%(FamilyName)s) readonly def
/Weight (%(Weight)s) readonly def
/ItalicAngle %(ItalicAngle)s def
/isFixedPitch %(isFixedPitch)s def
/UnderlinePosition %(UnderlinePosition)s def
/UnderlineThickness %(UnderlineThickness)s def
end readonly def
/FontName /%(FontName)s def
/FontType 1 def
/PaintType 0 def
/FontMatrix [%(xrevscale)f 0 0 %(yrevscale)f 0 0] readonly def
/FontBBox {%(llx)d %(lly)d %(urx)d %(ury)d} readonly def
/Encoding %(Encoding)s readonly def
currentdict end
currentfile eexec
dup /Private 20 dict dup begin
/-|{string currentfile exch readstring pop}executeonly def
/|-{noaccess def}executeonly def
/|{noaccess put}executeonly def
/lenIV 4 def
/password 5839 def
/MinFeature {16 16} |-
/BlueValues [] |-
/OtherSubrs [ {} {} {} {} ] |-
/ForceBold false def
/Subrs 1 array
dup 0 { return } |
|-
2 index
/CharStrings %(CharStringsLen)d dict dup begin
%(CharStrings)s


/.notdef { 0 0 hsbw endchar } |-
end
end
readonly put
noaccess put
dup/FontName get exch definefont
pop mark currentfile closefile
cleartomark
"""
## apparently, some fonts end the file with cleartomark.  Don't know why.

    copied_fields = ['FontName', 'FamilyName', 'FullName', 'DesignSize',
            'ItalicAngle', 'isFixedPitch', 'Weight']

    vars = {
        'VVV': '001',
        'WWW': '001',
        'Notice': 'Generated from MetaFont bitmap by mftrace %s, http://www.xs4all.nl/~hanwen/mftrace/ ' % program_version,
        'UnderlinePosition': '-100',
        'UnderlineThickness': '50',
        'xrevscale': 1.0/1000.0,
        'yrevscale': 1.0/1000.0,
        'llx': bbox[0],
        'lly': bbox[1],
        'urx': bbox[2],
        'ury': bbox[3],
        'Encoding': ps_encode_encoding (encoding),

        # need one extra entry for .notdef
        'CharStringsLen': len (outlines) + 1,
        'CharStrings': string.join (outlines),
        'CharBBox': '0 0 0 0',
    }

    for k in copied_fields:
        vars[k] = fontinfo[k]

    open ('mftrace.t1asm', 'w').write (template % vars)

def update_bbox_with_point (bbox, pt):
    (llx, lly, urx, ury) = bbox
    llx = min (pt[0], llx)
    lly = min (pt[1], lly)
    urx = max (pt[0], urx)
    ury = max (pt[1], ury)

    return         (llx, lly, urx, ury)

def update_bbox_with_bbox (bb, dims):
    (llx, lly, urx, ury) = bb
    llx = min (llx, dims[0])
    lly = min (lly, dims[1])
    urx = max (urx, dims[2])
    ury = max (ury, dims[3])

    return (llx, lly, urx, ury)

def get_binary (name):
    search_path = string.split (os.environ['PATH'], ':')
    for p in search_path:
        nm = os.path.join (p, name)
        if os.path.exists (nm):
            return nm

    return ''

def get_fontforge_command ():
    fontforge_cmd = ''
    for ff in ['fontforge', 'pfaedit']:
        if get_binary(ff):
            fontforge_cmd = ff

    stat = 1
    if fontforge_cmd:
        stat = system ("%s -usage > pfv 2>&1 " % fontforge_cmd,
               ignore_error = 1)

        if stat != 0:
            warning ("Command `%s -usage' failed.  Cannot simplify or convert to TTF.\n" % fontforge_cmd)
            return ''

    if fontforge_cmd == 'pfaedit' \
     and re.search ("-script", open ('pfv').read ()) == None:
        warning ("pfaedit does not support -script.  Install 020215 or later.\nCannot simplify or convert to TTF.\n")
        return ''
    return fontforge_cmd

def tfm2kpx (tfmname, encoding):
    kpx_lines = []
    pl = popen ("tftopl %s" % (tfmname))
    
    label_pattern = re.compile (
        "\A   \(LABEL ([DOHC]{1}) ([A-Za-z0-9]*)\)")
    krn_pattern = re.compile (
        "\A   \(KRN ([DOHC]{1}) ([A-Za-z0-9]*) R (-?[\d\.]+)\)")

    first = 0
    second = 0

    for line in pl.readlines ():
        
        label_match = label_pattern.search (line)
        if not (label_match is None):
            if label_match.group (1) == "D":
                first = int (label_match.group (2))
            elif label_match.group (1) == "O":
                first = int (label_match.group (2), 8)
            elif label_match.group (1) == "C":
                first = ord (label_match.group (2))
            
        krn_match = krn_pattern.search (line)
        if not (krn_match is None):
            if krn_match.group (1) == "D":
                second = int (krn_match.group (2))
            elif krn_match.group (1) == "O":
                second = int (krn_match.group (2), 8)
            elif krn_match.group (1) == "C":
                second = ord (krn_match.group (2))
            
            krn = round (float (krn_match.group (3)) * 1000)
            
            if (encoding[first] != '.notavail' and 
                encoding[first] != '.notdef' and
                encoding[second] != '.notavail' and 
                encoding[second] != '.notdef'):
                
                kpx_lines.append ("KPX %s %s %d\n" % (
                    encoding[first], encoding[second], krn))
    
    return kpx_lines

def get_afm (t1_path, tfmname, encoding, out_path):
    afm_stream = popen ("printafm %s" % (t1_path))
    afm_lines = []
    kpx_lines = tfm2kpx (tfmname, encoding)
    
    for line in afm_stream.readlines ():
        afm_lines.append (line)
        
        if re.match (r"^EndCharMetrics", line, re.I):
            afm_lines.append ("StartKernData\n")
            afm_lines.append ("StartKernPairs %d\n" % len (kpx_lines))
            
            for kpx_line in kpx_lines:
                afm_lines.append (kpx_line)
            
            afm_lines.append ("EndKernPairs\n")
            afm_lines.append ("EndKernData\n")
    
    progress (_ ("Writing metrics to `%s'... ") % out_path)
    afm_file = open (out_path, 'w')
    afm_file.writelines (afm_lines)
    afm_file.flush ()
    afm_file.close ()
    
    progress ('\n')

def assemble_font (fontname, format, is_raw):
    ext = '.' + format
    asm_opt = '--pfa'

    if format == 'pfb':
      asm_opt = '--pfb'

    if is_raw:
      ext = ext + '.raw'

    outname = fontname + ext

    progress (_ ("Assembling raw font to `%s'... ") % outname)
    if options.verbose:
        progress ('\n')
    system ('t1asm %s mftrace.t1asm %s' % (asm_opt, shell_escape_filename (outname)))
    progress ('\n')
    return outname

def make_outputs (fontname, formats, encoding):
    """
    run pfaedit to convert to other formats
    """
 
    ff_needed = 0
    ff_command = ""
  
    if (options.simplify or options.round_to_int or 'ttf' in formats or 'svg' in formats or 'afm' in formats):
        ff_needed = 1
    if ff_needed:
        ff_command = get_fontforge_command ()
  
    if ff_needed and ff_command:
        raw_name = assemble_font (fontname, 'pfa', 1)

        simplify_cmd = ''
        if options.round_to_int:
            simplify_cmd = 'RoundToInt ();'
        generate_cmds = ''
        for f in formats:
            generate_cmds += 'Generate("%s");' % (fontname  + '.' + f)

        if options.simplify:
            simplify_cmd ='''SelectAll ();

AddExtrema();
Simplify ();
%(simplify_cmd)s
AutoHint ();''' % vars()

        pe_script = ('''#!/usr/bin/env %(ff_command)s
Open ($1);
MergeKern($2);
%(simplify_cmd)s
%(generate_cmds)s
Quit (0);
''' % vars())

        open ('to-ttf.pe', 'w').write (pe_script)
        if options.verbose:
            print 'Fontforge script', pe_script
        system ("%s -script to-ttf.pe %s %s" % (ff_command,
              shell_escape_filename (raw_name), shell_escape_filename (options.tfm_file)))
    elif ff_needed and (options.simplify or options.round_to_int or 'ttf' in formats or 'svg' in formats):
        error(_ ("fontforge is not installed; could not perform requested command"))
    else:
        t1_path = ''
    
        if ('pfa' in formats):
            t1_path = assemble_font (fontname, 'pfa', 0)

        if ('pfb' in formats):
            t1_path = assemble_font (fontname, 'pfb', 0)
    
        if (t1_path != '' and 'afm' in formats):
            if get_binary("printafm"):
                get_afm (t1_path, options.tfm_file, encoding, fontname + '.afm')
            else:
                error(_ ("Neither fontforge nor ghostscript is not installed; could not perform requested command"))


def getenv (var, default):
    if os.environ.has_key (var):
        return os.environ[var]
    else:
        return default

def gen_pixel_font (filename, metric, magnification):
    """
    Generate a GF file for FILENAME, such that `magnification'*mfscale
    (default 1000 * 1.0) pixels fit on the designsize.
    """
    base_dpi = 1200

    size = metric.design_size

    size_points = size * 1/72.27 * base_dpi

    mag = magnification / size_points

    prod = mag * base_dpi
    try:
        open ('%s.%dgf' % (filename, prod))
    except IOError:

        ## MFINPUTS/TFMFONTS take kpathsea specific values;
        ## we should analyse them any further.
        os.environ['MFINPUTS'] = '%s:%s' % (origdir,
                          getenv ('MFINPUTS', ''))
        os.environ['TFMFONTS'] = '%s:%s' % (origdir,
                          getenv ('TFMINPUTS', ''))

        progress (_ ("Running Metafont..."))

        cmdstr = r"mf '\mode:=lexmarks; mag:=%f; nonstopmode; input %s'" %  (mag, filename)
        if not options.verbose:
            cmdstr = cmdstr + ' 1>/dev/null 2>/dev/null'
        st = system (cmdstr, ignore_error = 1)
        progress ('\n')

        logfile = '%s.log' % filename
        log = ''
        prod = 0
        if os.path.exists (logfile):
            log = open (logfile).read ()
            m = re.search ('Output written on %s.([0-9]+)gf' % re.escape (filename), log)
            prod = int (m.group (1))

        if st:
            sys.stderr.write ('\n\nMetafont failed.  Excerpt from the log file: \n\n*****')
            m = re.search ("\n!", log)
            start = m.start (0)
            short_log = log[start:start+200]
            sys.stderr.write (short_log)
            sys.stderr.write ('\n*****\n')
            if re.search ('Arithmetic overflow', log):
                sys.stderr.write ("""

Apparently, some numbers overflowed.  Try using --magnification with a
lower number.  (Current magnification: %d)
""" % magnification)

            if not options.keep_trying or prod == 0:
                sys.exit (1)
            else:
                sys.stderr.write ('\n\nTrying to proceed despite of the Metafont errors...\n')
        
      

    return "%s.%d" % (filename, prod)

def parse_command_line ():
    p = optparse.OptionParser (version="""mftrace @VERSION@

This program is free software.  It is covered by the GNU General Public
License and you are welcome to change it and/or distribute copies of it
under certain conditions.  Invoke as `mftrace --warranty' for more
information.

Copyright (c) 2005--2006 by
 Han-Wen Nienhuys <hanwen@xs4all.nl> 

""")
    p.usage = "mftrace [OPTION]... FILE..."
    p.description = _ ("Generate Type1 or TrueType font from Metafont source.")

    p.add_option ('-k', '--keep',
                  action="store_true",
                  dest="keep_temp_dir",
                  help=_ ("Keep all output in directory %s.dir") % program_name)
    p.add_option ('','--magnification',
                  dest="magnification",
                  metavar="MAG",
                  default=1000.0,
                  type="float",
                  help=_("Set magnification for MF to MAG (default: 1000)"))
    p.add_option ('-V', '--verbose',
                  action='store_true',
                  default=False,
                  help=_ ("Be verbose"))
    p.add_option ('-f', '--formats',
                  action="append",
                  dest="formats",
                  default=[],
                  help=_("Which formats to generate (choices: AFM, PFA, PFB, TTF, SVG)"))
    p.add_option ('', '--simplify',
                  action="store_true",
                  dest="simplify",
                  help=_ ("Simplify using fontforge"))
    p.add_option ('', '--gffile',
                  dest="gffile",
                  help= _("Use gf FILE instead of running Metafont"))
    p.add_option ('-I', '--include',
                  dest="include_dirs",
                  action="append",
                  default=[],
                  help=_("Add to path for searching files"))
    p.add_option ('','--glyphs',
                  default=[],
                  action="append",
                  dest="glyphs",
                  metavar="LIST",
                  help= _('Process only these glyphs.  LIST is comma separated'))
    p.add_option ('', '--tfmfile',
                  metavar='FILE',
                  action='store',
                  dest='tfm_file')
    
    p.add_option ('-e', '--encoding',
                  metavar="FILE",
                  action='store',
                  dest="encoding_file",
                  default="",
                  help= _ ("Use encoding file FILE"))
    p.add_option ('','--keep-trying',
                  dest='keep_trying',
                  default=False,
                  action="store_true",
                  help= _ ("Don't stop if tracing fails"))
    p.add_option ('-w', '--warranty',
                  action="store_true",
                  help=_ ("show warranty and copyright"))
    p.add_option ('','--dos-kpath',
                  dest="dos_kpath",
                  help=_("try to use Miktex kpsewhich"))
    p.add_option ('', '--potrace',
                  dest='potrace',
                  help=_ ("Use potrace"))
    p.add_option ('', '--autotrace',
                  dest='autotrace',
                  help=_ ("Use autotrace"))
    p.add_option ('', '--no-afm',
                  action='store_false',
                  dest="read_afm",
                  default=True,
                  help=_("Don't read AFM file"))
    p.add_option ('','--noround',
                  action="store_false",
                  dest='round_to_int',
                  default=True,
                  help= ("Do not round coordinates of control points to integer values (use with --grid)"))
    p.add_option ('','--grid',
                  metavar='SCALE',
                  dest='grid_scale',
                  type='float',
                  default = 1.0,
                  help=_ ("Set reciprocal grid size in em units"))
    p.add_option ('-D','--define',
                  metavar="SYMBOL=VALUE",
                  dest="defs",
                  default=[],
                  action='append',help=_("Set the font info SYMBOL to VALUE"))
    
    global options
    (options, files) = p.parse_args ()

    if not files:
        sys.stderr.write ('Need argument on command line \n')
        p.print_help ()
        sys.exit (2)
        
    if options.warranty :
        warranty ()
        sys.exit (0)

    options.font_info = {}
    for d in options.defs:
        kv = d.split('=')
        if len (kv) == 1:
            options.font_info[kv] = 'true'
        elif len (kv) > 1:
            options.font_info[kv[0]] = '='.join (kv[1:])
            
    def comma_sepped_to_list (x):
        fs = [] 
        for f in x:
            fs += f.lower ().split (',')
        return fs
    
    options.formats = comma_sepped_to_list (options.formats)

    new_glyphs = []
    for r in options.glyphs:
        new_glyphs += r.split (',')
    options.glyphs = new_glyphs
    
    glyph_range = []
    for r in options.glyphs: 
        glyph_subrange = map (int, string.split (r, '-'))
        if len (glyph_subrange) == 2 and glyph_subrange[0] < glyph_subrange[1] + 1:
            glyph_range += range (glyph_subrange[0], glyph_subrange[1] + 1)
        else:
            glyph_range.append (glyph_subrange[0])

    options.glyphs = glyph_range
    
    options.trace_binary = ''
    if options.potrace:
        options.trace_binary = 'potrace'
    elif options.autotrace:
        options.trace_binary = 'autotrace'
    
    if options.formats == []:
        options.formats = ['pfa']



    global trace_command
    global path_to_type1_ops
    
    stat = os.system ('potrace --version > /dev/null 2>&1 ')
    if options.trace_binary != 'autotrace' and stat == 0:
        options.trace_binary = 'potrace'

        trace_command = potrace_command
        path_to_type1_ops = potrace_path_to_type1_ops
    elif options.trace_binary == 'potrace' and stat != 0:
        error (_ ("Could not run potrace; have you installed it?"))

    stat = os.system ('autotrace --version > /dev/null 2>&1 ')
    if options.trace_binary != 'potrace' and stat == 0:
        options.trace_binary = 'autotrace'
        trace_command = autotrace_command
        path_to_type1_ops = autotrace_path_to_type1_ops
    elif options.trace_binary == 'autotrace' and stat != 0:
        error (_ ("Could not run autotrace; have you installed it?"))

    if not options.trace_binary:
        error (_ ("No tracing program found.\nInstall potrace or autotrace."))
        
    return files


def derive_font_name (family, fullname):
    fullname = re.sub (family, '', fullname)
    family = re.sub (' ',  '', family)
    fullname = re.sub ('Oldstyle Figures', 'OsF', fullname)
    fullname = re.sub ('Small Caps', 'SC', fullname)
    fullname = re.sub ('[Mm]edium', '', fullname)
    fullname = re.sub ('[^A-Za-z0-9]', '', fullname)
    return '%s-%s' % (family, fullname)
    
def cm_guess_font_info (filename, fontinfo):
    # urg.
    filename = re.sub ("cm(.*)tt", r"cmtt\1", filename)
    m = re.search ("([0-9]+)$", filename)
    design_size = ''
    if m:
        design_size = int (m.group (1))
        fontinfo['DesignSize'] = design_size

    prefixes = [("cmtt", "Computer Modern Typewriter"),
          ("cmvtt", "Computer Modern Variable Width Typewriter"),
          ("cmss", "Computer Modern Sans"),
          ("cm", "Computer Modern")]

    family = ''
    for (k, v) in prefixes:
        if re.search (k, filename):
            family = v
            if k == 'cmtt':
                fontinfo['isFixedPitch'] = 'true'
            filename = re.sub (k, '', filename)
            break

    # shapes
    prefixes = [("r", "Roman"),
          ("mi", "Math italic"),
          ("u", "Unslanted italic"),
          ("sl", "Oblique"),
          ("csc", "Small Caps"),
          ("ex", "Math extension"),
          ("ti", "Text italic"),
          ("i", "Italic")]
    shape = ''
    for (k, v) in prefixes:
        if re.search (k, filename):
            shape = v
            filename = re.sub (k, '', filename)
            
    prefixes = [("b", "Bold"),
          ("d", "Demi bold")]
    weight = 'Regular'
    for (k, v) in prefixes:
        if re.search (k, filename):
            weight = v
            filename = re.sub (k, '', filename)

    prefixes = [("c", "Condensed"),
          ("x", "Extended")]
    stretch = ''
    for (k, v) in prefixes:
        if re.search (k, filename):
            stretch = v
            filename = re.sub (k, '', filename)
    
    fontinfo['ItalicAngle'] = 0
    if re.search ('[Ii]talic', shape) or re.search ('[Oo]blique', shape):
        a = -14
        if re.search ("Sans", family):
            a = -12

        fontinfo ["ItalicAngle"] = a

    fontinfo['Weight'] = weight
    fontinfo['FamilyName'] = family
    full  = '%s %s %s %s %dpt' \
               % (family, shape, weight, stretch, design_size)
    full = re.sub (" +", ' ', full)
    
    fontinfo['FullName'] = full
    fontinfo['FontName'] = derive_font_name (family, full)

    return fontinfo

def ec_guess_font_info (filename, fontinfo):
    design_size = 12
    m = re.search ("([0-9]+)$", filename)
    if m:
        design_size = int (m.group (1))
        fontinfo['DesignSize'] = design_size

    prefixes = [("ecss", "European Computer Modern Sans"),
          ("ectt", "European Computer Modern Typewriter"),
          ("ec", "European Computer Modern")]

    family = ''
    for (k, v) in prefixes:
        if re.search (k, filename):
            if k == 'ectt':
                fontinfo['isFixedPitch'] = 'true'
            family = v
            filename = re.sub (k, '', filename)
            break

    # shapes
    prefixes = [("r", "Roman"),
          ("mi", "Math italic"),
          ("u", "Unslanted italic"),
          ("sl", "Oblique"),
          ("cc", "Small caps"),
          ("ex", "Math extension"),
          ("ti", "Italic"),
          ("i", "Italic")]
    
    shape = ''
    for (k, v) in prefixes:
        if re.search (k, filename):
            shape = v
            filename = re.sub (k, '', filename)

    prefixes = [("b", "Bold"),
          ("d", "Demi bold")]
    weight = 'Regular'
    for (k, v) in prefixes:
        if re.search (k, filename):
            weight = v
            filename = re.sub (k, '', filename)

    prefixes = [("c", "Condensed"),
          ("x", "Extended")]
    stretch = ''
    for (k, v) in prefixes:
        if re.search (k, filename):
            stretch = v
            filename = re.sub (k, '', filename)
    
    fontinfo['ItalicAngle'] = 0
    if re.search ('[Ii]talic', shape) or re.search ('[Oo]blique', shape):
        a = -14
        if re.search ("Sans", family):
            a = -12

        fontinfo ["ItalicAngle"] = a

    fontinfo['Weight'] = weight
    fontinfo['FamilyName'] = family
    full  = '%s %s %s %s %dpt' \
               % (family, shape, weight, stretch, design_size)
    full = re.sub (" +", ' ', full)
    
    fontinfo['FontName'] = derive_font_name (family, full)
    fontinfo['FullName'] = full

    return fontinfo


def guess_fontinfo (filename):
    fi = {
        'FontName': filename,
        'FamilyName': filename,
        'Weight': 'Regular',
        'ItalicAngle': 0,
        'DesignSize' : 12,
        'isFixedPitch' : 'false',
        'FullName': filename,
       }

    if re.search ('^cm', filename):
        fi.update (cm_guess_font_info (filename, fi))
    elif re.search ("^ec", filename):
        fi.update (ec_guess_font_info (filename, fi))
    elif options.read_afm:
        global afmfile
        if not afmfile:
            afmfile = find_file (filename + '.afm')

        if afmfile:
            afmfile = os.path.abspath (afmfile)
            afm_struct = afm.read_afm_file (afmfile)
            fi.update (afm_struct.__dict__)
        return fi
    else:
        sys.stderr.write ("Warning: no extra font information for this font.\n"
                 + "Consider writing a XX_guess_font_info() routine.\n")

    return fi

def do_file (filename):        
    encoding_file = options.encoding_file
    global include_dirs
    include_dirs = options.include_dirs
    include_dirs.append (origdir)

    basename = strip_extension (filename, '.mf')
    progress (_ ("Font `%s'..." % basename))
    progress ('\n')

    ## setup encoding
    if encoding_file and not os.path.exists (encoding_file):
        encoding_file = find_file (encoding_file)
    elif encoding_file:
        encoding_file = os.path.abspath (encoding_file)

    ## setup TFM
    if options.tfm_file:
        options.tfm_file = os.path.abspath (options.tfm_file)
    else:
        tfm_try = find_file (basename + '.tfm')
        if tfm_try:
            options.tfm_file = tfm_try

    if not os.environ.has_key ("MFINPUTS"):
         os.environ["MFINPUTS"] = os.getcwd () + ":"

    ## must change dir before calling mktextfm.
    if options.keep_temp_dir:
        def nop():
            pass
        setup_temp (os.path.join (os.getcwd (), program_name + '.dir'))
        temp_dir.clean = nop
    else:
        setup_temp (None)
        
    if options.verbose:
        progress ('Temporary directory is `%s\'\n' % temp_dir)
    
    if not options.tfm_file:
        options.tfm_file = popen ("mktextfm %s 2>/dev/null" % shell_escape_filename (basename)).read ()
        if options.tfm_file:
            options.tfm_file = options.tfm_file.strip ()
            options.tfm_file = os.path.abspath (options.tfm_file)

    if not options.tfm_file:
        error (_ ("Can not find a TFM file to match `%s'") % basename)

    metric = tfm.read_tfm_file (options.tfm_file)

    fontinfo = guess_fontinfo (basename)
    fontinfo.update (options.font_info)

    if not encoding_file:
        codingfile = 'tex256.enc'
        if not coding_dict.has_key (metric.coding):
            sys.stderr.write ("Unknown encoding `%s'; assuming tex256.\n" % metric.coding)
        else:
            codingfile = coding_dict[metric.coding]

        encoding_file = find_file (codingfile)
        if not encoding_file:
            error (_ ("can't find file `%s'" % codingfile))

    (enc_name, encoding) = read_encoding (encoding_file)

    if not len (options.glyphs):
        options.glyphs = range (0, len (encoding))

    if not options.gffile:
        # run mf
        base = gen_pixel_font (basename, metric, options.magnification)
        options.gffile = base + 'gf'
    else:
        options.gffile = find_file (options.gffile)

    # the heart of the program:
    trace_font (basename, options.gffile, metric, options.glyphs, encoding,
          options.magnification, fontinfo)
        
    make_outputs (basename, options.formats, encoding)
    for format in options.formats:
        shutil.copy2 (basename + '.' + format, origdir)

    os.chdir (origdir)





afmfile = ''
backend_options = getenv ('MFTRACE_BACKEND_OPTIONS', '')
def main ():
    files = parse_command_line ()
    identify (sys.stderr)
    
    for filename in files:
        do_file (filename)
    sys.exit (exit_value)

if __name__ =='__main__':
    main()
