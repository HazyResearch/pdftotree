from __future__ import division
from builtins import str
import string

from pdftotree.pdf.pdf_parsers import *
from pdftotree.pdf.vector_utils import *
from pdftotree.utils.bbox_utils import isContained


# ******************* Table Coverage Features *************************************


def get_area_coverage(bbox):
    b = bbox[-4:]
    return ((b[2] - b[0]) * (b[3] - b[1])) / float(bbox[1] * bbox[2])


def get_width_coverage(bbox):
    b = bbox[-4:]
    return (b[3] - b[1]) / float(bbox[1])


def get_height_coverage(bbox):
    b = bbox[-4:]
    return (b[2] - b[0]) / float(bbox[2])


# ******************* Text Coverage Features *************************************

def get_mentions_within_bbox(bbox, mentions):
    mentions_within_bbox = []
    for mention in mentions:
        bbox_mention = (int(mention.y0), int(mention.x0), int(mention.y1), int(mention.x1))
        if isContained(bbox_mention, bbox[-4:]):
            mentions_within_bbox += [mention]
    return mentions_within_bbox


def get_text_sparsity(bbox, mentions):
    """
    computes text area coverage
    :param mentions:
    :return:
    """
    b = bbox[-4:]
    bbox_area = ((b[2] - b[0]) * (b[3] - b[1]))
    text_area = 0
    for m in mentions:
        text_area += (m.x1 - m.x0) * (m.y1 - m.y0)
    try:
        return 1.0 * text_area / bbox_area
    except ZeroDivisionError:
        return 0.


def symbols_and_numbers_density(bbox, mentions):
    symbols = set(string.punctuation)
    num_symbols = sum([1 for elem in mentions if elem.get_text() in symbols])
    num_numbers = 0
    for elem in mentions:
        num_numbers += sum([c.isdigit() for c in elem.get_text()])
    return [num_symbols, num_numbers]


# ******************* Lines Features *************************************

def get_lines_within_bbox(bbox, segments):
    lines_within_bbox = []
    for line in segments:
        bbox_line = (int(line.y0), int(line.x0), int(line.y1), int(line.x1))
        if isContained(bbox_line, bbox[-4:]):
            lines_within_bbox += [line]
    return lines_within_bbox


def get_lines_features(bboxes, elems):
    features = []
    for bbox in bboxes:
        mentions = get_mentions_within_bbox(bbox, elems.mentions)
        segments = get_lines_within_bbox(bbox, elems.segments)
        feat = [get_area_coverage(bbox)]
        feat += [get_height_coverage(bbox)]
        feat += [get_width_coverage(bbox)]
        feat += [get_text_sparsity(bbox, mentions)]
        feat += symbols_and_numbers_density(bbox, mentions)
        feat += [len(segments)]
        features += [feat]
    return features

# ******************* Alignments Features *************************************


def get_alignment_features(line_bboxes, elems, font_stat):
    alignment_features = []
    for line_bbox in line_bboxes:
        line_bbox_ordered = (line_bbox[4], line_bbox[3], line_bbox[6], line_bbox[5])
        boxes = [elem for elem in elems.mentions if intersect(line_bbox_ordered, elem.bbox)]
        boxes_segments = [elem for elem in elems.segments if intersect(line_bbox_ordered, elem.bbox)]
        boxes_figures = [elem for elem in elems.figures if intersect(line_bbox_ordered, elem.bbox)]
        boxes_curves = [elem for elem in elems.curves if intersect(line_bbox_ordered, elem.bbox)]
        page_width = elems.layout.width
        page_height = elems.layout.height
        avg_font_pts = get_most_common_font_pts(elems.mentions, font_stat)
        width = get_page_width(boxes + boxes_segments + boxes_figures + boxes_curves)
        if (len(boxes) == 0):
            alignment_features += [[0] * 17]
            continue
        char_width = get_char_width(boxes)
        grid_size = avg_font_pts / 2.0
        for i, m in enumerate(boxes + elems.figures):
            m.id = i
            m.feats = defaultdict(bool)
            prefix = ''
            if isinstance(m, LTTextLine) and m.font_name: prefix = m.font_name + '-' + str(m.font_size) + '-'
            m.xc = (m.x0 + m.x1) / 2.0
            m.yc = (m.y0 + m.y1) / 2.0
            m.feats[prefix + 'x0'] = m.x0_grid = m.x0 // grid_size
            m.feats[prefix + 'x1'] = m.x1_grid = m.x1 // grid_size
            m.feats[prefix + 'xc'] = m.xc_grid = m.xc // grid_size
            m.feats[prefix + 'yc'] = m.yc_grid = m.yc // grid_size

        nodes, nodes_features = cluster_vertically_aligned_boxes(boxes, elems.layout.bbox, avg_font_pts, width,
                                                                 char_width, boxes_segments, boxes_curves,
                                                                 boxes_figures, page_width, True)
        if (len(nodes_features) == 0):
            alignment_features += [[0] * 17]
        else:
            alignment_features += [nodes_features]
    return alignment_features
