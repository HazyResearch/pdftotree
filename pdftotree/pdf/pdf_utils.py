'''
Created on Oct 12, 2015
Various routines to work with pdf objects
extracted with PDFminer

@author: xiao
'''
import logging
import os
import re
import six  # Python 2+3 compatibility
import string
from collections import Counter
from pdftotree.img_utils import *
from pdftotree.pdf.vector_utils import *
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTFigure
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.utils import apply_matrix_pt
from pdfminer.pdfdocument import PDFDocument
from pdftotree.pdf.layout_utils import *

# Compact wrapper representation for the pdf
PDFElems = namedtuple('PDFElems', ['mentions', 'segments', 'curves', 'figures', 'layout', 'chars'])

log = logging.getLogger(__name__)


class CustomPDFPageAggregator(PDFPageAggregator):
    '''
    A custom version of the default pdf miner stateful draw call
    interpreter. Handles the creation of python object from pdf draw
    calls.
    Changes the way LTCurves are created - break up large polylines
    and rectangles into standard segments.
    '''
    line_only_shape = re.compile('ml+h?')

    def paint_path(self, gstate, stroke, fill, evenodd, path):
        '''
        Converting long paths to small segments each time we m=Move
        or h=ClosePath for polygon
        '''
        shape = ''.join(x[0] for x in path)
        prev_split = 0
        for i in range(len(shape)):
            if shape[i] == 'm' and prev_split != i:
                self.paint_single_path(gstate, stroke, fill, evenodd, path[prev_split:i])
                prev_split = i
            if shape[i] == 'h':
                self.paint_single_path(gstate, stroke, fill, evenodd, path[prev_split:i + 1])
                prev_split = i + 1

        # clean up remaining segments
        if prev_split < len(shape):
            self.paint_single_path(gstate, stroke, fill, evenodd, path[prev_split:])

    def paint_single_path(self, gstate, stroke, fill, evenodd, path):
        '''
        Converting a single path draw command into lines and curves objects
        '''
        if len(path) < 2:
            return
        shape = ''.join(x[0] for x in path)

        pts = []
        for p in path:
            for i in range(1, len(p), 2):
                pts.append(apply_matrix_pt(self.ctm, (p[i], p[i + 1])))

        # Line mode
        if self.line_only_shape.match(shape):
            # check for sloped lines first
            has_slope = False
            for i in range(len(pts) - 1):
                if pts[i][0] != pts[i + 1][0] and pts[i][1] != pts[i + 1][1]:
                    has_slope = True
                    break
            if not has_slope:
                for i in range(len(pts) - 1):
                    self.cur_item.add(LTLine(gstate.linewidth, pts[i], pts[i + 1]))

                # Adding the closing line for a polygon, especially rectangles
                if shape.endswith('h'):
                    self.cur_item.add(LTLine(gstate.linewidth, pts[0], pts[-1]))
                return

        # Add the curve as an arbitrary polyline (belzier curve info is lost here)
        self.cur_item.add(LTCurve(gstate.linewidth, pts))


def analyze_pages(file_name, char_margin=1.0):
    '''
    Input: the file path to the PDF file
    Output: yields the layout object for each page in the PDF
    '''
    # Open a PDF file.
    with open(os.path.realpath(file_name), 'rb') as fp:
        # Create a PDF parser object associated with the file object.
        parser = PDFParser(fp)
        # Create a PDF document object that stores the document structure.
        # Supply the password for initialization.
        document = PDFDocument(parser, password='')
        # Create a PDF resource manager object that stores shared resources.
        rsrcmgr = PDFResourceManager()
        # Set parameters for analysis.
        laparams = LAParams(char_margin=char_margin, word_margin=0.1, detect_vertical=True)
        # Create a PDF page aggregator object.
        device = CustomPDFPageAggregator(rsrcmgr, laparams=laparams)
        # Create a PDF interpreter object.
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        # Process each page contained in the document.
        for page_num, page in enumerate(PDFPage.create_pages(document)):
            try:
                interpreter.process_page(page)
            except OverflowError as oe:
                log.execption(oe, ', skipping page', page_num, 'of', file_name)
                continue
            layout = device.get_result()
            yield layout


def normalize_pdf(layout, scaler):
    '''
    Normalizes pdf object coordinates (bot left) to image
    conventions (top left origin).
    Returns the list of chars and average char size
    '''
    chars = []
    mentions = []
    height = scaler * layout.height
    font_size_counter = Counter()
    # Lines longer than this are included in segments
    pts_thres = 2.0 * scaler
    segments = []
    curves = []
    figures = []

    def processor(m):
        # Normalizes the coordinate system to be consistent with
        # image library conventions (top left as origin)
        if isinstance(m, LTComponent):
            m.set_bbox(normalize_bbox(m.bbox, height, scaler))

            if isinstance(m, LTCurve):
                m.pts = normalize_pts(m.pts, height, scaler)
                # Only keep longer lines here
                if isinstance(m, LTLine) and max(m.width, m.height) > pts_thres:
                    segments.append(m)
                    return
                # Here we exclude straight lines from curves
                curves.append(m)
                return

            if isinstance(m, LTFigure):
                figures.append(m)
                return

            # Collect stats on the chars
            if isinstance(m, LTChar):
                chars.append(m)
                # fonts could be rotated 90/270 degrees
                font_size = _font_size_of(m)
                font_size_counter[font_size] += 1
                return

            if isinstance(m, LTTextLine):
                mention_text = keep_allowed_chars(m.get_text()).strip()
                # Skip empty and invalid lines
                if mention_text:
                    # TODO: add subscript detection and use latex underscore
                    # or superscript
                    m.clean_text = mention_text
                    m.font_name, m.font_size = _font_of_mention(m)
                    mentions.append(m)
                return

        # Also include non character annotations
        if isinstance(m, LTAnno):
            chars.append(m)

    traverse_layout(layout, processor)

    # Resets mention y0 to the first y0 of alphanum character instead of
    # considering exotic unicode symbols and sub/superscripts to reflect
    # accurate alignment info
    for m in mentions:
        # best_y1 = min(c.y1 for c in m if isinstance(c, LTChar))
        alphanum_c = next((c for c in m if c.get_text().isalnum()), None)
        if alphanum_c:
            m.set_bbox((m.x0, alphanum_c.y0, m.x1, alphanum_c.y1))

        #     mentions.sort(key = lambda m: (m.y0,m.x0))
    elems = PDFElems(mentions, segments, curves, figures, layout, chars)
    return elems, font_size_counter


def _print_dict(elem_dict):
    '''
    Print a dict in a readable way
    '''
    for key, value in sorted(elem_dict.iteritems()):
        if isinstance(value, collections.Iterable):
            print(key, len(value))
        else:
            print(key, value)


def _font_size_of(ch):
    if isinstance(ch, LTChar):
        return max(map(abs, ch.matrix[:4]))
    return -1


def _font_of_mention(m):
    '''
    Returns the font type and size of the first alphanumeric
    char in the text or None if there isn't any.
    '''
    for ch in m:
        if isinstance(ch, LTChar) and ch.get_text().isalnum():
            return (ch.fontname, _font_size_of(ch))
    return (None, 0)


# Initialize the set of chars allowed in output
_ascii_allowed = [False] * 128
_forbidden_chars = '\n\t'
for c in string.printable: _ascii_allowed[ord(c)] = True
for c in _forbidden_chars: _ascii_allowed[ord(c)] = False


def _allowed_char(c):
    '''
    Returns whether the given unicode char is allowed in output
    '''
    c = ord(c)
    if c < 0:
        return False
    if c < 128:
        return _ascii_allowed[c]
    # Genereally allow unicodes, TODO: check for unicode control characters
    # characters
    return True


def keep_allowed_chars(text):
    '''
    Cleans the text for output
    '''
    #     print ','.join(str(ord(c)) for c in text)
    return ''.join(' ' if c == '\n' else c for c in text.strip() if _allowed_char(c))
