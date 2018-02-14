'''
Created on Jan 25, 2016

@author: xiao
'''
import collections
import logging
import numpy as np
from itertools import chain
from pdfminer.layout import LTTextLine, LTChar, LTAnno, LTCurve, LTComponent, LTLine
from pdftotree.pdf.vector_utils import *

log = logging.getLogger(__name__)

def traverse_layout(root, callback):
    '''
    Tree walker and invokes the callback as it
    traverse pdf object tree
    '''
    callback(root)
    if isinstance(root, collections.Iterable):
        for child in root:
            traverse_layout(child, callback)


def get_near_items(tree,tree_key):
    '''
    Check both possible neighbors for key
    in a binary tree
    '''
    try:
        yield tree.floor_item(tree_key)
    except KeyError:
        pass
    try:
        yield tree.ceiling_item(tree_key)
    except KeyError:
        pass

def align_add(tree, key, item, align_thres = 2.0):
    '''
    Adding the item object to a binary tree with the given
    key while allow for small key differences
    close_enough_func that checks if two keys are
    within threshold
    '''
    for near_key, near_list in get_near_items(tree, key):
        if abs(key - near_key) < align_thres:
            near_list.append(item)
            return
    # Create a new group if no items are close
    tree[key] = [item]


right_wall = lambda m: (m.x1,m.y0,m.x1,m.y1)
left_wall = lambda m: (m.x0,m.y0,m.x0,m.y1)
top_wall = lambda m: (m.x0,m.y0,m.x1,m.y0)
bot_wall = lambda m: (m.x0,m.y1,m.x1,m.y1)
def vlines_between(plane, prev, m):
    if not prev or not m: return []
    if prev.xc > m.xc: prev, m = m, prev
    query = (prev.xc, prev.yc, m.xc, prev.yc)
    return [l for l in plane.find(query) if l.x1 - l.x0 < 0.1]

def hlines_between(plane, prev, m):
    if not prev or not m: return []
    if prev.yc > m.yc: prev, m = m, prev
    query = (prev.xc, prev.yc, prev.xc, m.yc)
    return [l for l in plane.find(query) if l.y1 - l.y0 < 0.1]


def is_same_row(m1,m2):
    # Corner case for row separation
    #------
    #-prev- ------
    #------ ---m--
    #       ------
    return m1 and m2 and m2.yc > m1.y0 and m2.yc < m1.y1

def is_vline(l):
    return l.x1 - l.x0 < 0.1

def is_hline(l):
    return l.y1 - l.y0 < 0.1
#
# def align_add_to_tree(tree, key, item, close_enough_func):
#     '''
#     Adding the item object to a binary tree with the given
#     key while allow for small key differences
#     close_enough_func that checks if two keys are
#     within threshold
#     '''
#     has_neighbor = False
#     for near_key, near_list in get_near_items(tree, key):
#         if close_enough_func(key, near_key):
#             near_list.append(item)
#             has_neighbor = True
#             break
#
#     # Create a new group if no items are close
#     if not has_neighbor:
#         tree[key] = [item]
#

def collect_table_content(table_bboxes,elems):
    '''
    Returns a list of elements that are contained inside
    the corresponding supplied bbox.
    '''
    # list of table content chars
    table_contents = [[] for _ in xrange(len(table_bboxes))]
    prev_content = None
    prev_bbox = None
    for cid, c in enumerate(elems):
        # Annotations should not fall outside alone
        if isinstance(c, LTAnno):
            if prev_content is not None:
                prev_content.append(c)
            continue
        # Generally speaking table contents should be included sequentially
        # and we can avoid checking all tables for elems inside
        # Elements only need to intersect the bbox for table as some
        # formatting of fonts may result in slightly out of bbox text
        if prev_bbox is not None and intersect(prev_bbox,c.bbox):
            prev_content.append(c)
            continue
        # Search the rest of the tables for membership when done with
        # the current one
        for table_id,table_bbox in enumerate(table_bboxes):
            if intersect(table_bbox, c.bbox):
                prev_bbox = table_bbox
                prev_content = table_contents[table_id]
                prev_content.append(c)
                break
    return table_contents

_bbox = namedtuple('_bbox', ['bbox'])
_inf_bbox = _bbox([float('inf')] * 4)

def _gaps_from(intervals):
    '''
    From a list of intervals extract
    a list of sorted gaps in the form of [(g,i)]
    where g is the size of the ith gap.
    '''
    sliding_window = izip(intervals, intervals[1:])
    gaps = [b[0] - a[1] for a, b in sliding_window]
    return gaps

def project_onto(objs, axis, min_gap_size = 4.0):
    '''
    Projects object bboxes onto the axis and return the
    unioned intervals and groups of objects in intervals.
    '''
    if axis == 'x': axis = 0
    if axis == 'y': axis = 1
    axis_end = axis + 2
    if axis == 0: # if projecting onto X axis
        objs.sort(key = lambda o:o.x0)
    else:
        objs.sort(key = lambda o:o.y0)

    intervals = []
    groups = []

    start_i = 0
    start = objs[0].bbox[axis]
    end = objs[0].bbox[axis_end]

    # Use _inf_bbox to trigger the last interval divide
    for o_i, o in enumerate(chain(objs,[_inf_bbox])):

        # Get current interval
        o_start = o.bbox[axis]
        o_end = o.bbox[axis_end]

        # start new interval when gap with previous end is big
        if o_start > end + min_gap_size:

            # Append new interval coordinates for children
            intervals.append((start, end))

            # Append child object group on page
            groups.append(objs[start_i:o_i])

            # Mark next obj list range
            start_i = o_i
            start = o_start

        # Always check to extend current interval to new end
        if o_end > end:
            end = o_end
        # else do nothing
    return intervals, groups

def recursive_xy_divide(elems, avg_font_size):
    '''
    Recursively group/divide the document by white stripes
    by projecting elements onto alternating axes as intervals.

    avg_font_size: the minimum gap size between elements below
    which we consider interval continuous.
    '''
    log.info(avg_font_size)
    objects = list(elems.mentions)
    objects.extend(elems.segments)
    bboxes = []
    # A tree that is a list of its children
    # bboxes can be recursively reconstructed from
    # the leaves
    def divide(objs, bbox, h_split = True, is_single = False):
        '''
        Recursive wrapper for splitting a list of objects
        with bounding boxes.
        h_split: whether to split along y axis, otherwise
        we split along x axis.
        '''
        if not objs: return []

        # range start/end indices
        axis = 1 if h_split else 0

        intervals, groups = project_onto(objs, axis, avg_font_size)

        # base case where we can not actually divide
        single_child = len(groups) == 1

        # Can not divide in both X and Y, stop
        if is_single and single_child:
            bboxes.append(bbox)
            return objs
        else:
            children = []

            for interval, group in izip(intervals, groups):
                # Create the bbox for the subgroup
                sub_bbox = np.array(bbox)
                sub_bbox[[axis, axis + 2]] = interval
                # Append the sub-document tree
                child = divide(group, sub_bbox, not h_split, single_child)
                children.append(child)
            return children

    full_page_bbox = (0, 0, elems.layout.width, elems.layout.height)
    # Filter out invalid objects
    objects = [o for o in objects if inside(full_page_bbox,o.bbox)]
    log.info('avg_font_size for dividing', avg_font_size)
    tree = divide(objects, full_page_bbox) if objects else []
    return bboxes, tree

