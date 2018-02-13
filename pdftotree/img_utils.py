'''
Created on Oct 11, 2015

@author: xiao
'''
import os
from sys import platform as _platform

import numpy as np
from PIL import ImageFont, Image, ImageDraw

from pdftotree.pdf.vector_utils import center
from pdfminer.layout import LTAnno

white = (255, 255, 255)
black = (0, 0, 0)
red = (255, 0, 0)
green = (0, 255, 0)
blue = (0, 0, 255)
default_font_size = 10
_font_cache = {}


def lazy_load_font(font_size=default_font_size):
    '''
    Lazy loading font according to system platform
    '''
    if font_size not in _font_cache:
        if _platform.startswith('darwin'):
            font_path = "/Library/Fonts/Arial.ttf"
        elif _platform.startswith('linux'):
            font_path = "/usr/share/fonts/truetype/ubuntu-font-family/UbuntuMono-R.ttf"
        elif _platform.startswith('win32'):
            font_path = "C:\\Windows\\Fonts\\arial.ttf"
        _font_cache[font_size] = ImageFont.truetype(font_path, font_size)
    return _font_cache[font_size]


def normalize_bbox(coords, ymax, scaler=2):
    '''
    scales all coordinates and flip y axis due to different
    origin coordinates (top left vs. bottom left)
    '''
    return [coords[0] * scaler,
            ymax - (coords[3] * scaler),
            coords[2] * scaler,
            ymax - (coords[1] * scaler)]


def normalize_pts(pts, ymax, scaler=2):
    '''
    scales all coordinates and flip y axis due to different
    origin coordinates (top left vs. bottom left)
    '''
    return [(x * scaler, ymax - (y * scaler)) for x, y in pts]


def create_img(bbox=(0, 0, 200, 200)):
    # create new white image
    img = Image.new("RGBA", bbox[-2:], white)
    return img, ImageDraw.Draw(img)


def render(draw, bbox, text=None, align=None, fill=None, outline=black):
    draw.rectangle(bbox, outline=outline, fill=fill)
    if text:
        coord = center(bbox) if align == 'center' else bbox[:2]
        draw.text(coord, text, black, font=lazy_load_font())


def load_image(pdf_path, page_num):
    pdf_file = os.path.basename(pdf_path)
    basename = pdf_file[:-4]
    image_name = '%s-%06d.png' % (basename, page_num + 1)
    scan = Image.open(os.path.join('private/imgs/', image_name))
    #     scan.filter(ImageFilter.GaussianBlur(2)).show()
    # make it black and white for simplicity
    return scan.convert('1')


def load_pixels(pdf_path, page_num):
    scan_img = load_image(pdf_path, page_num)
    raw_data = np.array(scan_img.getdata())
    return (raw_data > 0).reshape(scan_img.height, scan_img.width), scan_img


def fill(mat, orig_bbox, margin):
    pass


def render_debug_img(file_name,
                     page_num,
                     elems,
                     nodes=[],
                     scaler=1,
                     print_segments=False,
                     print_curves=True,
                     print_table_bbox=True,
                     print_text_as_rect=True,
                     ):
    '''
    Shows an image rendering of the pdf page along with debugging
    info printed
    '''
    # For debugging show the boolean pixels in black white grayscale
    height = scaler * int(elems.layout.height)
    width = scaler * int(elems.layout.width)
    debug_img, draw = create_img((0, 0, width, height))
    font = lazy_load_font()
    large_font = lazy_load_font(24)

    if print_curves:
        for i, c in enumerate(elems.curves):
            if len(c.pts) > 1:
                draw.polygon(c.pts, outline=blue)
            draw.rectangle(c.bbox, fill=blue)
            # for fig in elems.figures:
            #     draw.rectangle(fig.bbox, fill = blue)

    for i, m in enumerate(elems.mentions):
        if isinstance(m, LTAnno): continue
        if print_text_as_rect:
            fill = 'pink' if hasattr(m, 'feats') and m.feats['is_cell'] else green
            #             fill = green
            draw.rectangle(m.bbox, fill=fill)
            # draw.text(center(m.bbox), str(i), black, font = font) # Draw id
            draw.text(m.bbox[:2], m.get_text(), black, font=font)  # Draw mention content
        else:
            draw.text(m.bbox[:2], m.get_text(), 'black', font=font)

    if print_segments:
        # draw skeleton for all segments
        for i, s in enumerate(elems.segments):
            draw.line(s.bbox, fill='black')

    if print_table_bbox:
        for node in nodes:
            is_table = node.is_table()
            color = 'red' if is_table else 'green'
            draw.rectangle(node.bbox, outline=color)
            if is_table:
                # text = 'Borderless' if node.is_borderless() else 'Bordered'
                text = 'Table'
                draw.rectangle(node.bbox, outline=color)
                draw.text(node.bbox[:2], text, red, font=large_font)

    # Water mark with file name so we can identify among multiple images
    if file_name and page_num is not None:
        water_mark = file_name + ':page ' + str(page_num + 1) + '@%dx%d' % (width, height)
        draw.text((10, 10), water_mark, black, font=font)
    debug_img.show()
    return debug_img
