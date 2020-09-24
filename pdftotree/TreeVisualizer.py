from typing import Tuple

from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

try:
    from IPython import get_ipython

    if "IPKernelApp" not in get_ipython().config:
        raise ImportError("console")
except (AttributeError, ImportError):
    from wand.display import display
else:
    from IPython.display import display

from wand.color import Color
from wand.drawing import Drawing
from wand.image import Image


class TreeVisualizer:
    """
    Object to display bounding boxes on a pdf document
    """

    def __init__(self, pdf_file):
        """
        :param pdf_path: directory where documents are stored
        :return:
        """
        self.pdf_file = pdf_file

    def display_boxes(self, tree, html_path, filename_prefix, alternate_colors=False):
        """
        Displays each of the bounding boxes passed in 'boxes' on images of the pdf
        pointed to by pdf_file
        boxes is a list of 5-tuples (page, top, left, bottom, right)
        """
        imgs = []
        colors = {
            "section_header": Color("blue"),
            "figure": Color("green"),
            "figure_caption": Color("green"),
            "table_caption": Color("red"),
            "list": Color("yellow"),
            "paragraph": Color("gray"),
            "table": Color("red"),
            "header": Color("brown"),
        }
        for i, page_num in enumerate(tree.keys()):
            img = self.pdf_to_img(page_num)
            draw = Drawing()
            draw.fill_color = Color("rgba(0, 0, 0, 0.0)")
            for clust in tree[page_num]:
                for (pnum, pwidth, pheight, top, left, bottom, right) in tree[page_num][
                    clust
                ]:
                    draw.stroke_color = colors[clust]
                    draw.rectangle(left=left, top=top, right=right, bottom=bottom)
                    draw.push()
                    draw.font_size = 20
                    draw.font_weight = 10
                    draw.fill_color = colors[clust]
                    if int(left) > 0 and int(top) > 0:
                        draw.text(x=int(left), y=int(top), body=clust)
                    draw.pop()
            draw(img)
            img.save(filename=html_path + filename_prefix + "_page_" + str(i) + ".png")
            imgs.append(img)
        return imgs

    def display_candidates(self, tree, html_path, filename_prefix):
        """
        Displays the bounding boxes corresponding to candidates on an image of the pdf
        boxes is a list of 5-tuples (page, top, left, bottom, right)
        """
        imgs = self.display_boxes(
            tree, html_path, filename_prefix, alternate_colors=True
        )
        return display(*imgs)

    def pdf_to_img(self, page_num, pdf_dim=None):
        """
        Converts pdf file into image
        :param pdf_file: path to the pdf file
        :param page_num: page number to convert (index starting at 1)
        :return: wand image object
        """
        if not pdf_dim:
            pdf_dim = get_pdf_dim(self.pdf_file)
        page_width, page_height = pdf_dim
        img = Image(filename="{}[{}]".format(self.pdf_file, page_num - 1))
        img.resize(page_width, page_height)
        return img


def get_pdf_dim(pdf_file) -> Tuple[int, int]:
    with open(pdf_file, "rb") as f:
        parser = PDFParser(f)
        doc = PDFDocument(parser)
        # Look at the 1st page only.
        page = next(PDFPage.create_pages(doc))
        _, _, page_width, page_height = page.mediabox
    return page_width, page_height
