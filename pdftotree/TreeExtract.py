import html
import logging
import os
from functools import cmp_to_key
from typing import Any, Dict, List, Optional, Tuple
from xml.dom.minidom import Document, Element

import numpy as np
import tabula
from pdfminer.layout import LAParams, LTChar, LTPage, LTTextLine
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.utils import Plane

from pdftotree._version import __version__
from pdftotree.ml.features import get_lines_features, get_mentions_within_bbox
from pdftotree.utils.bbox_utils import get_rectangles
from pdftotree.utils.lines_utils import (
    extend_horizontal_lines,
    extend_vertical_lines,
    get_vertical_and_horizontal,
    merge_horizontal_lines,
    merge_vertical_lines,
    reorder_lines,
)
from pdftotree.utils.pdf.pdf_parsers import parse_layout, parse_tree_structure
from pdftotree.utils.pdf.pdf_utils import CustomPDFPageAggregator, PDFElems
from pdftotree.utils.pdf.vector_utils import column_order, reading_order

logger = logging.getLogger(__name__)


class TreeExtractor(object):
    """
    Object to extract tree structure from pdf files
    """

    def __init__(self, pdf_file):
        self.pdf_file = pdf_file
        self.elems: Dict[int, PDFElems] = {}  # key represents page_num
        self.font_stats: Dict[int, Any] = {}  # key represents page_num
        self.iou_thresh = 0.8
        self.scanned = False
        self.tree: Dict[int, Any] = {}  # key represents page_num

    def identify_scanned_page(self, boxes, page_bbox, page_width, page_height):
        plane = Plane(page_bbox)
        plane.extend(boxes)
        # initialize clusters
        cid2obj = [set([i]) for i in range(len(boxes))]
        # default object map to cluster with its own index
        obj2cid = list(range(len(boxes)))
        prev_clusters = obj2cid
        while True:
            for i1, b1 in enumerate(boxes):
                for i2, b2 in enumerate(boxes):
                    box1 = b1.bbox
                    box2 = b2.bbox
                    if (
                        box1[0] == box2[0]
                        and box1[2] == box2[2]
                        and round(box1[3]) == round(box2[1])
                    ):
                        min_i = min(i1, i2)
                        max_i = max(i1, i2)
                        cid1 = obj2cid[min_i]
                        cid2 = obj2cid[max_i]
                        for obj_iter in cid2obj[cid2]:
                            cid2obj[cid1].add(obj_iter)
                            obj2cid[obj_iter] = cid1
                        cid2obj[cid2] = set()
            if prev_clusters == obj2cid:
                break
            prev_clusters = obj2cid
        clusters = [[boxes[i] for i in cluster] for cluster in filter(bool, cid2obj)]
        if (
            len(clusters) == 1
            and clusters[0][0].bbox[0] < -0.0
            and clusters[0][0].bbox[1] <= 0
            and abs(clusters[0][0].bbox[2] - page_width) <= 5
            and abs(clusters[0][0].bbox[3] - page_height) <= 5
        ):
            return True
        return False

    def parse(self):
        is_scanned = False
        lin_seg_present = False
        layouts: List[LTPage] = []

        log = logging.getLogger(__name__)
        # Open a PDF file.
        with open(os.path.realpath(self.pdf_file), "rb") as fp:
            # Create a PDF parser object associated with the file object.
            parser = PDFParser(fp)
            # Create a PDF document object that stores the document structure.
            # Supply the password for initialization.
            document = PDFDocument(parser, password="")
            # Create a PDF resource manager object that stores shared resources.
            rsrcmgr = PDFResourceManager()
            # Set parameters for analysis.
            laparams = LAParams(char_margin=1.0, word_margin=0.1, detect_vertical=True)
            # Create a PDF page aggregator object.
            device = CustomPDFPageAggregator(rsrcmgr, laparams=laparams)
            # Create a PDF interpreter object.
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            # Process each page contained in the document.
            for page_num, page in enumerate(PDFPage.create_pages(document)):
                try:
                    interpreter.process_page(page)
                except OverflowError as oe:
                    log.exception(
                        "{}, skipping page {} of {}".format(oe, page_num, self.pdf_file)
                    )
                    continue
                layout = device.get_result()
                layouts.append(layout)

        for page_num, layout in enumerate(layouts):
            page_num += 1  # indexes start at 1
            elems, font_stat = device.normalize_pdf(layout, scaler=1)
            self.elems[page_num] = elems
            self.font_stats[page_num] = font_stat
            # code to detect if the page is scanned
            if len(elems.segments) > 0:
                lin_seg_present = True
            for fig in elems.figures:
                if (
                    fig.bbox[0] <= 0.0
                    and fig.bbox[1] <= 0.0
                    and round(fig.bbox[2]) == round(elems.layout.width)
                    and round(fig.bbox[3]) == round(elems.layout.height)
                ):
                    is_scanned = True
            page_scanned = self.identify_scanned_page(
                elems.figures,
                elems.layout.bbox,
                elems.layout.width,
                elems.layout.height,
            )
            # doc is scanned if any page is scanned
            if page_scanned:
                is_scanned = True
        if is_scanned or not lin_seg_present:
            self.scanned = True

    def is_scanned(self):
        if len(self.elems) == 0:
            self.parse()
        return self.scanned

    def get_tables_page_num(self, page_num):
        page_boxes, _ = self.get_candidates_and_features_page_num(page_num)
        tables = page_boxes
        return tables

    def get_candidates_and_features_page_num(self, page_num):
        elems = self.elems[page_num]
        #  font_stat = self.font_stats[page_num]
        #  lines_bboxes = self.get_candidates_lines(page_num, elems)
        alignments_bboxes, alignment_features = self.get_candidates_alignments(
            page_num, elems
        )

        boxes = alignments_bboxes
        if len(boxes) == 0:
            logger.info("No boxes were found on page {}.".format(page_num))
            return [], []

        lines_features = get_lines_features(boxes, elems)
        features = np.concatenate(
            (np.array(alignment_features), np.array(lines_features)), axis=1
        )
        return boxes, features

    def get_candidates_lines(self, page_num, elems):
        page_width = int(elems.layout.width)
        page_height = int(elems.layout.height)
        lines = reorder_lines(elems.segments)
        vertical_lines, horizontal_lines = get_vertical_and_horizontal(lines)
        extended_vertical_lines = extend_vertical_lines(horizontal_lines)
        extended_horizontal_lines = extend_horizontal_lines(vertical_lines)
        vertical_lines = merge_vertical_lines(
            sorted(extended_vertical_lines + vertical_lines)
        )
        horizontal_lines = merge_horizontal_lines(
            sorted(extended_horizontal_lines + horizontal_lines)
        )
        rects = get_rectangles(sorted(vertical_lines), sorted(horizontal_lines))
        return [(page_num, page_width, page_height) + bbox for bbox in rects]

    def get_candidates_alignments(self, page_num, elems):
        page_width = int(elems.layout.width)
        page_height = int(elems.layout.height)
        font_stat = self.font_stats[page_num]
        try:
            nodes, features = parse_layout(elems, font_stat)
        except Exception as e:
            logger.exception(e)
            nodes, features = [], []
        return (
            [
                (page_num, page_width, page_height)
                + (node.y0, node.x0, node.y1, node.x1)
                for node in nodes
            ],
            features,
        )

    def get_elems(self):
        return self.elems

    def get_font_stats(self):
        return self.font_stats

    def get_tree_structure(self, model_type, model) -> Dict[str, Any]:
        tables = {}
        # use vision to get tables
        if model_type == "vision":
            from pdftotree.visual.visual_utils import get_bboxes, predict_heatmap

            for page_num in self.elems.keys():
                page_width = int(self.elems[page_num].layout.width)
                page_height = int(self.elems[page_num].layout.height)
                image, pred = predict_heatmap(
                    self.pdf_file, page_num - 1, model
                )  # index start at 0 with wand
                bboxes, _ = get_bboxes(image, pred)
                tables[page_num] = [
                    (page_num, page_width, page_height)
                    + (top, left, top + height, left + width)
                    for (left, top, width, height) in bboxes
                ]

        # use ML to get tables
        elif model_type == "ml":
            for page_num in self.elems.keys():
                t_cands, cand_feats = self.get_candidates_and_features_page_num(
                    page_num
                )
                tables[page_num] = []
                if len(cand_feats) != 0:
                    table_predictions = model.predict(cand_feats)
                    tables[page_num] = [
                        t_cands[i]
                        for i in range(len(t_cands))
                        if table_predictions[i] > 0.5
                    ]

        # use heuristics to get tables if no model_type is provided
        else:
            for page_num in self.elems.keys():
                tables[page_num] = self.get_tables_page_num(page_num)

        # Manage References - indicator to indicate if reference has been seen
        ref_page_seen = False
        for page_num in self.elems.keys():
            # Get Tree Structure for this page
            self.tree[page_num], ref_page_seen = parse_tree_structure(
                self.elems[page_num],
                self.font_stats[page_num],
                page_num,
                ref_page_seen,
                tables[page_num],
            )
        return self.tree

    def get_html_tree(self) -> str:
        doc = Document()
        self.doc = doc
        html = doc.createElement("html")
        doc.appendChild(html)
        head = doc.createElement("head")
        html.appendChild(head)
        # meta
        meta = doc.createElement("meta")
        head.appendChild(meta)
        meta.setAttribute("name", "ocr-system")
        meta.setAttribute("content", f"Converted from PDF by pdftotree {__version__}")
        meta = doc.createElement("meta")
        head.appendChild(meta)
        meta.setAttribute("name", "ocr-capabilities")
        meta.setAttribute("content", "ocr_page ocr_table ocrx_block ocrx_word")
        meta = doc.createElement("meta")
        head.appendChild(meta)
        meta.setAttribute("name", "ocr-number-of-pages")
        meta.setAttribute("content", f"{len(self.elems.keys())}")
        # body
        body = doc.createElement("body")
        html.appendChild(body)
        for page_num in self.elems.keys():  # 1-based
            boxes = []
            for clust in self.tree[page_num]:
                for (pnum, pwidth, pheight, top, left, bottom, right) in self.tree[
                    page_num
                ][clust]:
                    boxes += [
                        [clust.lower().replace(" ", "_"), top, left, bottom, right]
                    ]
            page = doc.createElement("div")
            page.setAttribute("class", "ocr_page")
            page.setAttribute("id", f"page_{page_num}")
            width = int(self.elems[page_num].layout.width)
            height = int(self.elems[page_num].layout.height)
            page.setAttribute(
                "title",
                f"bbox 0 0 {width} {height}; ppageno {page_num-1}",
            )
            body.appendChild(page)
            # TODO: We need to detect columns and sort acccordingly.
            boxes.sort(key=cmp_to_key(column_order))

            for box in boxes:
                if box[0] == "table":
                    table = box[1:]  # bbox
                    table_element = self.get_html_table(table, page_num)
                    page.appendChild(table_element)
                elif box[0] == "figure":
                    fig_element = doc.createElement("figure")
                    page.appendChild(fig_element)
                    top, left, bottom, right = [int(i) for i in box[1:]]
                    fig_element.setAttribute(
                        "title", f"bbox {left} {top} {right} {bottom}"
                    )
                else:
                    element = self.get_html_others(box[0], box[1:], page_num)
                    page.appendChild(element)
        return doc.toprettyxml()

    def get_word_boundaries(
        self, mention: LTTextLine
    ) -> List[Tuple[str, float, float, float, float]]:
        mention_text = mention.get_text()
        mention_chars: List[Tuple[str, int, int, int, int]] = []
        for obj in mention:
            if isinstance(obj, LTChar):
                x0, y0, x1, y1 = obj.bbox
                mention_chars.append([obj.get_text(), y0, x0, y1, x1])
        words = []
        mention_words: List[str] = mention_text.split()  # word split by " " (space)
        char_idx = 0
        for word in mention_words:
            curr_word = [word, float("Inf"), float("Inf"), float("-Inf"), float("-Inf")]
            len_idx = 0
            while len_idx < len(word):
                if mention_chars[char_idx][0] == " ":
                    char_idx += 1
                    continue
                if word[len_idx] != mention_chars[char_idx][0]:
                    logger.warning(
                        "Out of order ({}, {})".format(word, mention_chars[char_idx][0])
                    )
                curr_word[1] = min(curr_word[1], mention_chars[char_idx][1])
                curr_word[2] = min(curr_word[2], mention_chars[char_idx][2])
                curr_word[3] = max(curr_word[3], mention_chars[char_idx][3])
                curr_word[4] = max(curr_word[4], mention_chars[char_idx][4])
                len_idx += len(mention_chars[char_idx][0])
                char_idx += 1
            words.append(curr_word)
        return words

    def get_char_boundaries(self, mention):
        #  mention_text = mention.get_text()
        mention_chars = []
        for obj in mention:
            if isinstance(obj, LTChar):
                x0, y0, x1, y1 = obj.bbox
                mention_chars.append([obj.get_text(), y0, x0, y1, x1])
        return mention_chars

    def get_html_others(self, tag: str, box: List[float], page_num: int) -> Element:
        element = self.doc.createElement("div")
        element.setAttribute("class", "ocrx_block")
        element.setAttribute("pdftotree", tag)  # for backward-compatibility
        top, left, bottom, right = [int(x) for x in box]
        element.setAttribute("title", f"bbox {left} {top} {right} {bottom}")
        elems: List[LTTextLine] = get_mentions_within_bbox(
            box, self.elems[page_num].mentions
        )
        elems.sort(key=cmp_to_key(reading_order))
        for elem in elems:
            line_element = self.doc.createElement("span")
            element.appendChild(line_element)
            line_element.setAttribute("class", "ocrx_line")
            line_element.setAttribute(
                "title",
                f"bbox {int(elem.x0)} {int(elem.y0)} {int(elem.x1)} {int(elem.y1)}",
            )
            words = self.get_word_boundaries(elem)
            for word in words:
                top, left, bottom, right = [int(x) for x in word[1:]]
                # escape special HTML chars
                text = html.escape(word[0])

                word_element = self.doc.createElement("span")
                line_element.appendChild(word_element)
                word_element.setAttribute("class", "ocrx_word")
                word_element.setAttribute(
                    "title", f"bbox {left} {top} {right} {bottom}"
                )
                word_element.appendChild(self.doc.createTextNode(text))
        return element

    def get_html_table(self, table: List[float], page_num) -> Optional[Element]:
        """Recognize a table using tabula and return a DOM element.

        :param table: bbox for a table (top,left,bottom,right)
        :param page_num: 1-based page number
        :return: DOM element for a table
        """
        logger.debug(f"Calling tabula at page: {page_num} and area: {table}.")
        table_json = tabula.read_pdf(
            self.pdf_file, pages=page_num, area=table, output_format="json"
        )
        logger.debug(f"Tabula recognized {len(table_json)} table(s).")
        if len(table_json) == 0:
            return None
        table_element = self.doc.createElement("table")
        table_element.setAttribute("class", "ocr_table")
        top = int(table_json[0]["top"])
        left = int(table_json[0]["left"])
        bottom = int(table_json[0]["bottom"])
        right = int(table_json[0]["right"])
        table_element.setAttribute("title", f"bbox {left} {top} {right} {bottom}")
        for i, row in enumerate(table_json[0]["data"]):
            row_element = self.doc.createElement("tr")
            table_element.appendChild(row_element)
            for j, cell in enumerate(row):
                # It is not explicitly stated anywhere but tabula seems to use the cell
                # bbox to represent that of cell itself rather than that of text inside.
                # Note: bbox could be [0, 0, 0, 0] if tabula recognizes no text inside.
                box: List[float] = [
                    cell["top"],
                    cell["left"],
                    cell["top"] + cell["height"],
                    cell["left"] + cell["width"],
                ]
                cell_element = self.doc.createElement("td")
                row_element.appendChild(cell_element)
                elems = get_mentions_within_bbox(box, self.elems[page_num].mentions)
                if len(elems) == 0:
                    continue
                cell_element.setAttribute(
                    "title",
                    f"bbox {int(box[1])} {int(box[0])} {int(box[3])} {int(box[2])}",
                )
                elems.sort(key=cmp_to_key(reading_order))
                for elem in elems:
                    line_element = self.doc.createElement("span")
                    cell_element.appendChild(line_element)
                    line_element.setAttribute("class", "ocrx_line")
                    line_element.setAttribute(
                        "title",
                        " ".join(["bbox"] + [str(int(_)) for _ in elem.bbox]),
                    )
                    words = self.get_word_boundaries(elem)
                    for word in words:
                        top = int(word[1])
                        left = int(word[2])
                        bottom = int(word[3])
                        right = int(word[4])
                        # escape special HTML chars
                        text = html.escape(word[0])

                        word_element = self.doc.createElement("span")
                        line_element.appendChild(word_element)
                        word_element.setAttribute("class", "ocrx_word")
                        word_element.setAttribute(
                            "title", f"bbox {left} {top} {right} {bottom}"
                        )
                        word_element.appendChild(self.doc.createTextNode(text))
        return table_element
