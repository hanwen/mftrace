#!@PYTHON@    

import string
import os
import getopt
import sys
import re
import tempfile
import shutil

prefix='@prefix@'
exec_prefix='@exec_prefix@'
datadir='@datadir@'
libdir="@libdir@"



def interpolate (str):
	str = string.replace (str, '{', '(')
        str = string.replace (str, '}', ')s')
        str = string.replace (str, '$', '%')        
        return str

if prefix <> '@' + 'prefix@':
        exec_prefix = interpolate (exec_prefix) % vars()
        datadir = os.path.join (interpolate (datadir) % vars() , 'mftrace')
        libdir = interpolate (libdir) % vars()

# run from textrace-source dir.

simplify_p = 0
verbose_p = 0
pfa_p = 0
pfb_p = 0
afm_p = 0
dos_kpath_p = 0
ttf_p = 0
keep_trying_p = 0
# should be installed.
autotrace_bin = 'autotrace'
magnification = 1000.0
program_name = 'mftrace'
temp_dir = os.path.join (os.getcwd (), program_name + '.dir' )
gf_fontname = ''

keep_temp_dir_p = 0
program_version='@VERSION@'
origdir= os.getcwd ()

coding_dict = {
	'Extended TeX Font Encoding - Latin' : 'tex256.enc',
	'TeX text': 'tex256.enc',
	'feta braces': 'feta-braces0.enc',
	'feta number': 'feta-nummer10.enc',
	'feta music': 'feta20.enc',
	'parmesan music' : 'parmesan20.enc',
	}


if datadir == '@' + "datadir" + "@":
	datadir = os.getcwd ()

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

def identify (port):
	port.write ('%s %s\n' % (program_name, program_version))

def warranty ():
	identify (sys.stdout)
	sys.stdout.write ('\n')
	sys.stdout.write (_ ('Copyright (c) %s by' % ' 2001--2002'))
	sys.stdout.write ('\n')
	sys.stdout.write ('  Han-Wen Nienhuys')
	sys.stdout.write ('  Jan Nieuwenhuizen')
	sys.stdout.write ('\n')
	sys.stdout.write (_ (r'''
Distributed under terms of the GNU General Public License. It comes with
NO WARRANTY.'''))
	sys.stdout.write ('\n')

def progress (s):
	errorport.write (s)

def warning (s):
	errorport.write (_ ("warning: ") + s)
		
def error (s):


	'''Report the error S.  Exit by raising an exception. Please
	do not abuse by trying to catch this error. If you do not want
	a stack trace, write to the output directly.

	RETURN VALUE

	None
	
	'''
	
	errorport.write (_ ("error: ") + s + '\n')
	raise _ ("Exiting ... ")

def getopt_args (opts):
	'''Construct arguments (LONG, SHORT) for getopt from  list of options.'''
	short = ''
	long = []
	for o in opts:
		if o[1]:
			short = short + o[1]
			if o[0]:
				short = short + ':'
		if o[2]:
			l = o[2]
			if o[0]:
				l = l + '='
			long.append (l)
	return (short, long)

def option_help_str (o):
	'''Transform one option description (4-tuple ) into neatly formatted string'''
	sh = '  '	
	if o[1]:
		sh = '-%s' % o[1]

	sep = ' '
	if o[1] and o[2]:
		sep = ','
		
	long = ''
	if o[2]:
		long= '--%s' % o[2]

	arg = ''
	if o[0]:
		if o[2]:
			arg = '='
		arg = arg + o[0]
	return '  ' + sh + sep + long + arg


def options_help_str (opts):
	'''Convert a list of options into a neatly formatted string'''
	w = 0
	strs =[]
	helps = []

	for o in opts:
		s = option_help_str (o)
		strs.append ((s, o[3]))
		if len (s) > w:
			w = len (s)

	str = ''
	for s in strs:
		str = str + '%s%s%s\n' % (s[0], ' ' * (w - len(s[0])  + 3), s[1])
	return str

def help ():
	ls = [(_ ("Usage: %s [OPTION]... FILE...") % program_name),
		('\n\n'),
		(help_summary),
		('\n\n'),
		(_ ("Options:")),
		('\n'),
		(options_help_str (option_definitions)),
		('\n\n'),
		(_ ("Report bugs to %s") % 'hanwen@cs.uu.nl'),
		('\n')]
	map (sys.stdout.write, ls)
	
def setup_temp ():
	"""
	Create a temporary directory, and return its name. 
	"""
	global temp_dir
	if not keep_temp_dir_p:
		temp_dir = tempfile.mktemp (program_name)
	try:
		os.mkdir (temp_dir, 0700)
	except OSError:
		pass

	return temp_dir

def popen (cmd, mode = 'r', ignore_error = 0):
	if verbose_p:
		progress (_ ("Opening pipe  `%s\'") % cmd)
	pipe = os.popen (cmd, mode)
	if verbose_p:
		progress ('\n')
	return pipe

def system (cmd, ignore_error = 0):
	"""Run CMD. If IGNORE_ERROR is set, don't complain when CMD returns non zero.

	RETURN VALUE

	Exit status of CMD
	"""
	
	if verbose_p:
		progress (_ ("Invoking `%s\'\n") % cmd)
	st = os.system (cmd)
	if st:
		name = re.match ('[ \t]*([^ \t]*)', cmd).group (1)
		msg = name + ': ' + _ ("command exited with value %d") % st
		if ignore_error:
			warning (msg + ' ' + _ ("(ignored)") + ' ')
		else:
			error (msg)
	if verbose_p:
		progress ('\n')
	return st


def cleanup_temp ():
	if not keep_temp_dir_p:
		if verbose_p:
			progress (_ ("Cleaning %s...") % temp_dir)
		shutil.rmtree (temp_dir)


def strip_extension (f, ext):
	(p, e) = os.path.splitext (f)
	if e == ext:
		e = ''
	return p + e


################################################################
# END Library


help_summary = _ ("""Generate Type1 or TrueType font from Metafont source.

Example:

   mftrace cmr10""")

option_definitions = [
	('', 'h', 'help', _ ("This help")),
	('', 'k', 'keep', _ ("Keep all output in directory %s.dir") % program_name),
	('MAG', '', 'magnification', _("Set magnification for MF to MAG (default: 1000).")),
	('', 'V', 'verbose', _ ("Verbose")),
	('', 'v', 'version', _ ("Print version number")),
	('', 'a', 'pfa', _ ("Generate PFA file (default)")),
	('','', 'afm',  _("Generate AFM file (implies --simplify)")),
	('', 'b', 'pfb', _ ("Generate PFB file")),
	('', '', 'simplify', _("Simplify using pfaedit")),
	('FILE', '', 'gffile', _("Use gf FILE instead of running Metafont")),
	('DIR', 'I', 'include', _("Add to path for searching files")),	
	('LIST','', 'glyphs', _('Process only these glyphs. LIST is comma separated')),
	('FILE', '', 'tfmfile' , _("Use FILE for the TFM file")),
	('FILE', 'o', 'output-base', _("Set output file name")), 
	('ENC', 'e', 'encoding', _("Use encoding file ENC")),
	('', 't', 'truetype', _("Generate TrueType file (requires pfaedit).")),
	('', '', 'keep-trying', _("Don't stop if autotrace fails")),
	('', 'w', 'warranty', _ ("show warranty and copyright")),
	('', '', 'dos-kpath', _ ("try to use Miktex kpsewhich")),
	]



include_dirs = [origdir]
def find_file (nm):
	for d in include_dirs:
		p = os.path.join (d, nm)
		try:
			f = open (p)
			return p
		except IOError:
			pass
	
	p = popen ('kpsewhich %s' % nm).read ()[:-1]

	if dos_kpath_p:
		orig = p 
		def func(m):
			return string.lower (m.group(1))
		p = string.lower (p)
		p = re.sub ('^([a-z]):', '/cygdrive/\\1', p)
		p = re.sub ('\\\\', '/', p)
		sys.stderr.write ("Got `%s' from kpsewhich, using `%s'\n" % (orig, p))
	return p


################################################################
# TRACING.
################################################################

def autotrace_command (fi, fn, opts):
	opts = " " + opts + " --output-format=eps --input-format=pbm "
	cmd = autotrace_bin + opts + " --output-file=char.eps -filter-iterations %d %s  " % (fi,fn)
	return cmd

def run_autotrace  (fi,fn,opts):
	stat = system (autotrace_command (fi,fn,opts), 1)
	return stat

def do_autotrace_best_fi (fn, opts):

	""" Run autotrace, and find the
	best filter-iterations value.
	"""
	fi = 8
	while fi >= 0:
		if run_autotrace (fi, fn, opts) ==0:
			return 0

		fi  = fi -1  

	return 1

def blank_pbm (filename):
	"""
	Kill the contents of a PBM: write 0xFF to the PBM.
	"""
	f = open (filename)
	l = f.readline ()
	length = len (f.read())

	f.close ()
	
	open (filename, 'w').write ('%s\n%s' % (l,'\377' * length))

def do_autotrace_one (pbmfile, id):
	"""
	Run autotrace, first with -background-color, then without.
	"""
	
	status = run_autotrace (9, pbmfile , '-background-color FFFFFF')
	if status == 2:
		sys.stderr.write ("\nUser interrupt. Exiting\n")
		sys.exit(2)
	if status <> 0:
		error_file = os.path.join (origdir, 'autotrace-bug-%s.pbm' % id)
		shutil.copy2 (pbmfile, error_file)
		msg = """Autotrace failed on bitmap. Bitmap left in `%s\'
Failed command was:

	%s
	
Please submit a bugreport to autotrace development.""" % (error_file,
							  autotrace_command (9, error_file, '-background-color FFFFFF'))

		if keep_trying_p:
			warning (msg)
			sys.stderr.write ("\nContinuing trace...\n")
		else:
			msg = msg + '\nRun mftrace with --keep-trying to produce a font anyway\n'
			error (msg)
	else:
		return 1

	status = do_autotrace_best_fi (pbmfile, '-background-color FFFFFF')
	if status <> 0:
		warning ("Failing even  -filter-iterations=0. Skipping character.\n")
		return 0
	else:
		return 1


	
def make_pbm (filename, outname, char_number):
	""" Extract bitmap from the PK file FILENAME (absolute) using `gf2pbm'.
	Return FALSE if the glyph is not valid. 
	"""
	
	command = "gf2pbm -n %d -o %s %s" %(char_number, outname, filename)
	status = system (command, ignore_error = 1)
	
	return  (status == 0)

def read_encoding (file):
	sys.stderr.write(_("Using encoding file: `%s'\n") % file)
	
	str = open (file).read ()
	str = re.sub ("%.*", '', str)
	str = re.sub ("[\n\t \f]+", ' ', str)
	m = re.search ('/([^ ]+) \[([^\]]+)\] def', str)
	if not m:
		raise 'Encoding file invalid.'
	
	name = m.group(1)	
	cod =m.group( 2)
	cod = re.sub('[ /]+', ' ',cod)
	cods = string.split (cod)

	return (name, cods)



def zip_to_pairs(as):
	r = []
	while as :
		r.append((as[0],  as[1]))
		as = as[2:]
	return r

def unzip_pairs (tups):
	l = []
	while tups:
		l = l + list (tups[0])
		tups = tups[1:]
	return l

def autotrace_path_to_type1_ops (at_file, bitmap_metrics, tfm_wid):
	inv_scale = 1000.0/magnification
	
	(size_y, size_x, off_x,off_y)= map(lambda m, s=inv_scale : m * s, bitmap_metrics)
	ls = open (at_file).readlines ()
	bbox =  (10000,10000,-10000,-10000)

	while ls and ls[0] <> '*u\n':
		ls = ls[1:]

	if ls == []:
		return (bbox, '')

	ls = ls[1:]

	commands = []
	


	while ls[0] <> '*U\n':
		l = ls[0]
		ls = ls[1:]

		toks = string.split (l)

		if len(toks) < 1:
			continue
		cmd= toks[-1]
		args = map (lambda m, s=inv_scale : s * string.atof(m), toks[:-1])
		args = zip_to_pairs (map (round, args))
		commands.append ((cmd,args))


	expand = {
		'l': 'rlineto',
		'm': 'rmoveto',
		'c': 'rrcurveto',
		'sbw' : 'sbw',
		'f': 'closepath' ,
		}

	cx = 0
	cy = size_y - off_y -1

	# t1asm seems to fuck up when using sbw. Oh well. 
	t1_outline =  '  %d %d hsbw\n' % (- off_x, tfm_wid)
	bbox =  (10000,10000,-10000,-10000)

	for (c,args) in commands[0:]:

		na = []
		for a in args:
			(nx, ny) = a
			if c == 'l' or c == 'c':
				bbox = update_bbox_with_point (bbox, a)
				
			na.append( (nx -cx, ny -cy) )
			(cx, cy) = (nx, ny)

		a = na
		c = expand[c]
		a = map (lambda x: '%d' % int (x),  unzip_pairs (a))

		t1_outline = t1_outline + '  %s %s\n' % (string.join (a),c)

	t1_outline = t1_outline + ' endchar '
	t1_outline = '{\n %s } |- \n' % t1_outline
	
	return (bbox, t1_outline)
	
def read_gf_dims (name, c):
	str = popen ('gf2pbm -n %d -s %s' % (c, name)).read ()
	m = re.search ('size: ([0-9]+)+x([0-9]+), offset: \(([0-9-]+),([0-9-]+)\)', str)

	return tuple (map (string.atoi ,m.groups ()))
		       

	
def autotrace_font (fontname, gf_file, metric, glyphs, encoding, magnification):
	t1os = []
	font_bbox =  (10000,10000,-10000,-10000)

	progress (_ ("Tracing bitmaps... "))

	eps_lines = []

	# for single glyph testing.
	# glyphs = []
	for a in glyphs:
		valid = metric.has_char (a)
		if not valid:
			continue

		valid = make_pbm (gf_file, 'char.pbm', a)
		if not valid:
			continue

		(w,h, xo, yo) = read_gf_dims (gf_file, a)
			
		if not verbose_p:
			sys.stderr.write('[%d' % a)
			sys.stderr.flush()

		# this wants the id, not the filename.
		success = do_autotrace_one ("char.pbm", '%s-%d' % (gf_fontname, a))
		if not success :
			sys.stderr.write ("(skipping character)]")
			sys.stderr.flush ()			
			continue 
		
		if not verbose_p:
			sys.stderr.write(']')
			sys.stderr.flush()
		metric_width = metric.get_char (a).width
		tw = int (round (metric_width / metric.design_size * 1000))
		(bbox, t1o)  = autotrace_path_to_type1_ops ("char.eps",
						    (h, w, xo, yo),
						    tw)

		if t1o == '' :
			continue
		
		font_bbox = update_bbox_with_bbox (font_bbox, bbox)

		t1os.append ('/%s %s ' % (encoding[a] , t1o ))

	progress ('\n')
	
	if pfa_p or ttf_p:
		to_type1 (t1os, font_bbox, fontname, encoding, magnification, 1)
	if ttf_p:
		shutil.copy2 (fontname + '.pfa', fontname + '.pfx')
	if pfb_p:
		to_type1 (t1os, font_bbox, fontname, encoding,
			  magnification, 0)


def ps_encode_encoding (encoding):
	str = ' %d array\n0 1 %d {1 index exch /.notdef put} for\n' % (len (encoding), len(encoding)-1)

	
	for i in range (0, len (encoding)):
		str = str  + 'dup %d /%s put\n' % (i, encoding[i])

	return str
	
 

def to_type1 (outlines, bbox, fontname, encoding, magnification, pfa):
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
/UniqueID %(UniqueID)s def
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
/UniqueID %(UniqueID)d def
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
## apparently, some fonts end the  file with cleartomark. Don't know why.
	
	vars = { 
		'FontName': '%s' % fontinfo['FontName'],
		'VVV': '001',
		'WWW': '001',
		'Notice': 'Generated from MetaFont bitmap by mftrace %s, http://www.cs.uu.nl/~hanwen/mftrace/ ' % program_version,
		'FullName': '%s' % fontinfo['FullName'],
		'FamilyName': '%s' % fontinfo['FamilyName'],
		'Weight': '%s' % fontinfo['Weight'],
		'ItalicAngle': '0',
		'isFixedPitch': 'false',
		'UnderlinePosition': '-100',
		'UnderlineThickness': '50',
		'UniqueID':  0 ,
		'xrevscale': 1.0/1000.0,
		'yrevscale': 1.0/1000.0,
		'llx' : bbox[0],
		'lly' : bbox[1],
		'urx' : bbox[2],
		'ury' : bbox[3], 
		'Encoding' : ps_encode_encoding (encoding),
		
		# need one extra entry for .notdef
		'CharStringsLen': len(outlines) + 1,
		'CharStrings': string.join (outlines),
		'CharBBox': '0 0 0 0'
	}

	open ('mftrace.t1asm','w').write (template  % vars)

	opt = ''
	
	if pfa:
		opt = '--pfa'
		outname = fontname + '.pfa'
	else:
		outname = fontname + '.pfb'
		
	progress (_ ("Assembling font to `%s'... ") % outname)
	system ('t1asm %s mftrace.t1asm %s' % (opt, outname))
	progress ('\n')
	
def update_bbox_with_point (bbox, pt):
	(llx,lly,urx,ury) = bbox
	llx = min(pt[0], llx)
	lly = min(pt[1], lly)
	urx = max(pt[0], urx)
	ury = max(pt[1], ury)

	return 	(llx,lly,urx,ury)

def update_bbox_with_bbox (bb, dims):
	(llx,lly,urx,ury) = bb
	llx = min(llx, dims[0])
	lly = min(lly, dims[1])
	urx = max(urx, dims[2])
	ury = max(ury, dims[3])
		
	return (llx,lly,urx,ury) 

def check_pfaedit_scripting ():
	stat = system ("pfaedit -usage > pfv 2>&1", ignore_error = 1)
	if stat <> 0:
		warning ("Command `pfaedit -usage' failed. Cannot simplify or convert to TTF.")
		return 0
		
	if re.search ("-script", open ('pfv').read()) == None:
		warning ("pfaedit does not support -script. Install 020215 or later.\nCannot simplify or convert to TTF.\n")
		return 0
	return 1

def cleanup_font (file):
        """
        run pfaedit to simplify and auto-hint the PFX
        """

	if not check_pfaedit_scripting() :
		return 0

	# not used?
	shutil.copy2 (file, "before-pfaedit.pfx")
	
	progress (_ ("Simplifying font... "))
	
	open ('simplify.pe', 'w').write ('''#!/usr/bin/env pfaedit
Open ($1);
MergeKern($2);
SelectAll ();
Simplify ();
AutoHint ();
Generate ("%s");
Quit (0);
''' % file)
	system ("pfaedit -script simplify.pe %s %s" % (file, tfmfile))
	progress ('\n')

def make_ttf (fontname):
        """
        run pfaedit to convert to TTF.
        """

	if not check_pfaedit_scripting() :
		return 0

	# not used?
	shutil.copy2 (fontname + '.pfx', "before-pfaedit.pfx")
	
	open ('to-ttf.pe', 'w').write ('''#!/usr/bin/env pfaedit
Open ($1);
MergeKern($2);
SelectAll ();
Simplify ();
AutoHint ();
Generate ("%s");
Quit (0);
''' % (filename + '.ttf'))
	
	system ("pfaedit -script to-ttf.pe %s %s" % ((filename + '.pfx'), tfmfile))
	

def getenv (var, default):
	if os.environ.has_key (var):
		return os.environ[var]
	else:
		return default
	
	
def gen_pixel_font (filename, metric, magnification):
	"""
	Generate a GF file  for FILENAME, such that `magnification'*mfscale
	(default 1000 * 1.0) points fit on the designsize.
	"""
	base_dpi = 600

	size = metric.design_size
	
	size_points = size * 1/72.27 * base_dpi

	mag = magnification / size_points

	prod = mag * base_dpi
	try:
		f = open ('%s.%dgf' % (filename, prod))
	except IOError:
		os.environ['KPSE_DOT'] = '%s:' % origdir
		os.environ['MFINPUTS'] =  '%s:%s' % (origdir,getenv('MFINPUTS',''))
		os.environ['TFMFONTS'] =  '%s:%s' % (origdir,getenv('TFMINPUTS',''))

		progress (_ ("Running Metafont..."))

		cmdstr = r"mf '\mode:=ljfour; mag:=%f; nonstopmode; input %s'" %  (mag,filename)
		if not verbose_p:
			cmdstr = cmdstr +  ' 1>/dev/null 2>/dev/null'
		st = system (cmdstr, ignore_error = 1)
		progress ('\n')

		
		log = open ('%s.log' % filename).read ()

		if st:
			sys.stderr.write ('\n\nMetafont failed. Excerpt from the log file: \n\n*****')
			m = re.search ("\n!", log)
			start = m.start (0)
			short_log = log[start:start+200]
			sys.stderr.write (short_log)
			sys.stderr.write ('\n*****\n')
			if re.search ('Arithmetic overflow', log):
				sys.stderr.write ("""

Apparently, some numbers overflowed. Try using --magnification with a
lower number.  (Current magnification: %d)
""" % magnification)

			sys.exit (1)
		m = re.search('Output written on %s.([0-9]+)gf' % re.escape (filename), log)
		prod = string.atoi (m.group (1))
	
	return "%s.%d" % (filename , prod)

(sh, long) = getopt_args (option_definitions)
try:
	(options, files) = getopt.getopt(sys.argv[1:], sh, long)
except getopt.error, s:
	errorport.write ('\n')
	errorport.write (_ ("error: ") + _ ("getopt says: `%s\'" % s))
	errorport.write ('\n')
	errorport.write ('\n')
	help ()
	sys.exit (2)

fontinfo = {}
afmfile = ''
tfmfile = ''
outname = ''
gf_fontname = ''
encoding_file_override = '' 
glyph_range=[]
for (o,a) in options:
	if 0:
		pass
	elif o == '--help' or o == '-h':
		help ()
		sys.exit (0)
	elif o == '--keep' or o == '-k':
		keep_temp_dir_p = 1
	elif o == '--verbose' or o == '-V':
		verbose_p = 1
	elif o == '--keep-trying':
		keep_trying_p = 1
	elif o == '--version' or o == '-v':
		identify (sys.stdout)
		sys.exit (0)
	elif o == '--warranty' or o == '-w':
		warranty ()
		sys.exit (0)
	elif o == '--encoding' or o == '-e':
		encoding_file_override = a
	elif o == '--gffile':
		gf_fontname = a
	elif o == '--glyphs':
		glyph_range = map (string.atoi, string.split(a, ','))
	elif o == '--output-base' or o == '-o':
		outname = a
	elif o == '--tfmfile' :
		tfmfile = a
	elif o == '--pfa' or o == '-a':
		pfa_p = 1
	elif o == '--truetype' or o == '-t':
		ttf_p =1 
	elif o == '--dos-kpath':
		dos_kpath_p = 1
	elif o == '--pfb' or o == '-b':
		pfb_p = 1
	elif o== '--include' or o == '-I':
		include_dirs.append (a)
	elif o == '--simplify':
		simplify_p = 1
	elif o == '--magnification':
		magnification = string.atof(a)
	elif o == '--afm':
		afm_p = 1
		simplify_p = 1
		
	else:
		raise 'Ugh -- forgot to implement option %s. :)' % o

identify (sys.stderr)
if not pfa_p and not pfb_p and not ttf_p:
	pfa_p = 1
	
if not files:
	try:
		error("No input files specified.")
	except:
		pass
	help ()
	sys.exit(2)


class Font_info:
	def set_defaults (self, name):
		self.FontName = name
		self.FullName = name
		self.EncodingScheme = 'AdobeStandard'

		# FontName is usually: <FamilyName>-<Weight>;
		# if possible, split off last section.
		s = string.join (string.split (name, '-')[:-1], '-')
		if s:
			self.FamilyName = s
		else:
			self.FamilyName = name

		self.Weight = 'Regular'
	
	def __init__ (self, x):
		if type (x) == type ("hallo"):
			self.set_defaults (x)
		elif type (x) == type ({}):
			self.set_defaults (x['FontName'])
			for k in x.keys ():
				self.__dict__[k] = x[k]

	def __getitem__ (self, key):
		return self.__dict__[key]

for filename in files:
	encoding_file = encoding_file_override

	basename = strip_extension(filename, '.mf')
	progress (_ ("Font `%s'..." % basename))
	progress ('\n')
	
	if not tfmfile:
		tfmfile = find_file (basename + '.tfm')

	if not tfmfile:
		tfmfile =  popen ("mktextfm %s 2>/dev/null" % basename).read ()
		if tfmfile:
			tfmfile = tfmfile[:-1]

	if not tfmfile:
		error (_("Can not find a TFM file to match `%s'") % basename) 

	tfmfile = os.path.abspath(tfmfile)
	metric = tfm.read_tfm_file (tfmfile)

	if not afmfile:
		afmfile = find_file (basename + '.afm')

	if afmfile:
		afmfile = os.path.abspath (afmfile)
		afm = afm.read_afm_file (afmfile)
		fontinfo = Font_info (afm.__dict__)
	else:
		fontinfo = Font_info (basename)
		
	if encoding_file and not os.path.exists (encoding_file):
		encoding_file = find_file (encoding_file)


	if not encoding_file:
		codingfile = 'tex256.enc'
		if not coding_dict.has_key (metric.coding):
			sys.stderr.write ("Unknown encoding `%s'; assuming tex256.\n" % metric.coding)
		else:
			codingfile = coding_dict[metric.coding]

		encoding_file = find_file (codingfile)
		if not encoding_file:
			error (_("can't find file `%s'" % codingfile))

	(enc_name, encoding) = read_encoding (encoding_file)

	if not len(glyph_range):
		glyph_range = range(0,len(encoding))

	temp_dir =setup_temp ()

	if verbose_p:
		progress ('Temporary directory is `%s\' ' % temp_dir)
	os.chdir (temp_dir)

        if not gf_fontname:
        	# run mf
		base = gen_pixel_font (basename, metric, magnification)
		gf_fontname = base + 'gf'
	else:
		gf_fontname = find_file (gf_fontname)

	# the heart of the program:
	autotrace_font (basename, gf_fontname, metric, glyph_range, encoding, magnification)

	if pfa_p:
		if simplify_p:
			cleanup_font (basename + '.pfa')
		shutil.copy2 (basename + '.pfa', origdir)
	if pfb_p:
		if simplify_p:
			cleanup_font (basename + '.pfb')
		shutil.copy2 (basename + '.pfb', origdir)


	if afm_p and simplify_p:
		shutil.copy2 (basename + '.afm', origdir)
		
	if ttf_p:
		if simplify_p:
			cleanup_font (basename + '.pfa')
		make_ttf (basename)
		shutil.copy2 (basename + '.ttf', origdir)

	os.chdir (origdir)
	cleanup_temp ()
