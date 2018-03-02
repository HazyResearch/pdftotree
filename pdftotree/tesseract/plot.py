import matplotlib.pyplot as plt
import matplotlib.patches as patches

def plot(soup, extracts):
    def makeBox(bbox):
        return {
            '_left': int(bbox[0]),
            '_top': int(bbox[1]),
            '_right': int(bbox[2]),
            '_bottom': int(bbox[3]),
            'width': int(bbox[2]) - int(bbox[0]),
            'height': int(bbox[3]) - int(bbox[1])
        }

    def getbbox(title):
        title_parts = title.split(';')
        for part in title_parts:
            if part.strip()[0:4] == 'bbox':
                return part.replace('bbox', '').strip().split()

        return

    page_boxes = [makeBox(getbbox(page.get('title'))) for page in soup.find_all('div', 'ocr_page')]
    carea_boxes = [makeBox(getbbox(carea.get('title'))) for carea in soup.find_all('div', 'ocr_carea')]
    word_boxes = [makeBox(getbbox(word.get('title'))) for word in soup.find_all('span', 'ocrx_word')]
    line_boxes = [makeBox(getbbox(box.get('title'))) for box in soup.find_all('span', 'ocr_line')]
#    pars = [makeBox(getbbox(box.get('title'))) for box in soup.find_all('p', 'ocr_par')]

    fig = plt.figure()
    ax = fig.add_subplot(111, aspect='equal')

    for box in line_boxes:
        ax.add_patch(patches.Rectangle(
            (box['_left'], box['_top']),
            box['_right'] - box['_left'],
            box['_bottom'] - box['_top'],
            fill=False,
            linewidth=0.5,
            edgecolor="#85DB18"
            )
            )

    # for box in pars:
    #     ax.add_patch(patches.Rectangle(
    #         (box['_left'], box['_top']),
    #         box['_right'] - box['_left'],
    #         box['_bottom'] - box['_top'],
    #         fill=False,
    #         linewidth=0.5,
    #         edgecolor="#85DB18"
    #         )
    #         )

    for box in carea_boxes:
        ax.add_patch(patches.Rectangle(
            (box['_left'], box['_top']),
            box['_right'] - box['_left'],
            box['_bottom'] - box['_top'],
            fill=False,
            linewidth=0.5,
            edgecolor="#0000FF"
            )
            )


    for box in word_boxes:
        ax.add_patch(patches.Rectangle(
            (box['_left'], box['_top']),
            box['_right'] - box['_left'],
            box['_bottom'] - box['_top'],
            fill=False,
            linewidth=0.1,
            edgecolor="#000000"
            )
            )

    for box in extracts:
        ax.add_patch(patches.Rectangle(
            (box['x1'], box['y1']),
            box['x2'] - box['x1'],
            box['y2'] - box['y1'],
            fill=False,
            linewidth=1,
            edgecolor="#E79245"
            )
            )

    plt.ylim(0,page_boxes[0]['_bottom'])
    plt.xlim(0,page_boxes[0]['_right'])
    plt.axis("off")
    ax = plt.gca()
    ax.invert_yaxis()
    plt.axis('off')
    fig.savefig('page_3.png', dpi=400, bbox_inches='tight', pad_inches=0)
