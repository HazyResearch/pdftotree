'''
Created on Oct 21, 2015

@author: xiao


'''
import six  # Python 2-3 compatibility
from collections import namedtuple
import numpy as np

# bbox indices
x0 = 0
y0 = 1
x1 = 2
y1 = 3

class Segment(namedtuple('Segment', ['e','vector'])):
    __slots__ = ()
    @property
    def length(self):
        return self.vector[x0] if self.vector[x0] else self.vector[y0]
    def horizontal(self):
        return bool(self.vector[x0])
    def vertical(self):
        return bool(self.vector[y0])
    def __str__(self, *args, **kwargs):
        return ' '.join(str(x) for x in [self.e, self.vector, self.e.linewidth])

def vectorize(e, tolerance = 0.1):
    '''
    vectorizes the pdf object's bounding box
    min_width is the width under which we consider it a line
    instead of a big rectangle
    '''
    tolerance = max(tolerance,e.linewidth)
    is_high = e.height > tolerance
    is_wide = e.width > tolerance
    # if skewed towards a line
    if is_wide and not is_high:
        return (e.width,0.)
    if is_high and not is_wide:
        return (0.,e.height)

def aligned(e1,e2):
    '''
    alignment is determined by two boxes having one exactly the same
    attribute, which could mean parallel, perpendicularly forming a
    corner etc.
    '''
    return (any(close(c1,c2) for c1,c2 in zip(e1.bbox,e2.bbox)) or
            x_center_aligned(e1, e2) or
            y_center_aligned(e1, e2))

def x_center_aligned(e1,e2):
    return close(e1.x0+e1.x1, e2.x0 + e2.x1)

def x_aligned(a, b):
    return x_center_aligned(a, b) or close(a.x0,b.x0) or close(a.x1, b.x1)

def y_center_aligned(e1,e2):
    return close(e1.y0+e1.y1, e2.y0 + e2.y1)

def close(f1,f2,thres = 2.0):
    return abs(f1-f2) < thres

def origin(bbox):
    return bbox[:2]

def center(bbox):
    return ((bbox[x0] + bbox[x1]) / 2, (bbox[y0] + bbox[y1]) / 2)

def area(bbox):
    return (bbox[x1]-bbox[x0])*(bbox[y1]-bbox[y0])

def l1(c1,c2):
    return sum(abs(v1-v2) for v1, v2 in zip(c1,c2))

def segment_diff(s1,s2):
    '''
    Returns the sum of absolute difference between
    two segments' end points.
    Only perfectly aligned segments return 0
    '''
    return abs(s1[0] - s2[0]) + abs(s1[1] - s2[1])

def bound_bboxes(bboxes):
    '''
    Finds the minimal bbox that contains all given bboxes
    '''
    group_x0 = min(map(lambda l:l[x0],bboxes))
    group_y0 = min(map(lambda l:l[y0],bboxes))
    group_x1 = max(map(lambda l:l[x1],bboxes))
    group_y1 = max(map(lambda l:l[y1],bboxes))
    return (group_x0,group_y0,group_x1,group_y1)

def bound_elems(elems):
    '''
    Finds the minimal bbox that contains all given elems
    '''
    group_x0 = min(map(lambda l:l.x0,elems))
    group_y0 = min(map(lambda l:l.y0,elems))
    group_x1 = max(map(lambda l:l.x1,elems))
    group_y1 = max(map(lambda l:l.y1,elems))
    return (group_x0,group_y0,group_x1,group_y1)

def intersect(a,b):
    '''
    Check if two rectangles intersect
    '''
    if (a[x0] == a[x1] or a[y0] == a[y1]):
        return False
    if (b[x0] == b[x1] or b[y0] == b[y1]):
        return False    
    return a[x0] <= b[x1] and b[x0] <= a[x1] \
        and a[y0] <= b[y1] and b[y0] <= a[y1]

def inside(outer,inner):
    return inner[x0] >= outer[x0] and inner[x1] <= outer[x1] \
        and inner[y0] >= outer[y0] and inner[y0] <= outer[y1]

_stretch_dir = np.array([-1,-1,1,1])
def enlarge(bbox, delta):
    return np.array(bbox) + delta * _stretch_dir

def reading_order(e1,e2):
    '''
    A comparator to sort bboxes from top to bottom, left to right
    '''
    b1 = e1.bbox
    b2 = e2.bbox
    if round(b1[y0]) == round(b2[y0]) or round(b1[y1]) == round(b2[y1]):
        return float_cmp(b1[x0], b2[x0])
    return float_cmp(b1[y0], b2[y0])

def xy_reading_order(e1, e2):
    '''
    A comparator to sort bboxes from left to right, top to bottom
    '''
    b1 = e1.bbox
    b2 = e2.bbox
    if round(b1[x0]) == round(b2[x0]):
        return float_cmp(b1[y0], b2[y0])
    return float_cmp(b1[x0], b2[x0])

def column_order(b1, b2):
    '''
    A comparator that sorts bboxes first by "columns", where a column is made
    up of all bboxes that overlap, then by vertical position in each column.

    b1 = [b1.type, b1.top, b1.left, b1.bottom, b1.right]
    b2 = [b2.type, b2.top, b2.left, b2.bottom, b2.right]
    '''
    (top, left, bottom, right) = (1, 2, 3, 4)
    # TODO(senwu): Reimplement the functionality of this comparator to
    # detect the number of columns, and sort those in reading order.

    # TODO: This is just a simple top to bottom, left to right comparator
    # for now.
    if (round(b1[top]) == round(b2[top]) or
            round(b1[bottom]) == round(b2[bottom])):
        return float_cmp(b1[left], b2[left])
    return float_cmp(b1[top], b2[top])

    #  if((b1[left] >= b2[left] and b1[left] <= b2[right]) or
    #          (b2[left] >= b1[left] and b2[left] <= b1[right])):
    #      return float_cmp(b1[top], b2[top])
    #
    #  # Return leftmost columns first
    #  return float_cmp(b1[left], b2[left])

def float_cmp(f1, f2):
    if f1 > f2:
        return 1
    elif f1 < f2:
        return -1
    else:
        return 0

def merge_intervals(elems, overlap_thres = 2.0):
    '''
    Project in x axis
    Sort by start
    Go through segments and keep max x1

    Return a list of non-overlapping intervals
    '''
    overlap_thres = max(0.0, overlap_thres)
    ordered = sorted(elems, key=lambda e:e.x0)

    intervals = []
    cur = [-overlap_thres,-overlap_thres]
    for e in ordered:
        if e.x0 - cur[1] > overlap_thres:
            # Check interval validity
            if cur[1] > 0.0:
                intervals.append(cur)
            cur = [e.x0,e.x1]
            continue
        cur[1] = max(cur[1],e.x1)
    intervals.append(cur)
    # Freeze the interval to tuples
    return map(tuple,intervals)
