'''
Created on Oct 26, 2015
Parsing raw PDF data into python data structures

@author: xiao
'''
from __future__ import division
from builtins import filter
from builtins import str
from builtins import zip
from builtins import range
import logging
import math
import operator
from collections import defaultdict
from copy import deepcopy
from functools import cmp_to_key
from pdfminer.utils import Plane
from pdftotree.pdf.layout_utils import *
from pdftotree.pdf.node import Node

log = logging.getLogger(__name__)


def parse_layout(elems, font_stat, combine=False):
    '''
    Parses pdf texts into a hypergraph grouped into rows
    and columns and then output
    '''
    boxes_segments = elems.segments
    boxes_curves = elems.curves
    boxes_figures = elems.figures
    page_width = elems.layout.width
    page_height = elems.layout.height
    boxes = elems.mentions
    avg_font_pts = get_most_common_font_pts(elems.mentions, font_stat)
    width = get_page_width(
        boxes + boxes_segments + boxes_figures + boxes_curves)
    char_width = get_char_width(boxes)
    grid_size = avg_font_pts / 2.0
    for i, m in enumerate(boxes + elems.figures):
        m.id = i
        m.feats = defaultdict(bool)
        prefix = ''
        if isinstance(m, LTTextLine) and m.font_name:
            prefix = m.font_name + '-' + str(m.font_size) + '-'
        m.xc = (m.x0 + m.x1) / 2.0
        m.yc = (m.y0 + m.y1) / 2.0
        m.feats[prefix + 'x0'] = m.x0_grid = m.x0 // grid_size
        m.feats[prefix + 'x1'] = m.x1_grid = m.x1 // grid_size
        m.feats[prefix + 'xc'] = m.xc_grid = m.xc // grid_size
        m.feats[prefix + 'yc'] = m.yc_grid = m.yc // grid_size

    tbls, tbl_features = cluster_vertically_aligned_boxes(
        boxes, elems.layout.bbox, avg_font_pts, width, char_width,
        boxes_segments, boxes_curves, boxes_figures, page_width, combine)
    return tbls, tbl_features


def cluster_vertically_aligned_boxes(boxes, page_bbox, avg_font_pts, width,
                                     char_width, boxes_segments, boxes_curves,
                                     boxes_figures, page_width, combine):
    # Too many "." in the Table of Content pages
    if (len(boxes) == 0 or len(boxes) > 3500):
        return []
    plane = Plane(page_bbox)
    plane.extend(boxes)

    # initialize clusters
    cid2obj = [set([i]) for i in range(len(boxes))]
    # default object map to cluster with its own index
    obj2cid = list(range(len(boxes)))
    prev_clusters = obj2cid
    while (True):
        for i1, b1 in enumerate(boxes):
            for i2, b2 in enumerate(boxes):
                if ((i1 == i2) or (obj2cid[i1] == obj2cid[i2])):
                    continue
                if (b1.bbox[1] < b2.bbox[1]):
                    box1 = b1.bbox
                    box2 = b2.bbox
                elif (b2.bbox[1] < b1.bbox[1]):
                    box1 = b2.bbox
                    box2 = b1.bbox
                else:
                    # horizontally aligned
                    continue
                if (box2[1] < box1[3]
                        or (box2[1] - box1[1] < 1.5 * avg_font_pts)
                        or (box2[3] - box1[3] < 1.5 * avg_font_pts)):
                    # can probably do better if we find the average space
                    # between words
                    if (abs(box1[0] - box2[0]) < 3
                            or abs(box1[2] - box2[2]) < 3
                            or (((box1[0] + box1[2]) / 2) == (
                                (box2[0] + box2[2]) / 2))
                            or ((box1[0] < box2[0]) and (box1[2] > box2[0]))
                            or ((box1[0] > box2[0]) and (box2[2] > box1[0]))):
                        min_i = min(i1, i2)
                        max_i = max(i1, i2)
                        cid1 = obj2cid[min_i]
                        cid2 = obj2cid[max_i]
                        # move all objects from cluster cid2 to cid1
                        # reassign cluster ids for all such objects as well
                        for obj_iter in cid2obj[cid2]:
                            cid2obj[cid1].add(obj_iter)
                            obj2cid[obj_iter] = cid1
                        cid2obj[cid2] = set()
        if (prev_clusters == obj2cid):
            break
        prev_clusters = obj2cid
    clusters = [[boxes[i] for i in cluster]
                for cluster in filter(bool, cid2obj)]

    rid2obj = [set([i]) for i in range(len(boxes))]  # initialize clusters
    # default object map to cluster with its own index
    obj2rid = list(range(len(boxes)))
    prev_clusters = obj2rid
    while (True):
        for i1, b1 in enumerate(boxes):
            for i2, b2 in enumerate(boxes):
                if ((i1 == i2) or (obj2rid[i1] == obj2rid[i2])):
                    continue
                box1 = b1.bbox
                box2 = b2.bbox
                if ((abs(box1[1] - box2[1]) < 0.11 * avg_font_pts)
                        or ((abs(box1[3] - box2[3]) < 0.11 * avg_font_pts))
                        or (round((box1[1] + box1[3]) / 2) == round(
                            (box2[1] + box2[3]) / 2))):
                    min_i = min(i1, i2)
                    max_i = max(i1, i2)
                    rid1 = obj2rid[min_i]
                    rid2 = obj2rid[max_i]
                    for obj_iter in rid2obj[rid2]:
                        rid2obj[rid1].add(obj_iter)
                        obj2rid[obj_iter] = rid1
                    rid2obj[rid2] = set()
        if (prev_clusters == obj2rid):
            break
        prev_clusters = obj2rid

    not_merge = set()
    for i1, b1 in enumerate(boxes):
        for i2 in cid2obj[obj2cid[i1]]:
            if (i1 == i2):
                continue
            row1 = obj2rid[i1]
            row2 = obj2rid[i2]
            if (row1 == row2):
                continue
            if (b1.bbox[1] < b2.bbox[1]):
                box1 = b1.bbox
                box2 = b2.bbox
            elif (b2.bbox[1] < b1.bbox[1]):
                box1 = b2.bbox
                box2 = b1.bbox
            else:
                # horizontally aligned
                continue
            text_1 = 0.0
            for obj in rid2obj[row1]:
                text_1 += boxes[obj].bbox[2] - boxes[obj].bbox[0]
            text_2 = 0.0
            for obj in rid2obj[row2]:
                text_2 += boxes[obj].bbox[2] - boxes[obj].bbox[0]
            if (abs(text_1 - text_2) / width > 0.1):
                min_i = min(i1, i2)
                max_i = max(i1, i2)
                not_merge.add((min_i, max_i))

    # Alignment Features
    # If text boxes are very close in a row
    if_row_connected = defaultdict(int)
    num_row_connected = defaultdict(lambda: 1)
    # If text is merged using span code in adjacent rows, this feature tells the number of times the cluster went through span based clustering
    if_connected_by_span = defaultdict(int)
    num_connected_by_span = defaultdict(lambda: 1)
    # If columns were merged using cluster alignment
    if_connected_by_align = defaultdict(int)
    num_connected_by_align = defaultdict(lambda: 1)
    # If vertical columns were merged
    if_vertical_columns_merged = defaultdict(int)
    num_vertical_columns_merged = defaultdict(lambda: 1)
    # Number of Line Segments, Curves and Figures
    num_segments = defaultdict(int)
    num_curves = defaultdict(int)
    num_figures = defaultdict(int)
    # Average Word Space
    total_word_space = defaultdict(float)
    avg_word_space = defaultdict(float)
    avg_word_space_norm = defaultdict(float)
    node_space = defaultdict(float)
    avg_node_space = defaultdict(float)
    avg_node_space_norm = defaultdict(float)

    cid2obj = [set([i]) for i in range(len(boxes))]  # initialize clusters
    obj2cid = list(range(
        len(boxes)))  # default object map to cluster with its own index
    prev_clusters = obj2cid
    # add the code for merging close text boxes in particular row
    while (True):
        for i1, b1 in enumerate(boxes):
            for i2, b2 in enumerate(boxes):
                if ((i1 == i2) or (obj2cid[i1] == obj2cid[i2])):
                    continue
                box1 = b1.bbox
                box2 = b2.bbox
                if (obj2rid[i1] == obj2rid[i2]):
                    if (((b1.bbox[0] < b2.bbox[0]) and
                         ((b2.bbox[0] - b1.bbox[2]) <= 2 * char_width)) or
                        ((b2.bbox[0] < b1.bbox[0]) and
                         ((b1.bbox[0] - b2.bbox[2]) <= 2 * char_width))):
                        min_i = min(i1, i2)
                        max_i = max(i1, i2)
                        cid1 = obj2cid[min_i]
                        cid2 = obj2cid[max_i]
                        for obj_iter in cid2obj[cid2]:
                            cid2obj[cid1].add(obj_iter)
                            obj2cid[obj_iter] = cid1
                        cid2obj[cid2] = set()
                        # Features
                        if_row_connected[cid1] = 1
                        if_row_connected[cid2] = 0
                        num_row_connected[cid1] += num_row_connected[cid2]
                        num_row_connected[cid2] = 0
        if (prev_clusters == obj2cid):
            break
        prev_clusters = obj2cid

    # vertical alignment code
    while (True):
        for i1, b1 in enumerate(boxes):
            for i2, b2 in enumerate(boxes):
                if ((i1 == i2) or (obj2cid[i1] == obj2cid[i2])):
                    continue
                if (b1.bbox[1] < b2.bbox[1]):
                    box1 = b1.bbox
                    box2 = b2.bbox
                elif (b2.bbox[1] < b1.bbox[1]):
                    box1 = b2.bbox
                    box2 = b1.bbox
                else:
                    # horizontally aligned
                    continue
                if (
                        box2[1] < box1[3]
                        or (box2[1] - box1[1] < 1.5 * avg_font_pts)
                        or (box2[3] - box1[3] < 1.5 * avg_font_pts)
                ):  # can probably do better if we find the average space between words
                    if (
                            abs(box1[0] - box2[0]) < 3
                            or abs(box1[2] - box2[2]) < 3
                            or (((box1[0] + box1[2]) / 2) == (
                                (box2[0] + box2[2]) / 2))
                    ):  # or ((box1[0]<box2[0]) and (box1[2]>box2[0])) or ((box1[0]>box2[0]) and (box2[2]>box1[0]))): #added center alignemnt
                        min_i = min(i1, i2)
                        max_i = max(i1, i2)
                        if ((min_i, max_i) not in not_merge):
                            cid1 = obj2cid[min_i]
                            cid2 = obj2cid[max_i]
                            # move all objects from cluster cid2 to cid1
                            # reassign cluster ids for all such objects as well
                            for obj_iter in cid2obj[cid2]:
                                cid2obj[cid1].add(obj_iter)
                                obj2cid[obj_iter] = cid1
                            cid2obj[cid2] = set()
                            # Features
                            if_connected_by_span[cid1] = 1
                            if_connected_by_span[cid2] = 0
                            if (if_row_connected[cid1] == 1
                                    or if_row_connected[cid2] == 1):
                                if_row_connected[cid1] = 1
                                num_row_connected[cid1] += num_row_connected[
                                    cid2]
                                num_row_connected[cid2] = 0
                                if_row_connected[cid2] = 0
                            num_connected_by_span[
                                cid1] = num_connected_by_span[cid1] + num_connected_by_span[cid2]
                            num_connected_by_span[cid2] = 0
        if (prev_clusters == obj2cid):
            break
        prev_clusters = obj2cid

    # blacklist nearly half-page wide clusters before horizontal merging
    cid2obj2 = cid2obj[:]
    obj2cid2 = obj2cid[:]
    blacklist = set()
    blacklist_obj = set()
    for cid_iter in range(len(cid2obj2)):
        cid = cid2obj2[cid_iter]
        xmin = float("Inf")
        xmax = float("-Inf")
        for obj in cid:
            xmin = min(xmin, boxes[obj].bbox[0])
            xmax = max(xmax, boxes[obj].bbox[2])
        if (((xmax - xmin) > width / 2.75 and (xmax - xmin) < width / 2)
                or ((xmax - xmin) > 0.9 * width)):
            blacklist.add(cid_iter)
            for obj in cid:
                blacklist_obj.add(obj)
                for obj_iter in rid2obj[obj2rid[obj]]:
                    if (boxes[obj_iter].bbox[0] >= xmin
                            and boxes[obj_iter].bbox[2] <= xmax):
                        blacklist_obj.add(obj_iter)

    # create a cluster span
    cid2span = {}
    for cid in range(len(cid2obj)):
        cid2span[cid] = {}
        cid2span[cid]["min_x"] = float("Inf")
        cid2span[cid]["min_y"] = float("Inf")
        cid2span[cid]["max_x"] = float("-Inf")
        cid2span[cid]["max_y"] = float("-Inf")
        for obj in cid2obj[cid]:
            cid2span[cid]["min_x"] = min(cid2span[cid]["min_x"],
                                         boxes[obj].bbox[0])
            cid2span[cid]["max_x"] = max(cid2span[cid]["max_x"],
                                         boxes[obj].bbox[2])
            cid2span[cid]["min_y"] = min(cid2span[cid]["min_y"],
                                         boxes[obj].bbox[1])
            cid2span[cid]["max_y"] = max(cid2span[cid]["max_y"],
                                         boxes[obj].bbox[3])

    cid2cid = {}
    cid_pair_compared = set()
    cid2cid2 = [cid for cid in range(len(cid2obj))]
    for i1, b1 in enumerate(boxes):
        for i2, b2 in enumerate(boxes):
            if (i1 == i2):
                continue
            if (i1 in blacklist_obj or i2 in blacklist_obj):
                continue
            cid1 = obj2cid[i1]
            cid2 = obj2cid[i2]
            if ((min(cid1, cid2), max(cid1, cid2)) in cid_pair_compared):
                continue
            if (cid1 == cid2):
                continue
            if (obj2rid[i1] == obj2rid[i2]):
                continue
            if (cid1 not in cid2cid):
                cid2cid[cid1] = set()
            if (cid2 not in cid2cid):
                cid2cid[cid2] = set()
            if (cid2span[cid1]["min_y"] < cid2span[cid2]["min_y"]):
                box1 = [
                    cid2span[cid1]["min_x"], cid2span[cid1]["min_y"],
                    cid2span[cid1]["max_x"], cid2span[cid1]["max_y"]
                ]
                box2 = [
                    cid2span[cid2]["min_x"], cid2span[cid2]["min_y"],
                    cid2span[cid2]["max_x"], cid2span[cid2]["max_y"]
                ]
            else:
                box1 = [
                    cid2span[cid2]["min_x"], cid2span[cid2]["min_y"],
                    cid2span[cid2]["max_x"], cid2span[cid2]["max_y"]
                ]
                box2 = [
                    cid2span[cid1]["min_x"], cid2span[cid1]["min_y"],
                    cid2span[cid1]["max_x"], cid2span[cid1]["max_y"]
                ]
            if (((box1[1] < box2[1]) and (box1[3] > box2[1]))
                    or ((box1[1] > box2[1]) and (box1[1] < box2[3]))):
                continue
            cid_pair_compared.add((min(cid1, cid2), max(cid1, cid2)))
            query_rect = (min(box1[0], box2[0]), min(box1[1], box2[1]),
                          max(box1[2], box2[2]), max(box1[3], box2[3]))
            connected = True
            for i3, b3 in enumerate(boxes):
                if ((i3 == i1) or (i3 == i2)):
                    continue
                if (obj2cid[i1] == obj2cid[i3] or obj2cid[i2] == obj2cid[i3]):
                    continue
                box3 = b3.bbox
                if (intersect(query_rect, box3)):
                    connected = False
                    break
            if (
                ((round(box1[0]) == round(box2[0])
                  or round(box1[2]) == round(box2[2])) and connected)
                    or (round((box1[0] + box1[2]) / 2) == round(
                        (box2[0] + box2[2]) / 2) and connected)
            ):  # or (abs((box1[0]+box1[2])/2-(box2[0]+box2[2])/2)<0.1*char_width and connected)):# or ((box1[0]<box2[0]) and (box1[2]>box2[0])) or ((box1[0]>box2[0]) and (box2[2]>box1[0]))): #added center alignemnt
                cid2cid[min(cid1, cid2)].add(max(cid1, cid2))
                min_cid = min(cid1, cid2)
                max_cid = max(cid1, cid2)
                for cid_iter in cid2cid2:
                    if (cid2cid2[cid_iter] == cid2cid2[max_cid]):
                        cid2cid2[cid_iter] = cid2cid2[min_cid]

    # post-process cid2cid
    cid2obj2 = cid2obj[:]
    obj2cid2 = obj2cid[:]
    for cid in range(len(cid2cid2)):
        cid_merge = cid2cid2[cid]
        if (cid != cid_merge):
            for obj_iter in cid2obj2[cid]:
                cid2obj2[cid_merge].add(obj_iter)
                obj2cid2[obj_iter] = cid_merge
            cid2obj2[cid] = set()
            # Features
            if_connected_by_align[cid_merge] = 1
            if_connected_by_align[cid] = 0
            if (if_row_connected[cid_merge] == 1
                    or if_row_connected[cid] == 1):
                if_row_connected[cid_merge] = 1
                num_row_connected[cid_merge] += num_row_connected[cid]
                num_row_connected[cid] = 0
                if_row_connected[cid2] = 0
            if (if_connected_by_span[cid_merge] == 1
                    or if_connected_by_span[cid] == 1):
                if_connected_by_span[cid_merge] = 1
                num_connected_by_span[cid_merge] += num_connected_by_span[cid]
                num_connected_by_span[cid] = 0
                if_connected_by_span[cid] = 0
            num_connected_by_align[cid_merge] += num_connected_by_align[cid]
            num_connected_by_align[cid] = 0

            # code to merge columns for table
    prev_clusters = obj2cid2
    while (True):
        for obj1, b1 in enumerate(boxes):
            cid1 = obj2cid2[obj1]
            rid1 = obj2rid[obj1]
            if (cid1 in blacklist):
                continue
            if (obj1 in blacklist_obj):
                continue
            for obj2, b2 in enumerate(boxes):
                if (obj1 == obj2):
                    continue
                if (obj2cid2[obj2] == cid1):
                    rid2 = obj2rid[obj2]
                    if (rid1 == rid2):
                        continue
                    for obj3 in rid2obj[rid2]:
                        cid3 = obj2cid2[obj3]
                        if (obj3 in blacklist_obj):
                            continue
                        if (cid1 != cid3):
                            for obj4 in cid2obj2[cid3]:
                                if (obj4 == obj3):
                                    continue
                                if (obj2rid[obj4] == rid1):
                                    min_cid = min(cid1, cid3)
                                    max_cid = max(cid1, cid3)
                                    for obj_iter in cid2obj2[max_cid]:
                                        cid2obj2[min_cid].add(obj_iter)
                                        obj2cid2[obj_iter] = min_cid
                                    cid2obj2[max_cid] = set()
                                    # Features
                                    if_vertical_columns_merged[min_cid] = 1
                                    if_vertical_columns_merged[max_cid] = 0
                                    num_vertical_columns_merged[
                                        min_cid] += num_vertical_columns_merged[
                                            max_cid]
                                    num_vertical_columns_merged[max_cid] = 0
                                    if (if_row_connected[min_cid] == 1
                                            or if_row_connected[max_cid] == 1):
                                        if_row_connected[min_cid] = 1
                                        num_row_connected[
                                            min_cid] += num_row_connected[
                                                max_cid]
                                        num_row_connected[max_cid] = 0
                                        if_row_connected[max_cid] = 0
                                    if (if_connected_by_span[min_cid] == 1 or
                                            if_connected_by_span[max_cid] == 1
                                        ):
                                        if_connected_by_span[min_cid] = 1
                                        num_connected_by_span[
                                            min_cid] += num_connected_by_span[
                                                max_cid]
                                        num_connected_by_span[max_cid] = 0
                                        if_connected_by_span[max_cid] = 0
                                    if (if_connected_by_align[min_cid] == 1 or
                                            if_connected_by_align[max_cid] == 1
                                        ):
                                        if_connected_by_align[min_cid] = 1
                                        num_connected_by_align[
                                            min_cid] += num_connected_by_align[
                                                max_cid]
                                        num_connected_by_align[max_cid] = 0
                                        if_connected_by_align[max_cid] = 0
                                    break
        if (prev_clusters == obj2cid2):
            break
        prev_clusters = obj2cid2

    clusters = [[boxes[i] for i in cluster]
                for cluster in filter(bool, cid2obj2)]
    nodes = [Node(elems) for elems in clusters]
    node_indices = [i for i, x in enumerate(cid2obj2) if x]
    merge_indices = [i for i in range(len(node_indices))]
    page_stat = Node(boxes)
    nodes, merge_indices = merge_nodes(nodes, plane, page_stat, merge_indices)
    # Features
    for idx in range(len(merge_indices)):
        if (merge_indices[idx] != idx):
            cid1 = node_indices[merge_indices[idx]]
            cid2 = node_indices[idx]
            if (if_row_connected[cid1] == 1 or if_row_connected[cid2] == 1):
                if_row_connected[cid1] = 1
                num_row_connected[cid1] += num_row_connected[cid2]
                num_row_connected[cid2] = 0
                if_row_connected[cid2] = 0
            if (if_connected_by_span[cid1] == 1
                    or if_connected_by_span[cid2] == 1):
                if_connected_by_span[cid1] = 1
                num_connected_by_span[cid1] += num_connected_by_span[cid2]
                num_connected_by_span[cid2] = 0
                if_connected_by_span[cid2] = 0
            if (if_connected_by_align[cid1] == 1
                    or if_connected_by_align[cid2] == 1):
                if_connected_by_align[cid1] = 1
                num_connected_by_align[cid1] += num_connected_by_align[cid2]
                num_connected_by_align[cid2] = 0
                if_connected_by_align[cid2] = 0
            if (if_vertical_columns_merged[cid1] == 1
                    or if_vertical_columns_merged[cid2] == 1):
                if_vertical_columns_merged[cid1] = 1
                num_vertical_columns_merged[
                    cid1] += num_vertical_columns_merged[cid2]
                num_vertical_columns_merged[cid2] = 0
                if_vertical_columns_merged[cid2] = 0

    # Get Word Spacing Features
    rid2space = defaultdict(float)
    rid2space_norm = defaultdict(float)
    row_indices = [i for i, x in enumerate(rid2obj) if x]
    for rid in row_indices:
        obj_list = list(rid2obj[rid])
        if (len(obj_list) == 1):
            rid2space[rid] = 0
            continue
        obj_boxes = [boxes[obj].bbox[0] for obj in obj_list]
        sorted_obj_idx = [
            i[0] for i in sorted(enumerate(obj_boxes), key=lambda x: x[1])
        ]
        for obj_idx in range(len(sorted_obj_idx) - 1):
            rid2space[rid] += boxes[obj_list[sorted_obj_idx[obj_idx + 1]]].bbox[2] - \
                              boxes[obj_list[sorted_obj_idx[obj_idx]]].bbox[0]
        rid2space_norm[rid] = rid2space[rid] / (len(obj_list) - 1)

    for idx, node in enumerate(nodes):
        node_idx = node_indices[idx]
        if (merge_indices[idx] == idx):
            obj_list = []
            for idx_iter in range(len(merge_indices)):
                if (merge_indices[idx_iter] == idx):
                    obj_list += list(cid2obj2[node_indices[idx_iter]])
            obj_list = list(set(obj_list))
            rid_list = list(set([obj2rid[obj] for obj in obj_list]))
            for rid in rid_list:
                total_word_space[node_idx] += rid2space[rid]
                avg_word_space_norm[node_idx] += rid2space_norm[rid]
                obj_boxes = [
                    boxes[obj].bbox[0] for obj in rid2obj
                    if obj in cid2obj2[node_idx]
                ]
                sorted_obj_idx = [
                    i[0]
                    for i in sorted(enumerate(obj_boxes), key=lambda x: x[1])
                ]
                for obj_idx in range(len(sorted_obj_idx) - 1):
                    node_space[node_idx] += boxes[obj_list[sorted_obj_idx[obj_idx + 1]]].bbox[2] - \
                                            boxes[obj_list[sorted_obj_idx[obj_idx]]].bbox[0]
                avg_node_space_norm[node_idx] += node_space[node_idx] / (
                    len(obj_boxes) - 1)
            avg_word_space[node_idx] = total_word_space[node_idx] / len(
                rid_list)
            avg_word_space_norm[node_idx] /= len(rid_list)
            avg_node_space[node_idx] = node_space[node_idx] / len(rid_list)
            avg_node_space_norm[node_idx] /= len(rid_list)

    new_nodes = []
    new_node_indices = []
    for idx in range(len(merge_indices)):
        if (merge_indices[idx] == idx):
            new_nodes.append(nodes[idx])
            new_node_indices.append(node_indices[idx])

    nodes = new_nodes
    node_indices = new_node_indices
    # Features
    for idx, node in enumerate(nodes):
        node_idx = node_indices[idx]
        node_bbox = (node.x0, node.y0, node.x1, node.y1)
        for i1, b1 in enumerate(boxes_segments):
            if (intersect(node_bbox, b1.bbox)):
                num_segments[node_idx] += 1
        for i1, b1 in enumerate(boxes_figures):
            if (intersect(node_bbox, b1.bbox)):
                num_figures[node_idx] += 1
        for i1, b1 in enumerate(boxes_curves):
            if (intersect(node_bbox, b1.bbox)):
                num_curves[node_idx] += 1

    tables = []
    table_indices = []
    for idx, node in enumerate(nodes):
        node_idx = node_indices[idx]
        isTable = True
        if node.is_table():
            for elem in node.elems:
                if ("table" in elem.get_text().lower()):
                    continue
                if ((node.width - elem.bbox[2] + elem.bbox[0]) <
                        2 * char_width):
                    isTable = False
            if (isTable):
                tables.append(node)
                table_indices.append(node_idx)

    if (combine == True):
        node_features = [0] * 17
        for idx, node in enumerate(nodes):
            node_idx = node_indices[idx]
            node_features = [
                sum(x) for x in zip(node_features, [
                    if_row_connected[node_idx], num_row_connected[node_idx],
                    if_connected_by_span[node_idx],
                    num_connected_by_span[node_idx],
                    if_connected_by_align[node_idx],
                    num_connected_by_align[node_idx],
                    if_vertical_columns_merged[node_idx],
                    num_vertical_columns_merged[node_idx],
                    num_segments[node_idx], num_curves[node_idx],
                    num_figures[node_idx], total_word_space[node_idx],
                    avg_word_space[node_idx], avg_word_space_norm[node_idx],
                    node_space[node_idx], avg_node_space[node_idx],
                    avg_node_space_norm[node_idx]
                ])
            ]
        return [], node_features
    else:
        table_features = []
        for idx, table in enumerate(tables):
            table_idx = table_indices[idx]
            table_features += [[
                if_row_connected[table_idx], num_row_connected[table_idx],
                if_connected_by_span[table_idx],
                num_connected_by_span[table_idx],
                if_connected_by_align[table_idx],
                num_connected_by_align[table_idx],
                if_vertical_columns_merged[table_idx],
                num_vertical_columns_merged[table_idx],
                num_segments[table_idx], num_curves[table_idx],
                num_figures[table_idx], total_word_space[table_idx],
                avg_word_space[table_idx], avg_word_space_norm[table_idx],
                node_space[table_idx], avg_node_space[table_idx],
                avg_node_space_norm[table_idx]
            ]]
        return tables, table_features


def parse_tree_structure(elems, font_stat, page_num, ref_page_seen, tables,
                         favor_figures):
    boxes_segments = elems.segments
    boxes_curves = elems.curves
    boxes_figures = elems.figures
    page_width = elems.layout.width
    page_height = elems.layout.height
    mentions = elems.mentions

    avg_font_pts = get_most_common_font_pts(elems.mentions, font_stat)
    width = get_page_width(
        mentions + boxes_segments + boxes_figures + boxes_curves)

    try:
        char_width = get_char_width(mentions)
    except:
        char_width = 2

    grid_size = avg_font_pts / 2.0

    # Atomic features and marking initialization
    for i, m in enumerate(mentions + boxes_figures):
        m.id = i
        m.feats = defaultdict(bool)
        prefix = ''
        if isinstance(m, LTTextLine) and m.font_name:
            prefix = m.font_name + '-' + str(m.font_size) + '-'
        # center X coordinate
        m.xc = (m.x0 + m.x1) / 2.0
        m.yc = (m.y0 + m.y1) / 2.0
        # Here we snap the elements to its closest grid line to detect rows/columns
        m.feats[prefix + 'x0'] = m.x0_grid = m.x0 // grid_size
        m.feats[prefix + 'x1'] = m.x1_grid = m.x1 // grid_size
        m.feats[prefix + 'xc'] = m.xc_grid = m.xc // grid_size
        m.feats[prefix + 'yc'] = m.yc_grid = m.yc // grid_size

    #Figures for this page
    figures_page = get_figures(mentions, elems.layout.bbox, page_num,
                               boxes_figures, page_width, page_height)

    #Omit tables that overlap with figures if figures need to be favored
    if favor_figures == "True":
        tables_page = []
        for idx, table in enumerate(tables):
            table_box = tuple(table[3:])
            intersect = False
            for fig in figures_page:
                bool_overlap = (table_box[1] <= fig[6]
                                and fig[4] <= table_box[3]
                                and table_box[0] <= fig[5]
                                and fig[3] <= table_box[2])
                if (bool_overlap):
                    intersect = True
                    break
            if not intersect:
                tables_page.append(table)
    else:
        tables_page = tables

    ##Eliminate tables from these boxes
    boxes = []
    for idx1, box in enumerate(mentions):
        intersect = False
        for idx2, table in enumerate(tables_page):
            table_box = tuple(table[3:])
            bool_overlap = (table_box[1] <= box.bbox[2]
                            and box.bbox[0] <= table_box[3]
                            and table_box[0] <= box.bbox[3]
                            and box.bbox[1] <= table_box[2])
            if (bool_overlap):
                intersect = True
                break
        if (not intersect):
            boxes.append(box)

    text_candidates, ref_page_seen = extract_text_candidates(
        boxes, elems.layout.bbox, avg_font_pts, width, char_width, page_num,
        ref_page_seen, boxes_figures, page_width, page_height)
    text_candidates["figure"] = figures_page
    text_candidates["table"] = tables_page

    #Check overlap with figures if figures are favored
    pruned_text_candidates = {}
    if favor_figures == "True":
        for clust in text_candidates:
            pruned_text_candidates[clust] = []
            for idx, box in enumerate(text_candidates[clust]):
                clust_box = tuple(box[3:])
                intersect = False
                for fig in figures_page:
                    bool_overlap = (clust_box[1] <= fig[6]
                                    and fig[4] <= clust_box[3]
                                    and clust_box[0] <= fig[5]
                                    and fig[3] <= clust_box[2])
                    if (bool_overlap):
                        intersect = True
                        break
                if not intersect:
                    pruned_text_candidates[clust].append(box)
        pruned_text_candidates["figure"] = text_candidates["figure"]
    else:
        pruned_text_candidates = text_candidates

    return pruned_text_candidates, ref_page_seen


def extract_text_candidates(boxes, page_bbox, avg_font_pts, width, char_width,
                            page_num, ref_page_seen, boxes_figures, page_width,
                            page_height):
    #Too many "." in the Table of Content pages - ignore because it takes a lot of time
    if (len(boxes) == 0 or len(boxes) > 3500):
        return {}, False
    plane = Plane(page_bbox)
    plane.extend(boxes)

    #Row level clustering - identify objects that have same horizontal alignment
    rid2obj = [set([i]) for i in range(len(boxes))]  # initialize clusters
    obj2rid = list(range(
        len(boxes)))  # default object map to cluster with its own index
    prev_clusters = obj2rid
    while (True):
        for i1, b1 in enumerate(boxes):
            for i2, b2 in enumerate(boxes):
                if ((i1 == i2) or (obj2rid[i1] == obj2rid[i2])):
                    continue
                box1 = b1.bbox
                box2 = b2.bbox
                if ((abs(box1[1] - box2[1]) < 0.11 * avg_font_pts)
                        or ((abs(box1[3] - box2[3]) < 0.11 * avg_font_pts))
                        or (round((box1[1] + box1[3]) / 2) == round(
                            (box2[1] + box2[3]) / 2))):
                    min_i = min(i1, i2)
                    max_i = max(i1, i2)
                    rid1 = obj2rid[min_i]
                    rid2 = obj2rid[max_i]
                    for obj_iter in rid2obj[rid2]:
                        rid2obj[rid1].add(obj_iter)
                        obj2rid[obj_iter] = rid1
                    rid2obj[rid2] = set()
        if (prev_clusters == obj2rid):
            break
        prev_clusters = obj2rid

    cid2obj = [set([i]) for i in range(len(boxes))]  # initialize clusters
    obj2cid = list(range(
        len(boxes)))  # default object map to cluster with its own index
    prev_clusters = obj2cid

    #add the code for merging close text boxes in particular row
    while (True):
        for i1, b1 in enumerate(boxes):
            for i2, b2 in enumerate(boxes):
                if ((i1 == i2) or (obj2cid[i1] == obj2cid[i2])):
                    continue
                box1 = b1.bbox
                box2 = b2.bbox
                if (obj2rid[i1] == obj2rid[i2]):
                    if (((b1.bbox[0] < b2.bbox[0]) and
                         ((b2.bbox[0] - b1.bbox[2]) <= 2 * char_width)) or
                        ((b2.bbox[0] < b1.bbox[0]) and
                         ((b1.bbox[0] - b2.bbox[2]) <= 2 * char_width))):
                        min_i = min(i1, i2)
                        max_i = max(i1, i2)
                        cid1 = obj2cid[min_i]
                        cid2 = obj2cid[max_i]
                        for obj_iter in cid2obj[cid2]:
                            cid2obj[cid1].add(obj_iter)
                            obj2cid[obj_iter] = cid1
                        cid2obj[cid2] = set()
        if (prev_clusters == obj2cid):
            break
        prev_clusters = obj2cid

    #vertical alignment code
    while (True):
        for i1, b1 in enumerate(boxes):
            for i2, b2 in enumerate(boxes):
                if ((i1 == i2) or (obj2cid[i1] == obj2cid[i2])):
                    continue
                if (b1.bbox[1] < b2.bbox[1]):
                    box1 = b1.bbox
                    box2 = b2.bbox
                elif (b2.bbox[1] < b1.bbox[1]):
                    box1 = b2.bbox
                    box2 = b1.bbox
                else:
                    #horizontally aligned
                    continue
                if (abs((box2[3] - box2[1]) - (box1[3] - box1[1])) >
                        0.5 * avg_font_pts):
                    continue
                if (
                        box2[1] < box1[3]
                        or (box2[1] - box1[1] < 1.5 * avg_font_pts)
                        or (box2[3] - box1[3] < 1.5 * avg_font_pts)
                ):  #can probably do better if we find the average space between words
                    if (abs(box1[0] - box2[0]) < 3 * char_width
                            or abs(box1[2] - box2[2]) < 3 * char_width
                            or (((box1[0] + box1[2]) / 2) == (
                                (box2[0] + box2[2]) / 2))):
                        min_i = min(i1, i2)
                        max_i = max(i1, i2)
                        cid1 = obj2cid[min_i]
                        cid2 = obj2cid[max_i]
                        #move all objects from cluster cid2 to cid1
                        #reassign cluster ids for all such objects as well
                        for obj_iter in cid2obj[cid2]:
                            cid2obj[cid1].add(obj_iter)
                            obj2cid[obj_iter] = cid1
                        cid2obj[cid2] = set()
        if (prev_clusters == obj2cid):
            break
        prev_clusters = obj2cid

    #get cluster spans
    cid2span = {}
    for cid in range(len(cid2obj)):
        cid2span[cid] = {}
        cid2span[cid]["min_x"] = float("Inf")
        cid2span[cid]["min_y"] = float("Inf")
        cid2span[cid]["max_x"] = float("-Inf")
        cid2span[cid]["max_y"] = float("-Inf")
        for obj in cid2obj[cid]:
            cid2span[cid]["min_x"] = min(cid2span[cid]["min_x"],
                                         boxes[obj].bbox[0])
            cid2span[cid]["max_x"] = max(cid2span[cid]["max_x"],
                                         boxes[obj].bbox[2])
            cid2span[cid]["min_y"] = min(cid2span[cid]["min_y"],
                                         boxes[obj].bbox[1])
            cid2span[cid]["max_y"] = max(cid2span[cid]["max_y"],
                                         boxes[obj].bbox[3])

    #Don't split up references
    references_bbox = []
    references_cid = set()
    for cid in range(len(cid2obj)):
        if (len(cid2obj[cid]) == 1):
            if (boxes[list(
                    cid2obj[cid])[0]].get_text().lower() == "references"):
                references_bbox = [
                    cid2span[cid]["min_x"], cid2span[cid]["min_y"],
                    cid2span[cid]["max_x"], cid2span[cid]["max_y"]
                ]
                for cid2 in range(len(cid2obj)):
                    if (round(cid2span[cid]["min_x"]) == round(
                            cid2span[cid2]["min_x"]) and
                            cid2span[cid]["max_y"] < cid2span[cid2]["min_y"]):
                        references_cid.add(cid2)
                        cid2span[cid2]["min_x"] = cid2span[cid]["min_x"]
                        cid2span[cid2]["max_x"] = cid2span[cid]["max_x"]

    #get a list of empty cids
    empty_cids = [cid for cid in range(len(cid2obj)) if len(cid2obj[cid]) == 0]
    empty_idx = 0

    #Split paras based on whitespaces - seems to work
    if (ref_page_seen == False):
        for cid in range(len(cid2obj)):
            if (len(cid2obj[cid]) > 0 and cid not in empty_cids
                    and cid not in references_cid):
                cid_maxx = max([boxes[obj].bbox[2] for obj in cid2obj[cid]])
                cid_minx = min([boxes[obj].bbox[0] for obj in cid2obj[cid]])
                rid_list = set([obj2rid[obj] for obj in cid2obj[cid]])
                #Get min_y for each row
                rid_miny = {}
                for rid in rid_list:
                    rid_miny[rid] = min([
                        boxes[obj].bbox[1] if obj in cid2obj[cid] else 10000
                        for obj in rid2obj[rid]
                    ])
                sorted_rid_miny = sorted(
                    list(rid_miny.items()), key=operator.itemgetter(1))
                last_rid = 0
                for i in range(len(sorted_rid_miny) - 1):
                    row1 = sorted_rid_miny[i][0]
                    row2 = sorted_rid_miny[i + 1][0]
                    row1_maxx = max([
                        boxes[obj].bbox[2] if obj in cid2obj[cid] else -1
                        for obj in rid2obj[row1]
                    ])
                    row2_minx = min([
                        boxes[obj].bbox[0] if obj in cid2obj[cid] else 10000
                        for obj in rid2obj[row2]
                    ])
                    if (row1_maxx <= cid_maxx
                            and (row2_minx - char_width) > cid_minx):
                        #split cluster cid
                        new_cid_idx = empty_cids[empty_idx]
                        empty_idx += 1
                        for i_iter in range(last_rid, i + 1):
                            obj_list = [
                                obj
                                for obj in rid2obj[sorted_rid_miny[i_iter][0]]
                                if obj2cid[obj] == cid
                            ]
                            for obj in obj_list:
                                cid2obj[cid].remove(obj)
                                cid2obj[new_cid_idx].add(obj)
                                obj2cid[obj] = new_cid_idx
                        last_rid = i + 1

    clusters = [[boxes[i] for i in cluster]
                for cluster in filter(bool, cid2obj)]
    nodes = [Node(elems) for elems in clusters]
    node_indices = [i for i, x in enumerate(cid2obj) if x]
    merge_indices = [i for i in range(len(node_indices))]
    page_stat = Node(boxes)
    nodes, merge_indices = merge_nodes(nodes, plane, page_stat, merge_indices)

    ##Merging Nodes
    new_nodes = []
    new_node_indices = []
    for idx in range(len(merge_indices)):
        if (merge_indices[idx] == idx):
            new_nodes.append(nodes[idx])
            new_node_indices.append(node_indices[idx])

    #Heuristics for Node type
    ref_nodes = []
    new_ref_page_seen = False
    if (len(references_cid) > 0 or ref_page_seen or references_bbox != []):
        new_ref_page_seen = True
    ref_seen_in_node = False or ref_page_seen
    all_boxes = boxes + boxes_figures
    min_y_page = float("Inf")
    for idx, box in enumerate(all_boxes):
        min_y_page = min(min_y_page, box.bbox[1])
    if page_num == -1:
        #handle title, authors and abstract here
        log.error("TODO: no way to handle title authors abstract yet.")
    else:
        #eliminate header, footer, page number
        #sort other text and classify as header/paragraph
        new_nodes.sort(key=cmp_to_key(xy_reading_order))
        for idx, node in enumerate(new_nodes):
            if (idx < len(new_nodes) - 1):
                if ((round(node.y0) == round(min_y_page)
                     or math.floor(node.y0) == math.floor(min_y_page)) and
                        node.y1 - node.y0 < 2 * avg_font_pts):  #can be header
                    idx_new = idx + 1
                    if idx_new < len(new_nodes) - 1:
                        while (idx_new < len(new_nodes) - 1 and
                               (round(node.y0) == round(new_nodes[idx_new].y0))
                               or (math.floor(node.y0) == math.floor(
                                   new_nodes[idx_new].y0))):
                            idx_new += 1
                    if (idx_new < len(new_nodes) - 1):
                        if (new_nodes[idx_new].y0 - node.y0 >
                                1.5 * avg_font_pts):
                            node.type = "Header"
                            continue
            #get captions - first word is fig/figure/table
            first_elem = None
            for elem in node.elems:
                if (round(elem.bbox[0]) == round(node.x0)
                        and round(elem.bbox[1]) == round(node.y0)):
                    first_elem = elem
                    break
            if (first_elem != None):
                text = first_elem.get_text()
                if (len(text) > 10):
                    text = first_elem.get_text()[0:10]
                if ("Table" in text):
                    node.type = "Table Caption"
                    continue
                if ("Fig" in text or "Figure" in text):
                    node.type = "Figure Caption"
                    continue
                if (first_elem.get_text().lower() == "references"):
                    node.type = "Section Header"
                    ref_seen_in_node = True
                    continue
            if (ref_seen_in_node):
                node.type = "List"
                continue
            if (references_bbox != [] or ref_seen_in_node):
                if (node.y0 > references_bbox[3]
                        and node.x0 <= references_bbox[0]
                        and node.x1 > references_bbox[2]):
                    node.type = "List"
                    continue
            if (node.y1 - node.y0 <= 2.0 * avg_font_pts):  #one lines - section
                node.type = "Section Header"
            else:  #multiple lines - para
                node.type = "Paragraph"

    #handle references
    newer_nodes = []
    ref_indices = [False for idx in range(len(new_nodes))]
    for idx1, node1 in enumerate(new_nodes):
        if (ref_indices[idx1] == True):
            continue
        if (node1.type != "List"):
            newer_nodes.append(node1)
            continue
        x0, y0, x1, y1 = node1.x0, node1.y0, node1.x1, node1.y1
        newer_node = node1
        ref_indices[idx1] = True
        for idx2, node2 in enumerate(new_nodes):
            if (idx1 != idx2):
                if (node2.type == "List" and ref_indices[idx2] == False):
                    if ((node2.x0 <= x0 and node2.x1 >= x0)
                            or (x0 <= node2.x0 and x1 >= node2.x0)):
                        newer_node.merge(node2)
                        ref_indices[idx2] = True
        newer_nodes.append(newer_node)

    #handle figures
    for fig_box in boxes_figures:
        node_fig = Node(fig_box)
        node_fig.type = "Figure"
        newer_nodes.append(node_fig)

    tree = {}
    tree["section_header"] = [(page_num, page_width, page_height) +
                              (node.y0, node.x0, node.y1, node.x1)
                              for node in newer_nodes
                              if node.type == "Section Header"]
    tree["header"] = [(page_num, page_width, page_height) +
                      (node.y0, node.x0, node.y1, node.x1)
                      for node in newer_nodes if node.type == "Header"]
    tree["paragraph"] = [(page_num, page_width, page_height) +
                         (node.y0, node.x0, node.y1, node.x1)
                         for node in newer_nodes if node.type == "Paragraph"]
    # tree["figure"] = [(page_num, page_width, page_height) + (node.y0, node.x0, node.y1, node.x1) for node in newer_nodes if node.type=="Figure"]
    tree["figure_caption"] = [(page_num, page_width, page_height) +
                              (node.y0, node.x0, node.y1, node.x1)
                              for node in newer_nodes
                              if node.type == "Figure Caption"]
    tree["table_caption"] = [(page_num, page_width, page_height) +
                             (node.y0, node.x0, node.y1, node.x1)
                             for node in newer_nodes
                             if node.type == "Table Caption"]
    tree["list"] = [(page_num, page_width, page_height) +
                    (node.y0, node.x0, node.y1, node.x1)
                    for node in newer_nodes if node.type == "List"]
    return tree, new_ref_page_seen


def get_figures(boxes, page_bbox, page_num, boxes_figures, page_width,
                page_height):
    plane = Plane(page_bbox)
    plane.extend(boxes)

    nodes_figures = []

    for fig_box in boxes_figures:
        node_fig = Node(fig_box)
        nodes_figures.append(node_fig)

    merge_indices = [i for i in range(len(nodes_figures))]
    page_stat = Node(boxes)
    nodes, merge_indices = merge_nodes(nodes_figures, plane, page_stat,
                                       merge_indices)

    ##Merging Nodes
    new_nodes = []
    for idx in range(len(merge_indices)):
        if (merge_indices[idx] == idx):
            new_nodes.append(nodes[idx])

    figures = [(page_num, page_width, page_height) +
               (node.y0, node.x0, node.y1, node.x1) for node in new_nodes]
    return figures


def merge_nodes(nodes, plane, page_stat, merge_indices):
    '''
    Merges overlapping nodes
    '''
    # Merge inner boxes to the best outer box
    # nodes.sort(key=Node.area)
    to_be_removed = set()
    for inner_idx in range(len(nodes)):
        inner = nodes[inner_idx]
        outers = []
        outers_indices = []
        for outer_idx in range(len(nodes)):
            outer = nodes[outer_idx]
            if outer is inner or outer in to_be_removed: continue
            if intersect(outer.bbox, inner.bbox):
                outers.append(outer)
                outers_indices.append(outer_idx)
        if not outers: continue
        # Best is defined as min L1 distance to outer center
        best_outer = min(
            outers,
            key=lambda outer: l1(center(outer.bbox), center(inner.bbox)))
        best_outer_idx = outers_indices[outers.index(best_outer)]
        to_be_removed.add(inner)
        best_outer.merge(inner)
        for cid_iter in range(len(merge_indices)):
            if (merge_indices[cid_iter] == merge_indices[inner_idx]):
                merge_indices[cid_iter] = merge_indices[best_outer_idx]
    return nodes, merge_indices


def get_most_common_font_pts(mentions, font_stat):
    '''
    font_stat: Counter object of font sizes
    '''
    # default min font size of 1 pt in case no font present
    most_common_font_size = font_stat.most_common(1)[0][0]
    # Corner case when no text on page
    if not most_common_font_size: return 2.0
    count = 0.01  # avoid division by zero
    height_sum = 0.02  # default to pts 2.0
    for m in mentions:
        if m.font_size == most_common_font_size:
            height_sum += m.height
            count += 1
    return height_sum / count


def get_page_width(boxes):
    xmin = float("Inf")
    xmax = float("-Inf")
    for i, b in enumerate(boxes):
        xmin = min(xmin, b.bbox[0])
        xmax = max(xmax, b.bbox[2])

    return (xmax - xmin)


def get_char_width(boxes):
    box_len_sum = 0
    num_char_sum = 0
    for i, b in enumerate(boxes):
        box_len_sum = box_len_sum + b.bbox[2] - b.bbox[0]
        num_char_sum = num_char_sum + len(b.get_text())
    return box_len_sum / num_char_sum
