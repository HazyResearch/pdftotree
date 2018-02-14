'''
Handles abstract rendering of the layout
in order to extract local visual features

Created on Jan 28, 2016

@author: xiao
'''
from pdf.vector_utils import *
import logging
import numpy as np

class Renderer(object):
    '''
    enumeration objects to be placed into the
    rendered image
    '''
    empty = 0
    horizontal_line = -1
    vertical_line = -2
    text = -3
    img = -4
    curve = -5
    misc = -6

    def __init__(self, elems, scaler = 1):
        '''
        Initializes the rendered object grid with specified
        scaler so we can map original coordinates into the
        new grid map.
        '''
        self.log = logging.getLogger(__name__)
        self.scaler = scaler
        layout = elems.layout
        width = int(np.ceil(scaler * layout.width))
        height = int(np.ceil(scaler * layout.height))

        self.grid = np.zeros((width, height), dtype = np.int8)

        # Estimates the grid size in megabytes
        self.log.info(self.grid.nbytes/float(1048576))
        for line in elems.segments:
            if line.height < 0.1:  # Horizontal lines
                self.draw_rect(line.bbox, self.horizontal_line)
            elif line.width < 0.1:# Vertical lines
                self.draw_rect(line.bbox, self.vertical_line)

        for mention in elems.mentions:
            self.draw_rect(mention.bbox, self.text)

        for figure in elems.figures:
            self.draw_rect(figure.bbox, self.img)

    def draw_rect(self, bbox, cell_val):
        '''
        Fills the bbox with the content values
        Float bbox values are normalized to have non-zero area
        '''
        new_x0 = int(bbox[x0])
        new_y0 = int(bbox[y0])
        new_x1 = max(new_x0 + 1, int(bbox[x1]))
        new_y1 = max(new_y0 + 1, int(bbox[y1]))

        self.grid[new_x0:new_x1,new_y0:new_y1] = cell_val

    @staticmethod
    def is_mention(cell_val):
        '''
        Nonnegative values in grid cells are reserved for mention ids
        '''
        return cell_val >= 0

