import numpy as np
from wand.color import Color
from wand.display import display
from wand.drawing import Drawing
from wand.image import Image


def display_bounding_boxes(img, blocks, alternatecolors=False, color=Color('blue')):
    """
    Displays each of the bounding boxes passed in 'boxes' on an image of the pdf
    pointed to by pdf_file
    boxes is a list of 5-tuples (page, top, left, bottom, right)
    """
    draw = Drawing()
    draw.fill_color = Color('rgba(0, 0, 0, 0)')
    draw.stroke_color = color
    for block in blocks:
        top, left, bottom, right = block[-4:]
        if alternatecolors:
            draw.stroke_color = Color('rgba({},{},{}, 1)'.format(
                    str(np.random.randint(255)), str(np.random.randint(255)), str(np.random.randint(255))))
        draw.rectangle(left=float(left), top=float(top), right=float(right), bottom=float(bottom))
        draw(img)
    display(img)


def display_bounding_boxes_within_notebook(page_num, extractor, blocks, alternatecolors=False, color=Color('blue')):
    """
    Displays each of the bounding boxes passed in 'boxes' on an image of the pdf
    pointed to by pdf_file
    boxes is a list of 5-tuples (page, top, left, bottom, right)
    """
    elems = extractor.elems[page_num]
    page_width, page_height = int(elems.layout.width), int(elems.layout.height)
    img = pdf_to_img(extractor.pdf_file, page_num, page_width, page_height)
    draw = Drawing()
    draw.fill_color = Color('rgba(0, 0, 0, 0)')
    draw.stroke_color = color
    for block in blocks:
        top, left, bottom, right = block[-4:]
        if alternatecolors:
            draw.stroke_color = Color('rgba({},{},{}, 1)'.format(
                    str(np.random.randint(255)), str(np.random.randint(255)), str(np.random.randint(255))))
        draw.rectangle(left=float(left), top=float(top), right=float(right), bottom=float(bottom))
        draw(img)
    return img


def pdf_to_img(pdf_file, page_num, page_width, page_height):
    """
    Converts pdf file into image
    :param pdf_file: path to the pdf file
    :param page_num: page number to convert (index starting at 1)
    :return: wand image object
    """
    img = Image(filename='{}[{}]'.format(pdf_file, page_num - 1))
    img.resize(page_width, page_height)
    return img


