import math
import numpy as np
import itertools
from PIL import Image
#edited code begin
from shapely.ops import cascaded_union
from shapely.geometry.polygon import *
#edited code end

def make_polygon(area):
    return Polygon([(area['x1'], area['y1']), (area['x1'], area['y2']), (area['x2'], area['y2']), (area['x2'], area['y1']), (area['x1'], area['y1'])])


def polygon_to_extract(polygon):
    bounds = polygon.bounds
    return {
        'x1': bounds[0],
        'y1': bounds[1],
        'x2': bounds[2],
        'y2': bounds[3]
    }


def union_extracts(extracts):
    unioned = cascaded_union([ make_polygon(p) for p in extracts ])

    if unioned.geom_type == 'Polygon':
        return [ polygon_to_extract(unioned) ]
    else:
        return [ polygon_to_extract(geom) for geom in unioned ]


def extract_table(doc, page, extract):
    #edited code
    extract_entries = ['x1', 'y1', 'x2', 'y2']
    for extract_ent in extract_entries:
        if(type(extract[extract_ent])==float):
            extract[extract_ent] = int(extract[extract_ent])
    #edited code
    image = Image.open('%s/png/page_%s.png' % (doc, page))
    image.crop((extract['x1'], extract['y1'], extract['x2'], extract['y2'])).save(doc + '/tables/page_' + str(page) + '_' + extract['name'].replace(' ', '_').replace('.', '') + '.png', 'png')


def enlarge_extract(extract, area):
    return {
        'x1': min([extract['x1'], area['x1']]),
        'y1': min([extract['y1'], area['y1']]),
        'x2': max([extract['x2'], area['x2']]),
        'y2': max([extract['y2'], area['y2']])
    }


def rectangles_intersect(a, b):
    # Determine whether or not two rectangles intersect
    if (a['x1'] < b['x2']) and (a['x2'] > b['x1']) and (a['y1'] < b['y2']) and (a['y2'] > b['y1']):
        return True
    else:
        return False


def extractbbox(title):
    # Given a tesseract title string, extract the bounding box coordinates
    for part in title.split(';'):
        if part.strip()[0:4] == 'bbox':
            bbox = part.replace('bbox', '').strip().split()
            return {
                'x1': int(bbox[0]),
                'y1': int(bbox[1]),
                'x2': int(bbox[2]),
                'y2': int(bbox[3])
            }
    return {}


def meanOfDifferences(d):
    return np.nanmean([abs(each[0] - each[1]) for each in  list(itertools.combinations(d, 2))])


def centroid(x):
    return {
        'x': x['x1'] + (float(x['x2'] - x['x1']) / 2),
        'y': x['y1'] + (float(x['y2'] - x['y1']) / 2)
    }


def min_distance(a, b):
    # Calculate 3 different distances and return the best one
    return min([ distance(a, b), top_left_distance(a, b), bottom_right_distance(a, b) ])

def top_left_distance(a, b):
    return abs(math.sqrt(math.pow((b['x1'] - a['x1']), 2) + math.pow((b['y1'] - a['y1']), 2)))

def bottom_right_distance(a, b):
    return abs(math.sqrt(math.pow((b['x2'] - a['x2']), 2) + math.pow((b['y2'] - a['y2']), 2)))

def distance(a, b):
    centroid_a = centroid(a)
    centroid_b = centroid(b)
    return abs(math.sqrt(math.pow((centroid_b['x'] - centroid_a['x']), 2) + math.pow((centroid_b['y'] - centroid_a['y']), 2)))

def get_gaps(x_axis):
    '''
    Presence of contiguous vertical white space is a good indicator that
    an area is a table. Given a list of 0s (white space) and 1s (content)
    returns a list of integers that correspond to contiguous pixels of
    whitespace.
    Ex: [1,1,1,1,0,0,0,0,0,0,1,1,0,0,0,0] -> [6, 4]
    '''
    gaps = []
    currentGap = 0
    for x in x_axis:
        if x == 1:
            if currentGap != 0:
                gaps.append(currentGap)
            currentGap = 0
        else:
            currentGap += 1

    return gaps


def expand_area(input_area, all_areas):
    text_blocks = [area for area in all_areas if area['type'] == 'text block']
    candidate_areas = [area for area in all_areas if area['type'] != 'text block' and area['type'] != 'decoration']

    extract = {
        'x1': input_area['x1'],
        'y1': input_area['y1'],
        'x2': input_area['x2'],
        'y2': input_area['y2']
    }

    for area in candidate_areas:
        # Create a geometry that is the current extract + the current area
        candidate_new_extract = enlarge_extract(extract, area)

        valid_extraction = True
        for block in text_blocks:
            will_intersect = rectangles_intersect(candidate_new_extract, block)
            if will_intersect:
                valid_extraction = False

        if valid_extraction:
            extract.update(candidate_new_extract)

    return extract

# Translated from the C++ implementation found here - http://www.geeksforgeeks.org/check-if-two-given-line-segments-intersect/
def lines_intersect(l1, l2):

    def on_segment(p1, p2, p3):
        if (
           (p2['x'] <= max([p1['x'], p3['x']])) and
           (p2['x'] >= min([p1['x'], p3['x']])) and
           (p2['y'] <= max([p1['y'], p3['y']])) and
           (p2['y'] >= min([p1['y'], p3['y']]))
         ):
            return True
        else:
            return False

    def orientation(p1, p2, p3):
        val = ((p2['y'] - p1['y']) * (p3['x'] - p2['x'])) - ((p2['x'] - p1['x']) * (p3['y'] - p2['y']))

        # colinear
        if val == 0:
            return 0
        # clockwise
        elif val > 0:
            return 1
        # counterclockwise
        else:
            return 2

    o1 = orientation({
        'x': l1['x1'],
        'y': l1['y1']
    }, {
        'x': l1['x2'],
        'y': l1['y2']
    }, {
        'x': l2['x1'],
        'y': l2['y1']
    })

    o2 = orientation({
        'x': l1['x1'],
        'y': l1['y1']
    }, {
        'x': l1['x2'],
        'y': l1['y2']
    }, {
        'x': l2['x2'],
        'y': l2['y2']
    })

    o3 = orientation({
        'x': l2['x1'],
        'y': l2['y1']
    }, {
        'x': l2['x2'],
        'y': l2['y2']
    }, {
        'x': l1['x1'],
        'y': l1['y1']
    })

    o4 = orientation({
        'x': l2['x1'],
        'y': l2['y1']
    }, {
        'x': l2['x2'],
        'y': l2['y2']
    }, {
        'x': l1['x2'],
        'y': l1['y2']
    })

    if o1 != o2 and o3 != o4:
        return True

    # Special cases
    if o1 == 0 and on_segment({
        'x': l1['x1'],
        'y': l1['y2']
    }, {
        'x': l2['x1'],
        'y': l2['y1']
    }, {
        'x': l1['x2'],
        'y': l1['y2']
    }):
        return True

    if o2 == 0 and on_segment({
        'x': l1['x1'],
        'y': l1['y1']
    }, {
        'x': l2['x2'],
        'y': l2['y2']
    }, {
        'x': l1['x2'],
        'y': l1['y2']
    }):
        return True

    if o3 == 0 and on_segment({
        'x': l2['x1'],
        'y': l2['y1']
    }, {
        'x': l1['x1'],
        'y': l1['y1']
    }, {
        'x': l2['x2'],
        'y': l2['y2']
    }):
        return True

    if o4 == 0 and on_segment({
        'x': l2['x1'],
        'y': l2['y1']
    }, {
        'x': l1['x2'],
        'y': l1['y2']
    }, {
        'x': l2['x2'],
        'y': l2['y2']
    }):
        return True

    return False
