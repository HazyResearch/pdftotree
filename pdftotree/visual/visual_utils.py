import glob
import os

import keras.backend as K
import numpy as np
import selectivesearch
from keras.preprocessing.image import load_img, img_to_array
from PyPDF2 import PdfFileReader
from wand.color import Color
from wand.image import Image


def predict_heatmap(pdf_path, page_num, model, img_dim=448, img_dir='tmp/img'):
    """
    Return an image corresponding to the page of the pdf
    documents saved at pdf_path. If the image is not found in img_dir this
    function creates it and saves it in img_dir.

    :param pdf_path: path to the pdf document.
    :param page_num: page number to create image from in the pdf file.
    :return:
    """
    if not os.path.isdir(img_dir):
        print("\nCreating image folder at {}".format(img_dir))
        os.makedirs(img_dir)
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    # TODO: add hashing function to make sure name is unique
    # TODO: add parallelization
    img_path = os.path.join(img_dir, pdf_name + '-{}.png'.format(page_num))
    if not os.path.isfile(img_path):
        # create image for a page in the pdf document and save it in img_dir
        save_image(pdf_path, img_path, page_num)
    image = load_img(img_path, grayscale=True, target_size=(img_dim, img_dim))
    image = img_to_array(image, data_format=K.image_data_format())
    image = image.reshape((img_dim, img_dim, 1)).repeat(
        3, axis=2).reshape((1, img_dim, img_dim, 3))
    return image.astype(np.uint8).reshape(
        (img_dim, img_dim, 3)), model.predict(image).reshape((img_dim,
                                                              img_dim))


def save_image(pdf_path, img_path, page_num):
    """

    Creates images for a page of the input pdf document and saves it
    at img_path.

    :param pdf_path: path to pdf to create images for.
    :param img_path: path where to save the images.
    :param page_num: page number to create image from in the pdf file.
    :return:
    """
    pdf_img = Image(filename='{}[{}]'.format(pdf_path, page_num))
    with pdf_img.convert('png') as converted:
        # Set white background.
        converted.background_color = Color('white')
        converted.alpha_channel = 'remove'
        converted.save(filename=img_path)


def do_intersect(bb1, bb2):
    """
    Helper function that returns True if two bounding boxes overlap.
    """
    if (bb1[0] + bb1[2] < bb2[0] or bb2[0] + bb2[2] < bb1[0]):
        return False
    if (bb1[1] + bb1[3] < bb2[1] or bb2[1] + bb2[3] < bb1[1]):
        return False
    return True


def get_bboxes(img,
               mask,
               nb_boxes=100,
               score_thresh=0.5,
               iou_thresh=0.2,
               prop_size=0.09,
               prop_scale=1.2):
    """
    Uses selective search to generate candidate bounding boxes and keeps the ones that have the largest
    iou with the predicted mask.

    :param img: original image
    :param mask: predicted mask
    :param nb_boxes: max number of candidate bounding boxes
    :param score_thresh: scre threshold to consider prediction is True
    :param iou_thresh: iou threshold to consider a candidate is a correct region
    :param prop_size: selective search parameter
    :param prop_scale: selective search parameter, larger prop_scale favorizes large boudning boxes
    :return: list of bounding boxes and ious, boudning boxes are tuples (left, top, width, height)
    """
    min_size = int(img.shape[0] * prop_size * img.shape[1] * prop_size)
    scale = int(img.shape[0] * prop_scale)
    # TODO: cross validate for multiple values of prop_size, prop_scale, and nb_bboxes
    img_lbl, regions = selectivesearch.selective_search(
        img, scale=scale, sigma=0.8, min_size=min_size)
    rect = [None] * nb_boxes
    max_iou = -1 * np.ones(nb_boxes)
    mask = 1. * (mask > score_thresh)
    # compute iou for each candidate bounding box and save top nb_bboxes
    for region in regions:
        left, top, width, height = region["rect"]
        intersection = mask[top:top + height, left:left + width].sum()
        union = height * width + mask.sum() - intersection
        iou = intersection / union
        idx = np.argmin(max_iou)
        if iou > max_iou[idx]:
            max_iou[idx] = iou
            rect[idx] = region["rect"]
    # Exclusive maximum
    remove_indexes = max_iou == -1
    bboxes = []
    filtered_ious = []
    for idx in np.argsort([-x for x in max_iou]):
        if remove_indexes[idx]:
            # no more tables bounding boxes
            break
        if len(bboxes) == 0:
            # first candidate table bounding box
            if max_iou[idx] > iou_thresh:
                bboxes += [rect[idx]]
                filtered_ious += [max_iou[idx]]
            else:
                # No tables in this document
                break
        else:
            # If it doensn't intersect with any other bounding box
            if not any([
                    do_intersect(rect[idx], bboxes[k])
                    for k in range(len(bboxes))
            ]):
                if max_iou[idx] > iou_thresh:
                    bboxes += [rect[idx]]
                    filtered_ious += [max_iou[idx]]
    return bboxes, filtered_ious
