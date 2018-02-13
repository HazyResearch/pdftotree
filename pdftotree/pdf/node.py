'''
Created on Jun 10, 2016

@author: xiao
'''
import six  # Python 2-3 compatibility
from pdftotree.pdf.vector_utils import bound_elems, bound_bboxes
from collections import Counter, defaultdict
from pdfminer.layout import LTLine, LTTextLine, LTCurve, LTFigure, LTComponent
from pdfminer.utils import Plane
from pdftotree.pdf.layout_utils import is_vline, is_same_row
import numbers
import numpy as np
from pprint import pprint
from pdftotree.pdf import grid
from pdftotree.pdf.grid import Grid

def elem_type(elem):
    if isinstance(elem, LTLine):
        return 'line'
    if isinstance(elem, LTCurve):
        return 'curve'
    if isinstance(elem, LTTextLine):
        return 'text'
    if isinstance(elem, LTFigure):
        return 'figure'
    return 'unkown'

class Node(LTComponent):
    '''
    A rectangular region in the document representing certain local semantics.
    Also holds its data and features.
    '''
    def __init__(self, elems):
        '''
        Constructor
        '''
        self.elems = elems
        self.sum_elem_bbox = 0
        for elem in elems:
            self.sum_elem_bbox = self.sum_elem_bbox + abs((elem.bbox[0]-elem.bbox[2])*(elem.bbox[1]-elem.bbox[3]))
        #     # self.sum_elem_bbox = self.sum_elem_bbox + len(elem.get_text())
        self.table_area_threshold = 0.7
        self.set_bbox(bound_elems(elems))
        # self.table_indicator = True
        self.type_counts = Counter(map(elem_type,elems))
        if(elem_type(elems) not in ["figure", "unknown"]):
            self.feat_counts = Counter(kv for e in elems for kv in six.iteritems(e.feats))
        else:
            self.feat_counts = 0
        self.type = "UNK"

    def merge(self, other):
        self.elems.extend(other.elems)
        self.set_bbox(bound_bboxes([self.bbox, other.bbox]))
        self.type_counts += other.type_counts
        self.feat_counts += other.feat_counts

    def area(self):
        return self.height * self.width

    def is_borderless(self):
        # at least this many segments for a table
        return self.type_counts['line'] < 6

    def is_table(self):
        '''
        Count the node's number of mention al ignment in both axes to determine
        if the node is a table.
        '''
        if self.type_counts['text'] < 6 or 'figure' in self.type_counts: return False
        for e in self.elems:
            # Characters written as curve are usually small, discard diagrams here
            if elem_type(e) == 'curve' and e.height*e.width > 100: return False
        # import re
        # space_re = '\\s+'
        # ws_arr = []
        # whitespace_aligned = False
        # for elem in self.elems:
        #     elem_ws = []
        #     for m in re.finditer(space_re, elem.get_text()):
        #         elem_ws.append(m.start())
        #     # print elem, elem_ws
        #     if(len(elem_ws)>0):
        #         ws_arr.append(elem_ws)
        # # print ws_arr
        # if(len(ws_arr)>0):
        #     count_arr = max([ws_arr.count(i) for i in ws_arr])
        #     if(float(count_arr)/len(ws_arr) > 0.75):
        #         return True
        if((self.sum_elem_bbox/(self.height*self.width)) > self.table_area_threshold):
            return False
        has_many_x_align = False
        has_many_y_align = False
        for k, v in six.iteritems(self.feat_counts):
            font_key = k[0]
            if v >= 2 and '-' in font_key: # Text row or column with more than 2 elements
                if font_key[-2] == 'x': has_many_x_align = True
                if font_key[-2] == 'y': has_many_y_align = True
        return has_many_x_align and has_many_y_align
        # return 0.5

    def get_grid(self):
        '''
        Standardize the layout of the table into grids
        '''
        mentions, lines = _split_text_n_lines(self.elems)
        # Sort mentions in reading order where y values are snapped to half height-sized grid
        mentions.sort(key=lambda m:(m.yc_grid, m.xc))

        grid = Grid(mentions, lines, self)
        return grid

    def _find_vbars_for_row(self, plane, row):
        align_grid_size = sum(m.height for m in row)/2.0/len(row) # half the avg height
        # Find all x_coords of vertical bars crossing this row
        ryc = sum(m.yc for m in row)/len(row) # avg yc
        query_rect = (self.x0, ryc, self.x1, ryc)
        vbars = filter(is_vline, plane.find(query_rect)) # vbars in this row
        vbars = [(v.xc, v.xc_grid) for v in vbars]
        vbars.sort()
        # Group bars less than min cell width apart as one bar
        prev_xc = -1
        clustered_vbars = []
        for xc, xc_grid in vbars:
            if prev_xc < 0 or xc - prev_xc > align_grid_size:
                clustered_vbars.append(xc_grid) # only keep snapped coord
                prev_xc = xc
        return clustered_vbars

    def __str__(self, *args, **kwargs):
        return '\t'.join(r.get_text().encode('utf8','replace') for r in self.elems
                         if isinstance(r, LTTextLine))

#############################################
#    Static utilities
#############################################
def _split_text_n_lines(elems):
    texts = []
    lines = []
    for e in elems:
        if isinstance(e, LTTextLine):
            texts.append(e)
        elif isinstance(e, LTLine):
            lines.append(e)
    return texts, lines


def _left_bar(content, default_val):
    last_bar = default_val
    for _coord, val in content:
        if not isinstance(val,LTTextLine):
            last_bar = val
        yield last_bar

def _right_bar(content, default_val):
    return reversed(list(_left_bar(reversed(content), default_val)))

def _find_col_parent_for_row(content):
    pass

def _get_cols(row_content):
    '''
    Counting the number columns based on the content of this row
    '''
    cols = []
    subcell_col = []
    prev_bar = None
    for _coord, item in row_content:
        if isinstance(item, LTTextLine):
            subcell_col.append(item)
        else:# bar, add column content
            # When there is no content, we count a None column
            if prev_bar:
                bar_ranges = (prev_bar, item)
                col_items = subcell_col if subcell_col else [None]
                cols.extend([bar_ranges,col_items])
            prev_bar = item
            subcell_col = []
    # Remove extra column before first bar
    return cols

def _row_str(row_content):
    def strfy(r):
        if r is None: return 'None'
        if isinstance(r, tuple):
            _c, r = r
        if isinstance(r, LTTextLine):
            return r.get_text().encode('utf8','replace')
        if isinstance(r, numbers.Number):
            return '|'
        return str(r)
    return '\t'.join(strfy(r) for r in row_content)

def _get_rows(mentions):
    curr_row = []
    rows = []
    prev = None
    for m in mentions:
        if not is_same_row(prev, m):
            if curr_row: rows.append(curr_row)
            curr_row = []
        curr_row.append(m)
        prev = m
    # Finish up last row
    if curr_row: rows.append(curr_row)
    return rows

def _one_contains_other(s1, s2):
    '''
    Whether one set contains the other
    '''
    return min(len(s1), len(s2)) == len(s1 & s2)
