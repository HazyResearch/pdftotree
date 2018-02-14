'''
Created on Dec 2, 2015

@author: xiao
'''
import bisect
import logging
import numpy as np
import pandas as pd
from collections import defaultdict
from functools import cmp_to_key
from pdfminer.utils import Plane
from pdftotree.pdf.vector_utils import inside, reading_order
from pprint import pformat

class Cell(object):
    '''Represents a cell with no visual dividers inside'''
    def __init__(self, origin, texts=[], rowspan=1, colspan=1):
        '''
        origin: the top left grid coordinate of the cell
        '''
        self.rowstart, self.colstart = origin
        self.rowend = self.rowstart + rowspan
        self.colend = self.colstart + colspan
        self.texts = texts

    def __str__(self, *args, **kwargs):
        return ','.join([m.get_text().encode('utf8') for m in self.texts])

class Grid(object):
    '''
    A rendered grid to capture structural layout info
    '''
    def __init__(self, mentions, lines, region, min_cell_size=6.0):
        '''
        Constructor
        '''
        self.min_cell_size = min_cell_size
        vlines, hlines = _split_vlines_hlines(lines)

        self.xs = [v.xc for v in vlines]
        self.ys = [h.yc for h in hlines]

        # Remove closely clustered lines
        # Also make sure there is at least 1 mega column for the table
        self.xs = _retain_centroids(self.xs + [region.x0, region.x1], min_cell_size)
        self.ys = _retain_centroids(self.ys + [region.y0, region.y1], min_cell_size)

        self.xranges = zip(self.xs, self.xs[1:])
        self.yranges = zip(self.ys, self.ys[1:])

        self.num_cols = len(self.xranges)
        self.num_rows = len(self.yranges)

        # Grid contents
        self._grid = np.full([self.num_rows, self.num_cols], None, dtype=np.dtype(object))
        grid = self._grid

        # Record whether a particular cell boundary is present
        line_plane = Plane(region.bbox)
        line_plane.extend(lines)
        vbars, hbars = self._mark_grid_bounds(line_plane, region)
        cells = []
        # Establish cell regions
        for i in xrange(self.num_rows):
            for j in xrange(self.num_cols):
                if grid[i, j]: continue  # Skip already marked cells
                # Merge with cell above
                if i > 0 and not hbars[i, j]:
                    grid[i, j] = cell = grid[i - 1, j]
                    cell.rowend = i + 1
                # Merge with cell left
                elif j > 0 and not vbars[i, j]:
                    grid[i, j] = cell = grid[i, j - 1]
                    cell.colend = j + 1
                # Create new cell otherwise
                else:
                    grid[i, j] = cell = Cell([i, j])
                    cells.append(cell)

        # Now get the cell's contents by using its boundary
        text_plane = Plane(region.bbox)
        text_plane.extend(mentions)

        for cell in cells:
            x0 = self.xs[cell.colstart]
            x1 = self.xs[cell.colend]
            y0 = self.ys[cell.rowstart]
            y1 = self.ys[cell.rowend]
            bbox = (x0, y0, x1, y1)
            # Keep mentions whose centers are inside the cell
            cell.texts = [m for m in text_plane.find(bbox) if inside(bbox, (m.xc, m.yc) * 2)]

        # TODO: provide HTML conversion here

        self.get_normalized_grid()

    def to_dataframe(self):
        return pd.DataFrame(self._grid)

    def to_html(self):
        return self.to_dataframe().to_html(index=False, header=False)

    def get_normalized_grid(self):
        '''
        Analyzes subcell structure
        '''
        log = logging.getLogger(__name__)
        # Resolve multirow mentions, TODO: validate against all PDFs
        subcol_count = 0;
        mega_rows = []
        for row_id, row in enumerate(self._grid):
            # maps yc_grid -> [mentions]
            subrow_across_cell = defaultdict(list)
            for col_id, cell in enumerate(row):
                # Keep cell text in reading order
                cell.texts.sort(key=cmp_to_key(reading_order))
#                intervals, groups = project_onto(cell.texts, axis='x', self.min_cell_size)
                prev = None
                log.debug('='*50)
                for m in cell.texts:
                    subrow_across_cell[m.yc_grid].append(m)
                    prev = m

            log.debug(pformat(dict(subrow_across_cell)))

            mega_rows.append(subrow_across_cell)

        # Multiline paragraph check
        # Subrow/Subcolumn

        return mega_rows

    def _mark_grid_bounds(self, plane, region_bbox):
        '''
        Assume all lines define a complete grid over the region_bbox.
        Detect which lines are missing so that we can recover merged
        cells.
        '''
        # Grid boundaries
        vbars = np.zeros([self.num_rows, self.num_cols + 1], dtype=np.bool)
        hbars = np.zeros([self.num_rows + 1, self.num_cols], dtype=np.bool)

        def closest_idx(arr, elem):
            left = bisect.bisect_left(arr, elem) - 1
            right = bisect.bisect_right(arr, elem) - 1
            return left if abs(arr[left] - elem) < abs(arr[right] - elem) else right

        # Figure out which separating segments are missing, i.e. merge cells
        for row, (y0, y1) in enumerate(self.yranges):
            yc = (y0 + y1) / 2
            for l in plane.find((region_bbox.x0, yc, region_bbox.x1, yc)):
                vbars[row, closest_idx(self.xs, l.xc)] = True
        for col, (x0, x1) in enumerate(self.xranges):
            xc = (x0 + x1) / 2
            for l in plane.find((xc, region_bbox.y0, xc, region_bbox.y1)):
                hbars[closest_idx(self.ys, l.yc), col] = True
        return vbars, hbars

############################
# Utilities
############################

def _retain_centroids(numbers, thres):
    '''Only keep one number for each cluster within thres of each other'''
    numbers.sort()
    prev = -1
    ret = []
    for n in numbers:
        if prev < 0 or n - prev > thres:
            ret.append(n)
            prev = n
    return ret

def _split_vlines_hlines(lines):
    '''Separates lines into horizontal and vertical ones'''
    vlines, hlines = [], []
    for line in lines:
        (vlines if line.x1 - line.x0 < 0.1 else hlines).append(line)
    return vlines, hlines

def _npiter(arr):
    '''Wrapper for iterating numpy array'''
    for a in np.nditer(arr, flags=['refs_ok']):
        c = a.item()
        if c is not None:
            yield c

