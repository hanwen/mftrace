/* -*-c-indentation-style:"bsd"-*- */
/*========================================================================*\

Copyright (c) 1990-1999  Paul Vojta

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to
deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
PAUL VOJTA BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

\*========================================================================*/

/*
 *	GF font reading routines.
 *	Public routines are read_GF_index and read_GF_char.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>		/* getopt. */
#include <strings.h>

#include "config.h"

#define	ARGS(x)	x

#define DBG_PK 0

#define	WIDENINT	(int)
typedef	unsigned int	wide_ubyte;
typedef	int		wide_bool;
typedef	unsigned long	Pixel;
typedef	unsigned int	Dimension;


#define one(fp)		((unsigned char) getc(fp))
#define sone(fp)	((long) one(fp))
#define two(fp)		num (fp, 2)
#define stwo(fp)	snum(fp, 2)
#define four(fp)	num (fp, 4)
#define sfour(fp)	snum(fp, 4)
typedef	unsigned char	ubyte;

struct font;
typedef	void (*read_char_proc) ARGS((struct font *, wide_ubyte));
typedef	long	(*set_char_proc) ARGS((wide_ubyte));

#define BMTYPE int
#define	GF_PRE		247
#define	GF_ID		131
#define	GF_MAGIC	(GF_PRE << 8) + GF_ID

#define	BMUNIT			unsigned BMTYPE

/*
  (can't use sizeof.
 */
#define BMBYTES 4 
#define	BMBITS			(8 * BMBYTES)
extern	BMUNIT	bit_masks[BMBITS + 1];
#define	ADD(a, b)	((BMUNIT *) (((char *) a) + b))
#define	SUB(a, b)	((BMUNIT *) (((char *) a) - b))



#if (BMBYTES == 1)
BMUNIT	bit_masks[9] = {
	0x0,	0x1,	0x3,	0x7,
	0xf,	0x1f,	0x3f,	0x7f,
	0xff
};
#else
#if (BMBYTES == 2)
BMUNIT	bit_masks[17] = {
	0x0,	0x1,	0x3,	0x7,
	0xf,	0x1f,	0x3f,	0x7f,
	0xff,	0x1ff,	0x3ff,	0x7ff,
	0xfff,	0x1fff,	0x3fff,	0x7fff,
	0xffff
};
#else	/* BMBYTES == 4 */
BMUNIT	bit_masks[33] = {
	0x0,		0x1,		0x3,		0x7,
	0xf,		0x1f,		0x3f,		0x7f,
	0xff,		0x1ff,		0x3ff,		0x7ff,
	0xfff,		0x1fff,		0x3fff,		0x7fff,
	0xffff,		0x1ffff,	0x3ffff,	0x7ffff,
	0xfffff,	0x1fffff,	0x3fffff,	0x7fffff,
	0xffffff,	0x1ffffff,	0x3ffffff,	0x7ffffff,
	0xfffffff,	0x1fffffff,	0x3fffffff,	0x7fffffff,
	0xffffffff
};
#endif
#endif

typedef enum {false,true}bool;
bool debug;

struct font {
	char *fontname;			/* name of font */
	float fsize;			/* size information (dots per inch) */
	int magstepval;			/* magstep number * two, or NOMAGSTP */
	FILE *file;			/* open font file or NULL */
	char *filename;			/* name of font file */
	long checksum;			/* checksum */
	unsigned short timestamp;	/* for LRU management of fonts */
	ubyte flags;			/* flags byte (see values below) */
	ubyte maxchar;			/* largest character code */
	double dimconv;			/* size conversion factor */
		/* these fields are used by (loaded) raster fonts */
	read_char_proc read_char;	/* function to read bitmap */
	struct glyph *glyph;
		/* these fields are used by (loaded) virtual fonts */
	struct font **vf_table;		/* list of fonts used by this vf */
	struct tn *vf_chain;		/* ditto, if TeXnumber >= VFTABLELEN */
	struct font *first_font;	/* first font defined */
	struct macro *macro;
		/* I suppose the above could be put into a union, but we */
		/* wouldn't save all that much space. */
};



/*
 * Bitmap structure for raster ops.
 */
struct bitmap {
	unsigned short	w, h;		/* width and height in pixels */
	short		bytes_wide;	/* scan-line width in bytes */
	char		*bits;		/* pointer to the bits */
};

/*
 * Per-character information.
 * There is one of these for each character in a font (raster fonts only).
 * All fields are filled in at font definition time,
 * except for the bitmap, which is "faulted in"
 * when the character is first referenced.
 */
struct glyph {
	long addr;		/* address of bitmap in font file */
	long dvi_adv;		/* DVI units to move reference point */
	short x, y;		/* x and y offset in pixels */
	struct bitmap bitmap;	/* bitmap for character */
	short x2, y2;		/* x and y offset in pixels (shrunken bitmap) */
#ifdef	GREY
	XImage *image2;
	char *pixmap2;
	char *pixmap2_t;
#endif
	struct bitmap bitmap2;	/* shrunken bitmap for character */
};

#define	PAINT_0		0
#define	PAINT1		64
#define	PAINT2		65
#define	PAINT3		66
#define	BOC		67
#define	BOC1		68
#define	EOC		69
#define	SKIP0		70
#define	SKIP1		71
#define	SKIP2		72
#define	SKIP3		73
#define	NEW_ROW_0	74
#define	NEW_ROW_MAX	238
#define	XXX1		239
#define	XXX2		240
#define	XXX3		241
#define	XXX4		242
#define	YYY		243
#define	NO_OP		244
#define	CHAR_LOC	245
#define	CHAR_LOC0	246
#define	PRE		247
#define	POST		248
#define	POST_POST	249

#define	GF_ID_BYTE	131
#define	TRAILER		223		/* Trailing bytes at end of file */

static	FILE	*GF_file;


static	void
expect(	ubyte ch)
{
	ubyte ch1 = one(GF_file);

	if (ch1 != ch)
	  {
	  fprintf(stderr, "Bad GF file:  %d expected, %d received.", ch, ch1);
	  exit (2);
	  }
}

static	void
too_many_bits(	ubyte ch)
{
	fprintf(stderr,"Too many bits found when loading character %d", ch);
	exit (2);
}


/*
 *
 *      Read size bytes from the FILE fp, constructing them into a
 *      signed/unsigned integer.
 *
 */

unsigned long
num(	FILE	*fp,	int	size)
{
	long	x	= 0;

	while (size--) x = (x << 8) | one(fp);
	return x;
}

long
snum(	FILE	*fp,	int	size)
{
	long	x;

	x = (signed char) getc(fp);

	while (--size) x = (x << 8) | one(fp);
	return x;
}

	ubyte		maxchar;

void
realloc_font(struct font *fontp, wide_ubyte	newsize)
{
	struct glyph *glyphp;

	glyphp = fontp->glyph = (struct glyph*)realloc(fontp->glyph,
	    (unsigned int) (newsize + 1) * sizeof(struct glyph));
	if (newsize > fontp->maxchar)
	    bzero((char *) (glyphp + fontp->maxchar + 1),
		(int) (newsize - fontp->maxchar) * sizeof(struct glyph));
	maxchar = fontp->maxchar = newsize;
}

#define ROUNDUP(x,y) (((x)+(y)-1)/(y))
void *
xmalloc(	unsigned	size)
{
	void	*mem	= malloc(size);

	if (mem == NULL)
	  {
	  fprintf(stderr,"! Out of memory (allocating %u bytes).\n", size);
	  exit (2);
	  }
	return mem;
}

void
alloc_bitmap(	struct bitmap	*bitmap)
{
	unsigned int	size;

	/* width must be multiple of 16 bits for raster_op */
	bitmap->bytes_wide = ROUNDUP((int) bitmap->w, BMBITS) * BMBYTES;
	size = bitmap->bytes_wide * bitmap->h;
	bitmap->bits = (char*)xmalloc(size != 0 ? size : 1);
}

/*
 *	Public routines
 */


#ifndef	WORDS_BIGENDIAN
#define word_swap(x) x
#else
#define word_swap(x) \
  ((((x) & 0xff000000) >> 24) | (((x) & 0x00ff0000) >>  8) | \
	 (((x) & 0x0000ff00) <<  8) | (((x) & 0x000000ff) << 24))
#endif

static	void
read_GF_char(struct font *fontp, wide_ubyte ch)
{
	struct glyph *g;
	ubyte	cmnd;
	int	min_m, max_m, min_n, max_n;
	BMUNIT	*cp, *basep, *maxp;
	BMUNIT	**basep_cpp = &basep;
	int	bytes_wide;
	bool	paint_switch;
#define	White	false
#define	Black	true
	bool	new_row;
	int	count;
	int	word_weight;

	g = &fontp->glyph[ch];
	GF_file = fontp->file;

	if(debug & DBG_PK)
	    printf("Loading gf char %d", ch);

	for (;;) {
	    switch (cmnd = one(GF_file)) {
		case XXX1:
		case XXX2:
		case XXX3:
		case XXX4:
		    fseek(GF_file, (long) num(GF_file,
			WIDENINT cmnd - XXX1 + 1), 1);
		    continue;
		case YYY:
		    (void) four(GF_file);
		    continue;
		case BOC:
		    (void) four(GF_file);	/* skip character code */
		    (void) four(GF_file);	/* skip pointer to prev char */
		    min_m = sfour(GF_file);
		    max_m = sfour(GF_file);
		    g->x = -min_m;
		    min_n = sfour(GF_file);
		    g->y = max_n = sfour(GF_file);
		    g->bitmap.w = max_m - min_m + 1;
		    g->bitmap.h = max_n - min_n + 1;
		    break;
		case BOC1:
		    (void) one(GF_file);	/* skip character code */
		    g->bitmap.w = one(GF_file);	/* max_m - min_m */
		    g->x = g->bitmap.w - one(GF_file);	/* ditto - max_m */
		    ++g->bitmap.w;
		    g->bitmap.h = one(GF_file) + 1;
		    g->y = one(GF_file);
		    break;
		default:
		    fprintf(stderr,"Bad BOC code:  %d", cmnd);
	    }
	    break;
	}
	paint_switch = White;

	if (debug)
	    printf(", size=%dlx%d, dvi_adv=%ld\n", g->bitmap.w, g->bitmap.h,
		g->dvi_adv);

	alloc_bitmap(&g->bitmap);
	cp = basep = (BMUNIT *) g->bitmap.bits;
/*
 *	Read character data into *basep
 */
	bytes_wide = ROUNDUP((int) g->bitmap.w, BMBITS) * BMBYTES;
	maxp = ADD(basep, g->bitmap.h * bytes_wide);
	bzero(g->bitmap.bits, g->bitmap.h * bytes_wide);
	new_row = false;
	word_weight = BMBITS;
	for (;;) {
	    count = -1;
	    cmnd = one(GF_file);
	    if (cmnd < 64) count = cmnd;
	    else if (cmnd >= NEW_ROW_0 && cmnd <= NEW_ROW_MAX) {
		count = cmnd - NEW_ROW_0;
		paint_switch = White;	/* it'll be complemented later */
		new_row = true;
	    }
	    else switch (cmnd) {
		case PAINT1:
		case PAINT2:
		case PAINT3:
		    count = num(GF_file, WIDENINT cmnd - PAINT1 + 1);
		    break;
		case EOC:
		    if (cp >= ADD(basep, bytes_wide)) too_many_bits(ch);
		    return;
		case SKIP1:
		case SKIP2:
		case SKIP3:
		  *(basep_cpp) +=
		    num(GF_file, WIDENINT cmnd - SKIP0) * bytes_wide / sizeof (BMUNIT);
		case SKIP0:
		    new_row = true;
		    paint_switch = White;
		    break;
		case XXX1:
		case XXX2:
		case XXX3:
		case XXX4:
		    fseek(GF_file, (long) num(GF_file,
			WIDENINT cmnd - XXX1 + 1), 1);
		    break;
		case YYY:
		    (void) four(GF_file);
		    break;
		case NO_OP:
		    break;
		default:
		    fprintf(stderr, "Bad command in GF file:  %d", cmnd);
	    } /* end switch */
	    if (new_row) {

	      *(basep_cpp) +=
		bytes_wide / sizeof (BMUNIT);
	      if (basep >= maxp || cp >= basep) too_many_bits(ch);
		 cp = basep;
		word_weight = BMBITS;
		new_row = false;
	    }
	    if (count >= 0) {
		while (count)
		    if (count <= word_weight) {
			if (paint_switch) {
			    *cp = word_swap (*cp);
			    *cp |= bit_masks[count] << (BMBITS - word_weight);
			    *cp = word_swap (*cp);
			}
			word_weight -= count;
			break;
		    }
		    else {
			if (paint_switch) {
			    *cp = word_swap (*cp);
			    *cp |= bit_masks[word_weight] <<
				(BMBITS - word_weight);
			    *cp = word_swap (*cp);
			}
			cp++;
			count -= word_weight;
			word_weight = BMBITS;
		    }
		paint_switch = ! paint_switch;
	    }
	} /* end for */
}


void
read_GF_index(	struct font	*fontp,	wide_bool	hushcs)
{
	int		hppp, vppp;
	ubyte		ch, cmnd;
	struct glyph	*g;
	long		checksum;

	fontp->read_char = read_GF_char;
	GF_file = fontp->file;
	if (debug)
	    printf("Reading GF pixel file %s\n", fontp->filename);
/*
 *	Find postamble.
 */
	fseek(GF_file, (long) -4, 2);
	while (four(GF_file) != ((unsigned long) TRAILER << 24 | TRAILER << 16
		| TRAILER << 8 | TRAILER))
	    fseek(GF_file, (long) -5, 1);
	fseek(GF_file, (long) -5, 1);
	for (;;) {
	    ch = one(GF_file);
	    if (ch != TRAILER) break;
	    fseek(GF_file, (long) -2, 1);
	}
	if (ch != GF_ID_BYTE)
	  fprintf(stderr, "Bad end of font file %s", fontp->fontname);
	fseek(GF_file, (long) -6, 1);
	expect(POST_POST);
	fseek(GF_file, sfour(GF_file), 0);	/* move to postamble */
/*
 *	Read postamble.
 */
	expect(POST);
	(void) four(GF_file);		/* pointer to last eoc + 1 */
	(void) four(GF_file);		/* skip design size */
	checksum = four(GF_file);
	if (checksum != fontp->checksum && checksum != 0 && fontp->checksum != 0
		&& !hushcs)
	    fprintf(stderr,
		"Checksum mismatch (dvi = %lu, gf = %lu) in font file %s\n",
		fontp->checksum, checksum, fontp->filename);
	hppp = sfour(GF_file);
	vppp = sfour(GF_file);
	if (hppp != vppp && (debug))
	    printf("Font has non-square aspect ratio %d:%d\n", vppp, hppp);
	(void) four(GF_file);		/* skip min_m */
	(void) four(GF_file);		/* skip max_m */
	(void) four(GF_file);		/* skip min_n */
	(void) four(GF_file);		/* skip max_n */
/*
 *	Prepare glyph array.
 */
	fontp->glyph = (struct glyph*)xmalloc(256 * sizeof(struct glyph));
	bzero((char *) fontp->glyph, 256 * sizeof(struct glyph));
/*
 *	Read glyph directory.
 */
	while ((cmnd = one(GF_file)) != POST_POST) {
	    int addr;

	    ch = one(GF_file);			/* character code */
	    g = &fontp->glyph[ch];
	    switch (cmnd) {
		case CHAR_LOC:
		    /* g->pxl_adv = sfour(GF_file); */
		    (void) four(GF_file);
		    (void) four(GF_file);	/* skip dy */
		    break;
		case CHAR_LOC0:
		    /* g->pxl_adv = one(GF_file) << 16; */
		    (void) one(GF_file);
		    break;
		default:
		    fprintf(stderr, "Non-char_loc command found in GF preamble:  %d",
			cmnd);
	    }
	    g->dvi_adv = (long int) fontp->dimconv * sfour(GF_file);
	    addr = four(GF_file);
	    if (addr != -1) g->addr = addr;
	    if (debug)
		printf("Read GF glyph for character %d; dy = %ld, addr = %d\n",
			ch, g->dvi_adv, addr);
	}
}


void
help ()
{
  printf (
	  "gf2pbm [options] FONT-NAME\n"
	  "Options: \n"
	  "  -b        dump bitmap\n"
	  "  -d        debug\n"
	  "  -n NUM    do glyph number NUM\n"
	  "  -o FILE   output to FILE\n"
	  "  -h        this help\n"
	  "  -s        print bitmap size\n"
	  "\n"
	  "Return status:\n"
	  "  0 - success\n"
	  "  1 - no such glyph\n"
	  "  2 - error\n"
 	  "Based on Paul Vojta's Xdvi, munged by Han-Wen Nienhuys <hanwen@xs4all.nl>\n"
	  );
}

void
dump_bitmap (FILE *out, struct bitmap *bm)
{
  int bs = (bm->w) / 8 + ((bm->w % 8) ? 1 : 0);
  int h =0;  
  fprintf (out, "P4\n");
  fprintf (out, "%d %d\n", bm->w, bm->h);

  for (h = 0 ; h < bm->h; h++)
    {
      int c;
      for (c = 0 ; c < bs; c++)
	{
	  ubyte todump = bm->bits[h *bm->bytes_wide + c];
	  ubyte outb = 0;
	  int i = 8; 
	  while (i --)
	    {
	      outb = (outb << 1) | (todump & 0x1);
	      todump = todump >> 1;
	    }
	  fputc(outb, out);
	}
    }
}

int
main (int argc, char * argv [])
{
  int print_size = 0;
  int do_bitmap = 0;
  FILE * in_file= 0;
  struct font * fontp;

  int glyph_num = 65;
  char *filename =NULL;
  char * outfilename = NULL;
  int c;
  while ((c = getopt (argc, argv, "bsdho:n:")) != -1)
    {
      switch (c)
	{
	case 'b':
	  do_bitmap = true;
	  break;
	  
	case 'd':
	  debug = true;
	  break;
	case 'h':
	  help ();
	  exit (0);
	  break;
	case 'n':
	   sscanf (optarg, "%d", &glyph_num);
	  break;
	case 's':
	  print_size = true;
	  break;
	case 'o':
	  outfilename = optarg;
	  break;
	  
	}
    }
  
  if (!do_bitmap && !print_size)
    do_bitmap = true;
  
  filename = argv[optind];
  
  if (!filename)
    {
      fprintf (stderr, "No font-name found. Use -h for help\n"); 
      exit (2);
    }
  
  in_file = fopen (filename, "r");
  if (!in_file)
    {
      fprintf (stderr, "could not open `%s'\n", filename);
      exit (2);
    }

  fontp = (struct font*)malloc (sizeof (struct font));
  bzero (fontp, sizeof (struct font));

  fontp->fontname = filename;
  fontp->file = in_file;
  fontp->fsize = 0;
  fontp->timestamp = 0;
  fontp->maxchar = 255;
  maxchar = 255;

  
  {
    int magic = two(fontp->file);
    if(magic != GF_MAGIC)
      {
	fprintf (stderr, "Not a GF file\n");
	exit (2);
      }
  }

  read_GF_index (fontp,	false);
  while (maxchar > 0 && fontp->glyph[maxchar].addr == 0) --maxchar;
  if (maxchar < 255)
    realloc_font(fontp, WIDENINT maxchar);

  if (fontp->glyph[glyph_num].addr == 0)
    {
      fprintf (stderr,  "No glyph number %d\n", glyph_num);
      return 1;
    }
  
  fseek(fontp->file, fontp->glyph[glyph_num].addr, 0);
	   
  read_GF_char (fontp, glyph_num);
  
  if (print_size)
    {
      struct glyph* gp = fontp->glyph + glyph_num;
      fprintf (stdout, "size: %dx%d, offset: (%d,%d)\n",
	       gp->bitmap.w, gp->bitmap.h,
	       gp->x, gp->y);
	       
    }

  if (do_bitmap)
    {
  FILE * out_file = 0; 
  if (outfilename && !strcmp ("-", outfilename))
    out_file = stdout;

  out_file = outfilename ? fopen (outfilename, "w") : NULL;
  if(!out_file)
    {
      static char s[100];
      sprintf (s, "%d.pbm", glyph_num);
      outfilename = s;
      out_file = fopen (s, "w");
    }

  if (!out_file)
    {
      fprintf (stderr, "Could not open output file `%s'\n", outfilename);
      exit (2);
    }
        
    dump_bitmap (out_file, &fontp->glyph[glyph_num].bitmap);
  fclose (out_file);
    }
  return 0;
}
