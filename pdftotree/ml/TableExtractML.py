from __future__ import division
from builtins import filter
from builtins import str
from builtins import range
from builtins import object
import logging
import numpy as np
from pdfminer.utils import Plane
from pdftotree.ml.features import get_alignment_features, get_lines_features
from pdftotree.pdf.pdf_parsers import parse_layout
from pdftotree.pdf.pdf_utils import normalize_pdf, analyze_pages
from pdftotree.utils.bbox_utils import get_rectangles, compute_iou
from pdftotree.utils.display_utils import pdf_to_img
from pdftotree.utils.lines_utils import extend_horizontal_lines
from pdftotree.utils.lines_utils import extend_vertical_lines
from pdftotree.utils.lines_utils import get_vertical_and_horizontal
from pdftotree.utils.lines_utils import merge_horizontal_lines
from pdftotree.utils.lines_utils import merge_vertical_lines
from pdftotree.utils.lines_utils import reorder_lines
from wand.color import Color
from wand.drawing import Drawing


class TableExtractorML(object):
    """
    Object to extract tables regions from pdf files
    """

    def __init__(self, pdf_file):
        self.log = logging.getLogger(__name__)
        self.pdf_file = pdf_file
        self.elems = {}
        self.font_stats = {}
        self.lines_bboxes = []
        self.alignments_bboxes = []
        self.intersection_bboxes = []
        self.bboxes = []
        self.candidates = []
        self.features = []
        self.iou_thresh = 0.8
        self.scanned = False

    def identify_scanned_page(self, boxes, page_bbox, page_width, page_height):
        plane = Plane(page_bbox)
        plane.extend(boxes)
        cid2obj = [set([i]) for i in range(len(boxes))]  # initialize clusters
        # default object map to cluster with its own index
        obj2cid = list(range(len(boxes)))
        prev_clusters = obj2cid
        while (True):
            for i1, b1 in enumerate(boxes):
                for i2, b2 in enumerate(boxes):
                    box1 = b1.bbox
                    box2 = b2.bbox
                    if (box1[0] == box2[0] and box1[2] == box2[2]
                            and round(box1[3]) == round(box2[1])):
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
        clusters = [[boxes[i] for i in cluster]
                    for cluster in filter(bool, cid2obj)]
        if (len(clusters) == 1 and clusters[0][0].bbox[0] < -0.0
                and clusters[0][0].bbox[1] <= 0
                and abs(clusters[0][0].bbox[2] - page_width) <= 5
                and abs(clusters[0][0].bbox[3] - page_height) <= 5):
            return True
        return False

    def parse(self):
        is_scanned = False
        lin_seg_present = False
        for page_num, layout in enumerate(analyze_pages(self.pdf_file)):
            page_num += 1  # indexes start at 1
            elems, font_stat = normalize_pdf(layout, scaler=1)
            self.elems[page_num] = elems
            self.font_stats[page_num] = font_stat
            # code to detect if the page is scanned
            if (len(elems.segments) > 0):
                lin_seg_present = True
            for fig in elems.figures:
                if (fig.bbox[0] <= 0.0 and fig.bbox[1] <= 0.0
                        and round(fig.bbox[2]) == round(elems.layout.width)
                        and round(fig.bbox[3]) == round(elems.layout.height)):
                    self.log.debug(
                        "{} is scanned because of full-page figure.".format(
                            self.pdf_file))
                    is_scanned = True
            page_scanned = self.identify_scanned_page(
                elems.figures, elems.layout.bbox, elems.layout.width,
                elems.layout.height)
            # doc is scanned if any page is scanned
            if (page_scanned == True):
                self.log.debug(
                    "{} is scanned one of its pages is scanned.".format(
                        self.pdf_file))
                is_scanned = True
        if (is_scanned or not lin_seg_present):
            self.scanned = True

    def get_scanned(self):
        if (len(self.elems) == 0):
            self.parse()
        return self.scanned

    def get_candidates(self):
        if (len(self.elems) == 0):
            self.parse()
        if (self.scanned):
            return []
        for page_num in list(self.elems.keys()):
            page_boxes, page_features = self.get_candidates_and_features_page_num(
                page_num)
            self.candidates += page_boxes
            self.features += list(page_features)
        return self.candidates

    def get_candidates_and_features(self):
        self.parse()
        if (self.scanned):
            self.log.info("{} is scanned.".format(self.pdf_file))
            return [], [], self.scanned
        for page_num in list(self.elems.keys()):
            page_boxes, page_features = self.get_candidates_and_features_page_num(
                page_num)
            self.candidates += page_boxes
            self.features += list(page_features)
        return self.candidates, self.features, self.scanned

    def get_candidates_and_features_page_num(self, page_num):
        elems = self.elems[page_num]
        font_stat = self.font_stats[page_num]
        lines_bboxes = self.get_candidates_lines(page_num, elems)
        boxes = []
        # Filter out bboxes that are zero width or height
        for bbox in lines_bboxes:
            if (bbox[5] - bbox[3] > 0 and bbox[6] - bbox[4] > 0):
                boxes += [bbox]
        alignments_bboxes, alignment_features = self.get_candidates_alignments(
            page_num, elems)
        self.log.info(
            "Page Num: {}, Line bboxes: {}, Alignment bboxes: {}".format(
                page_num, len(lines_bboxes), len(alignments_bboxes)))
        alignment_features += get_alignment_features(lines_bboxes, elems,
                                                     font_stat)
        # Filter out bboxes that are zero width or height
        for bbox in alignments_bboxes:
            if (bbox[5] - bbox[3] > 0 and bbox[6] - bbox[4] > 0):
                boxes += [bbox]
        #  boxes = alignments_bboxes + lines_bboxes
        if len(boxes) == 0:
            return [], []
        lines_features = get_lines_features(boxes, elems)
        features = np.concatenate(
            (np.array(alignment_features), np.array(lines_features)), axis=1)
        return boxes, features

    def get_candidates_lines(self, page_num, elems):
        page_width, page_height = int(elems.layout.width), int(
            elems.layout.height)
        lines = reorder_lines(elems.segments)
        vertical_lines, horizontal_lines = get_vertical_and_horizontal(lines)
        extended_vertical_lines = extend_vertical_lines(horizontal_lines)
        extended_horizontal_lines = extend_horizontal_lines(vertical_lines)
        vertical_lines = merge_vertical_lines(
            sorted(extended_vertical_lines + vertical_lines))
        horizontal_lines = merge_horizontal_lines(
            sorted(extended_horizontal_lines + horizontal_lines))
        rectangles = get_rectangles(
            sorted(vertical_lines), sorted(horizontal_lines))
        return [(page_num, page_width, page_height) + bbox
                for bbox in rectangles]

    def get_candidates_alignments(self, page_num, elems):
        page_width, page_height = int(elems.layout.width), int(
            elems.layout.height)
        font_stat = self.font_stats[page_num]
        try:
            nodes, features = parse_layout(elems, font_stat)
        except:
            nodes, features = [], []
        return [(page_num, page_width, page_height) +
                (node.y0, node.x0, node.y1, node.x1)
                for node in nodes], features

    def get_elems(self):
        return self.elems

    def get_font_stats(self):
        return self.font_stats

    def get_labels(self, gt_tables):
        """
        :param gt_tables: dict, keys are page number and values are list of
                          tables bbox within that page
        :return:
        """
        labels = np.zeros(len(self.candidates))
        for i, candidate in enumerate(self.candidates):
            page_num = candidate[0]
            try:
                tables = gt_tables[page_num]
                for gt_table in tables:
                    page_width, page_height, y0, x0, y1, x1 = gt_table
                    w_ratio = float(candidate[1]) / page_width
                    h_ratio = float(candidate[2]) / page_height
                    rescaled_gt_table = (y0 * h_ratio, x0 * w_ratio,
                                         y1 * h_ratio, x1 * w_ratio)
                    iou = compute_iou(candidate[-4:], rescaled_gt_table)
                    if iou > self.iou_thresh:
                        # candidate region is a table
                        labels[i] = 1
            except KeyError:
                # any of the candidates is a true table, all zero labels
                pass
        return labels

    def display_bounding_boxes(self, page_num, bboxes, alternate_colors=True):
        elems = self.elems[page_num]
        page_width, page_height = int(elems.layout.width), int(
            elems.layout.height)
        img = pdf_to_img(self.pdf_file, page_num, page_width, page_height)
        draw = Drawing()
        draw.fill_color = Color('rgba(0, 0, 0, 0)')
        color = Color('blue')
        draw.stroke_color = color
        for block in bboxes:
            top, left, bottom, right = block[-4:]
            draw.stroke_color = Color('rgba({},{},{}, 1)'.format(
                str(np.random.randint(255)), str(np.random.randint(255)),
                str(np.random.randint(255))))
            draw.rectangle(
                left=float(left),
                top=float(top),
                right=float(right),
                bottom=float(bottom))
        draw(img)
        return img
