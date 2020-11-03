import logging

import numpy as np
from wand.color import Color
from wand.drawing import Drawing

from pdftotree.ml.features import get_alignment_features, get_lines_features
from pdftotree.TreeExtract import TreeExtractor
from pdftotree.utils.bbox_utils import compute_iou
from pdftotree.utils.display_utils import pdf_to_img

logger = logging.getLogger(__name__)


class TableExtractorML(TreeExtractor):
    """
    Object to extract tables regions from pdf files
    """

    def __init__(self, pdf_file):
        super().__init__(pdf_file)
        self.lines_bboxes = []
        self.alignments_bboxes = []
        self.intersection_bboxes = []
        self.bboxes = []
        self.candidates = []
        self.features = []

    def get_candidates(self):
        if len(self.elems) == 0:
            self.parse()
        if self.scanned:
            return []
        for page_num in list(self.elems.keys()):
            page_boxes, page_features = self.get_candidates_and_features_page_num(
                page_num
            )
            self.candidates += page_boxes
            self.features += list(page_features)
        return self.candidates

    def get_candidates_and_features(self):
        self.parse()
        if self.scanned:
            logger.info("{} is scanned.".format(self.pdf_file))
            return [], [], self.scanned
        for page_num in list(self.elems.keys()):
            page_boxes, page_features = self.get_candidates_and_features_page_num(
                page_num
            )
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
            if bbox[5] - bbox[3] > 0 and bbox[6] - bbox[4] > 0:
                boxes += [bbox]
        alignments_bboxes, alignment_features = self.get_candidates_alignments(
            page_num, elems
        )
        logger.info(
            "Page Num: {}, Line bboxes: {}, Alignment bboxes: {}".format(
                page_num, len(lines_bboxes), len(alignments_bboxes)
            )
        )
        alignment_features += get_alignment_features(lines_bboxes, elems, font_stat)
        # Filter out bboxes that are zero width or height
        for bbox in alignments_bboxes:
            if bbox[5] - bbox[3] > 0 and bbox[6] - bbox[4] > 0:
                boxes += [bbox]
        #  boxes = alignments_bboxes + lines_bboxes
        if len(boxes) == 0:
            return [], []
        lines_features = get_lines_features(boxes, elems)
        features = np.concatenate(
            (np.array(alignment_features), np.array(lines_features)), axis=1
        )
        return boxes, features

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
                    rescaled_gt_table = (
                        y0 * h_ratio,
                        x0 * w_ratio,
                        y1 * h_ratio,
                        x1 * w_ratio,
                    )
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
        page_width, page_height = int(elems.layout.width), int(elems.layout.height)
        img = pdf_to_img(self.pdf_file, page_num, page_width, page_height)
        draw = Drawing()
        draw.fill_color = Color("rgba(0, 0, 0, 0)")
        color = Color("blue")
        draw.stroke_color = color
        for block in bboxes:
            top, left, bottom, right = block[-4:]
            draw.stroke_color = Color(
                "rgba({},{},{}, 1)".format(
                    str(np.random.randint(255)),
                    str(np.random.randint(255)),
                    str(np.random.randint(255)),
                )
            )
            draw.rectangle(
                left=float(left),
                top=float(top),
                right=float(right),
                bottom=float(bottom),
            )
        draw(img)
        return img
