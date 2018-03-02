from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from builtins import str
from builtins import range
from past.utils import old_div
from bs4 import BeautifulSoup
from .plot import plot
import math
import re
import numpy as np
import itertools
from . import helpers
import glob
np.set_printoptions(threshold=np.inf)
# Grab this much extra space around tables
padding = 10

'''
Tesseract hierarchy:

div.ocr_page
    div.ocr_carea
        p.ocr_par
            span.ocr_line
                span.ocrx_word
'''

'''
table definition:
    word separation index > document median + 1 std
    word area index < document median - 1 std
    never one line

text block:
    word separation index < document median + 1 std
    word area index === document median +/- (1 std / 2)
    never one line
    On second pass, width is 2 sigma

caption:
    best: starts with table|figure|fig|map followed by an optional period and a number on a dedicated line
    good: starts with table|figure|fig|map followed by an optional period and a number on a line with other text
    ok: starts with some words followed by a number in a text area with an average text height smaller than the average of other text areas on the page

'''

# Determine how tabley a given area is by comparing its attributes to those of the entire document
# Input is a page of areas, output is the same page, but with a 'type' and 'table_score' assigned
# to each area
def classify_areas(page, doc_stats):
    y_mins = [area['y1'] for area in page['areas']]
    y_maxes = [area['y2'] for area in page['areas']]

    for area in page['areas']:
        # The table_score keeps track of how "table-y" an area is, i.e. how many characteristics it has consistent with tables
        area['table_score'] = 0
        # Remove gaps smaller than the median gap between words
        area['gaps'] = [gap for gap in area['gaps'] if gap > doc_stats['word_separation_median']]

        # Add to the table score for each gap (each gap adds one point)
        for gap in area['gaps']:
            area['table_score'] += 4

        # Giant blank areas are probably tables
        if np.nanmean(area['line_heights']) > doc_stats['line_height_avg'] + 100 and area['area'] > 250000:
            area['type'] = 'table'
            area['table_score'] += 10

        # Separator lines are only one line, have no words or other attributes
        elif area['lines'] == 1 and area['words'] == 0 and area['word_separation_index'] == 0 and area['word_height_index'] == 0 and area['word_height_avg'] == 0:
            area['type'] = 'line'

        elif (area['word_separation_index'] >= (doc_stats['word_separation_index_median'] + doc_stats['word_separation_index_std'])) and (area['word_area_index'] <= (doc_stats['word_area_index_median'] - doc_stats['word_area_index_std'])) and area['lines'] > 1:
            area['type'] = 'table'

        elif (area['word_separation_index'] < (doc_stats['word_separation_index_median'] + doc_stats['word_separation_index_std'])) and (area['word_area_index'] > (doc_stats['word_area_index_median'] - (old_div(doc_stats['word_area_index_std'],float(2)))) and area['word_area_index'] < (doc_stats['word_area_index_median'] + (old_div(doc_stats['word_area_index_std'],float(2))))) and area['lines'] > 1:
            area['type'] = 'text block'

        # Probably a header or footer
        elif area['lines'] == 1 and (area['y1'] == min(y_mins) or area['y2'] == max(y_maxes)):
            area['type'] = 'decoration'

        # Else, unclassified
        else:
            area['type'] = 'other'

        # Tally other attributes that are indicative of tables
        if area['word_separation_index'] >= (doc_stats['word_separation_index_median'] + doc_stats['word_separation_index_std']):
            area['table_score'] += 1
        if area['word_area_index'] <= (doc_stats['word_area_index_median'] - doc_stats['word_area_index_std']):
            area['table_score'] += 1
        if area['lines'] > 1:
            area['table_score'] += 1

    # Summarize the width of text blocks in the document


    # Find lines - can be line breaks between paragraphs or divider lines in tables
    line_breaks = [area for area in page['areas'] if area['type'] == 'line']

    # If a line intersects an area, classify that area as a table
    for area in page['areas']:
        if area['type'] != 'line':
            intersecting_line_breaks = [line for line in line_breaks if helpers.rectangles_intersect(area, line)]
            for line in intersecting_line_breaks:
                area['type'] = 'table'
                area['table_score'] += 1

        # Don't call text blocks with small text text blocks
        if area['type'] == 'text block' and area['word_height_avg'] < (doc_stats['word_height_avg'] - (old_div(doc_stats['word_height_avg_std'],4))) and area['lines'] < 12:
            area['type'] = 'caption'

        lines = [line for line in area['soup'].find_all('span', 'ocr_line')]
        if len(lines):
            clean_line = lines[0].getText().strip().replace('\n', ' ').replace('  ', ' ').lower()

        if (area['type'] == 'text block' or area['type'] == 'other') and re.match('^(table|figure|fig|map)(\.)? \w{1,5}(\S)?(\w{1,5})?(\.)?', clean_line, flags=re.IGNORECASE|re.MULTILINE):
            area['type'] = 'caption'

    for area in page['areas']:
        if area['type'] != 'table' and area['table_score'] > 10:
            area['type'] = 'table'

    return page

# Summarize the area stats of a given document
def summarize_document(area_stats):
    # Don't use areas with 1 line or no words in creating summary statistics
    return {
        'word_separation_mean': np.nanmean([np.nanmean(area['word_distances']) for area in area_stats if area['words'] > 0 and area['lines'] > 1]),
        'word_separation_median': np.nanmedian([np.nanmean(area['word_distances']) for area in area_stats if area['words'] > 0 and area['lines'] > 1]),
        'word_separation_std': np.nanstd([np.nanmean(area['word_distances'])for area in area_stats if area['words'] > 0 and area['lines'] > 1]),
        'word_separation_index_mean': np.nanmean([area['word_separation_index'] for area in area_stats if area['words'] > 0 and area['lines'] > 1]),
        'word_separation_index_median': np.nanmedian([area['word_separation_index'] for area in area_stats if area['words'] > 0 and area['lines'] > 1]),
        'word_separation_index_std': np.nanstd([area['word_separation_index'] for area in area_stats if area['words'] > 0 and area['lines'] > 1]),
        'word_height_index_mean': np.nanmean([area['word_height_index'] for area in area_stats if area['words'] > 0 and area['lines'] > 1]),
        'word_height_index_median': np.nanmedian([area['word_height_index'] for area in area_stats if area['words'] > 0 and area['lines'] > 1]),
        'word_height_index_std': np.nanstd([area['word_height_index'] for area in area_stats if area['words'] > 0 and area['lines'] > 1]),
        'word_area_index_mean': np.nanmean([area['word_area_index'] for area in area_stats if area['words'] > 0 and area['lines'] > 1]),
        'word_area_index_median': np.nanmedian([area['word_area_index'] for area in area_stats if area['words'] > 0 and area['lines'] > 1]),
        'word_area_index_std': np.nanstd([area['word_area_index'] for area in area_stats if area['words'] > 0 and area['lines'] > 1]),
        'word_height_avg': np.nanmean([area['word_height_avg'] for area in area_stats if area['words'] > 0 and area['lines'] > 1]),
        'word_height_avg_median': np.nanmedian([area['word_height_avg'] for area in area_stats if area['words'] > 0 and area['lines'] > 1]),
        'word_height_avg_std': np.nanstd([area['word_height_avg'] for area in area_stats if area['words'] > 0 and area['lines'] > 1]),

        'line_height_avg': np.nanmean([a for a in area['line_heights'] for area in area_stats]),
        'line_height_std': np.nanstd([a for a in area['line_heights'] for area in area_stats])
    }

def line_word_height(line):
    # For each line, get words
    words = line.find_all('span', 'ocrx_word')
    word_heights = []
    for word_idx, word in enumerate(words):
        wordbbox = helpers.extractbbox(word.get('title'))
        word_heights.append(wordbbox['y2'] - wordbbox['y1'])

    avg = 0 if len(words) == 0 else np.nanmean(word_heights)

    return avg

def area_summary(area):
    summary = {}
    summary['soup'] = area
    # Bounding box (x1, y1, x2, y2)
    summary.update(helpers.extractbbox(area.get('title')))

    # Number of lines
    summary['lines'] = len(area.find_all('span', 'ocr_line'))
    summary['line_heights'] = []

    for line in area.find_all('span', 'ocr_line'):
        bbox = helpers.extractbbox(line.get('title'))
        height = bbox['y2'] - bbox['y1']
        summary['line_heights'].append(height)

    # Number of words
    summary['words'] = len([_f for _f in area.getText().strip().replace('\n', ' ').replace('  ', ' ').split(' ') if _f])

    # Area
    summary['area'] = (summary['x2'] - summary['x1']) * (summary['y2'] - summary['y1'])

    # Get spacing of words
    summary['x_gaps'] = np.zeros(summary['x2'] - summary['x1'], dtype=np.int)

    # Words per line
    summary['words_in_line'] = []
    summary['word_distances'] = []
    summary['word_heights'] = []
    summary['word_areas'] = []
    summary['words_per_line'] = []

    # Iterate on each line in the area
    for line in area.find_all('span', 'ocr_line'):
        # For each line, get words
        words = line.find_all('span', 'ocrx_word')

        # Record the number of words in this line
        summary['words_per_line'].append(len(words))

        for word_idx, word in enumerate(words):
            wordbbox = helpers.extractbbox(word.get('title'))
            summary['word_heights'].append(wordbbox['y2'] - wordbbox['y1'])
            summary['word_areas'].append((wordbbox['x2'] - wordbbox['x1']) * (wordbbox['y2'] - wordbbox['y1']))

            for x in range(wordbbox['x1'] - summary['x1'], wordbbox['x2'] - summary['x1']):
                summary['x_gaps'][x] = 1

            # If word isn't the last word in a line, get distance between word and word + 1
            if word_idx != (len(words) - 1):
                wordP1bbox = helpers.extractbbox(words[ word_idx + 1 ].get('title'))
                # Pythagorean theorum FTW
                summary['word_distances'].append(math.sqrt(math.pow((wordP1bbox['x1'] - wordbbox['x2']), 2) + math.pow((wordP1bbox['y1'] - wordbbox['y1']), 2)))

    # Count whitespace gaps
    summary['gaps'] = helpers.get_gaps(summary['x_gaps'])

    # Get the mean of the differences of the word distances (all the same == 0, difference increases away from 0)
    summary['word_separation_index'] = 0 if summary['words'] == 0 else helpers.meanOfDifferences(summary['word_distances'])

    # Quantify the variation in the height of words in this area
    summary['word_height_index'] = 0 if summary['words'] == 0 else helpers.meanOfDifferences(summary['word_heights'])

    # Get the average word height of this area
    summary['word_height_avg'] = 0 if summary['words'] == 0 else np.nanmean(summary['word_heights'])

    # Get word/area ratio
    summary['word_area_index'] = 0 if summary['words'] == 0 else old_div(np.sum(summary['word_areas']), float(summary['area']))

    return summary

# Entry into table extraction
def extract_tables(document_path):
    page_paths = glob.glob(document_path + '/tesseract/*.html')

    pages = []
    figures = []
    for page_no, page in enumerate(page_paths):
        num = page.split('/')[-1].replace('.html', '').replace('page_', '')
        # Read in each tesseract page with BeautifulSoup so we can look at the document holistically
        with open(page) as hocr:
            text = hocr.read()
            soup = BeautifulSoup(text, 'html.parser')
            pages.append({
                'page_no': num,
                'soup': soup,
                'page': helpers.extractbbox(soup.find_all('div', 'ocr_page')[0].get('title')),
                'areas': [ area_summary(area) for area in soup.find_all('div', 'ocr_carea') ],
                'lines': [ line for line in soup.find_all('span', 'ocr_line') ]
            })

            # Attempt to identify all charts/tables/etc in the paper by looking at the text layer
            # i.e. It is useful for us to know if the text mentions "see table 4", because if the caption
            # for table 4 is distorted in the text layer ("teble 4", for example), we can still guess that
            # it is table 4 because of it's position in the document and our prior knowledge that a table 4
            # exists
            page_content = soup.getText().strip().replace('\n', ' ').replace('  ', ' ').lower()
            for result in re.findall('(table|figure|fig|map|appendix|app|appx|tbl)(\.)? (\d+)(\.)?', page_content, flags=re.IGNORECASE):
                figures.append(' '.join(' '.join(result).replace('.', '').replace('figure', 'fig').split()).lower())

    # Clean up the list of figures/tables/etc
    figures = sorted(set(figures))
    pruned_figures = []
    order = 1
    current_type = ''
    for fig in figures:
        parts = fig.split(' ')
        if current_type == '':
            current_type = parts[0]
            order = int(parts[1])
            pruned_figures.append(fig)
        elif parts[0] == current_type and int(parts[1]) == (order + 1):
            order = int(parts[1])
            pruned_figures.append(fig)
        elif parts[0] != current_type:
            current_type = parts[0]
            order = int(parts[1])
            pruned_figures.append(fig)

    # map/reduce
    # print pages
    page_areas = [ page['areas'] for page in pages ]
    area_stats = [ area for areas in page_areas for area in areas ]
    # print page_areas, area_stats

    # Calculate summary stats for the document from all areas identified by Tesseract
    doc_stats = summarize_document(area_stats)

    # Classify and assign a table score to each area in each page
    pages = [classify_areas(page, doc_stats) for page in pages]

    # Identify the areas that classified as 'text block's and record their widths
    text_block_widths = []
    for page in pages:
        for area in page['areas']:
            if area['type'] == 'text block':
                text_block_widths.append( area['x2'] - area['x1'] )


    # Calculate stats about the text blocks in the whole document. First get rid of outliers
    two_sigma = [ val for val in text_block_widths if val > (np.nanmedian(text_block_widths) - (np.nanstd(text_block_widths) * 2)) and val < (np.nanmedian(text_block_widths) + (np.nanstd(text_block_widths) * 2))]

    # Update doc stats, then reclassify
    doc_stats['text_block_median'] = np.nanmedian(two_sigma)
    doc_stats['text_block_std'] = np.nanstd(two_sigma)

    # Reclassify all areas based on the stats of the whole document
    for page in pages:
        for area in page['areas']:
            width = area['x2'] - area['x1']
            # Not a text block if it's width is outside of 2 sigma
            if area['type'] == 'text block' and (width < doc_stats['text_block_median'] - (2 * doc_stats['text_block_std']) or width > doc_stats['text_block_median'] + (2 * doc_stats['text_block_std'])):
                area['type'] = 'other'


    doc_stats['found_tables'] = {}
    pruned_figures = sorted(set(pruned_figures))
    print('these tables were found --')
    for each in pruned_figures:
        print('    ', each)
        doc_stats['found_tables'][each] = False

    toWrite = ""
    for page in pages:
        from PIL import Image
        # im=Image.open(document_path+"png/"+str(page.split(".html")[0].split("/")[-1])+".png")
        im=Image.open(document_path+"png/page_"+str(page["page_no"])+".png")
        # print im.size
        page_extracts = process_page(doc_stats, page)

        found = []
        for e in page_extracts:
            if e['name'] in found:
                 e['name'] = e['name'] + '*'

            found.append(e['name'])

        # DEBUG
        # if page['page_no'] == '5':
        #     for idx, area in enumerate(page['areas']):
        #         print 'Area %s -- %s (%s)' % (idx, area['type'], area['table_score'])
        #         print '    Lines: %s' % (area['lines'], )
        #         print '    Words: %s' % (area['words'], )
        #         print '    Area: %s' % (area['area'], )
        #         print '    Word separation index: %s' % ('%.2f' % area['word_separation_index'], )
        #         print '    Word height index: %s' % ('%.2f' % area['word_height_index'], )
        #         print '    Word height avg: %s' % ('%.2f' % area['word_height_avg'], )
        #         print '    Area covered by words: %s%%' % (int(area['word_area_index'] * 100), )
        #         print '    Average word height: %s' % ('%.2f' % area['word_height_avg'])
        #         print '    Gaps: %s' % (area['gaps'])
        #         print '    Line height average: %s' %(np.nanmean(area['line_heights']))
        #     plot(page['soup'], page_extracts)
        
        for table in page_extracts:
            if("table" in table["name"]):
                toWrite = toWrite + str((int(page['page_no']), im.size[0], im.size[1], table['y1'], table['x1'], table['y2'], table['x2'])) + ";"
            helpers.extract_table(document_path, page['page_no'], table)
    if(len(toWrite)>0):
        return toWrite+"\n"
    return("NO_TABLES\n")

def process_page(doc_stats, page):
    def find_above_and_below(extract):
        out = {
            'above': [],
            'below': [],
            'left': [],
            'right': []
        }
        for area_idx, area in enumerate(page['areas']):
            # Check if they overlap in x space
            if area['x1'] <= extract['x2'] and extract['x1'] <= area['x2']:
                # Check how *much* they overlap in x space
                # Number of pixels area overlaps with current extract extent
                overlap = max([ 0, abs(min([ area['x2'], extract['x2'] ]) - max([ extract['x1'], area['x1'] ])) ])
                area_length = area['x2'] - area['x1']
                percent_overlap = old_div(float(overlap), area_length)

                # If the area overlaps more than 90% in x space with the target area
                if percent_overlap >= 0.9:
                    # Check if this area is above or below the extract area
                    area_centroid = helpers.centroid(area)
                    extract_centroid = helpers.centroid(extract)
                    # If it is above
                    if area_centroid['y'] <= extract_centroid['y']:
                        # Work backwards so that when we iterate we start at the area closest to the extract
                        out['above'].insert(0, area_idx)
                    # If below
                    else:
                        out['below'].append(area_idx)

            # Check if they overlap in y space
            elif area['y1'] <= extract['y2'] and extract['y1'] <= area['y2']:
                overlap = max([ 0, abs(min([ area['y2'], extract['y2'] ]) - max([ extract['y1'], area['y1'] ])) ])
                area_length = area['y2'] - area['y1']
                percent_overlap = old_div(float(overlap), area_length)
                if percent_overlap >= 0.9:
                    area_centroid = helpers.centroid(area)
                    extract_centroid = helpers.centroid(extract)

                    if area_centroid['x'] <= extract_centroid['x']:
                        out['left'].insert(0, area_idx)
                    else:
                        out['right'].append(area_idx)
        return out


    def expand_extraction(extract_idx, props):
        # Iterate on above and below areas for each extract
        for direction, areas in extract_relations[extract_idx].items():
            stopped = False
            for area_idx in extract_relations[extract_idx][direction]:
                # Iterate on all other extracts, making sure that extending the current one won't run into any of the others
                for extract_idx2, props2 in extract_relations.items():
                    if extract_idx != extract_idx2:
                        will_intersect = helpers.rectangles_intersect(extracts[extract_idx2], helpers.enlarge_extract(extracts[extract_idx], page['areas'][area_idx]))
                        if will_intersect:
                            stopped = True
                            continue

                if stopped:
                    continue

                if page['areas'][area_idx]['type'] == 'possible table' and direction == extracts[extract_idx]['direction']:
                    #print 'extend', extracts[extract_idx]['name'], 'into possible table'
                    extracts[extract_idx].update(helpers.enlarge_extract(extracts[extract_idx], page['areas'][area_idx]))

                elif page['areas'][area_idx]['type'] == 'caption':
                    extracts[extract_idx].update(helpers.enlarge_extract(extracts[extract_idx], page['areas'][area_idx]))

                elif page['areas'][area_idx]['type'] == 'table':
                    #print 'extend', extracts[extract_idx]['name'], 'into table'
                    extracts[extract_idx].update(helpers.enlarge_extract(extracts[extract_idx], page['areas'][area_idx]))

                elif page['areas'][area_idx]['type'] == 'line':
                    #print 'extend', extracts[extract_idx]['name'], 'into line'
                    extracts[extract_idx].update(helpers.enlarge_extract(extracts[extract_idx], page['areas'][area_idx]))

                elif ((page['areas'][area_idx]['type'] == 'text block' or page['areas'][area_idx]['type'] == 'other') and page['areas'][area_idx]['word_height_avg'] < (doc_stats['word_height_avg'] - (old_div(doc_stats['word_height_avg_std'],4)))):
                    #print 'extend', extracts[extract_idx]['name'], 'into text'
                    extracts[extract_idx].update(helpers.enlarge_extract(extracts[extract_idx], page['areas'][area_idx]))

                else:
                    #print 'stop ', extracts[extract_idx]['name']
                    stopped = True


    # Find the captions/titles for charts, figures, maps, tables
    indicator_lines = []

    for line in page['lines']:
        # Remove nonsense
        clean_line = line.getText().strip().replace('\n', ' ').replace('  ', ' ').lower()
        # Find all lines that contain only a target word plus a number
        dedicated_line_matches = re.match('(table|figure|fig|map)(\.)? \d+(\.)?', clean_line, flags=re.IGNORECASE|re.MULTILINE)
        # Find all the lines that start with one of the target words and a number
        caption_matches = re.match('(table|figure|fig|map)(\.)? \d+(\.)', clean_line, flags=re.IGNORECASE|re.MULTILINE)
        # Problematic tesseract matches
        bad_tesseract_matches = re.match('^(table|figure|fig|map)(\.)? \w{1,5}(\S)?(\w{1,5})?(\.)?', clean_line, flags=re.IGNORECASE|re.MULTILINE)

        bbox = helpers.extractbbox(line.get('title'))
        # dedicated line (ex: Table 1)
        if dedicated_line_matches and dedicated_line_matches.group(0) == clean_line:
            bbox['name'] = dedicated_line_matches.group(0)
            print('  ', bbox['name'].replace('.', ''))
            indicator_lines.append(bbox)

        # Other
        elif caption_matches:
            bbox['name'] = caption_matches.group(0)
            print('  ',  bbox['name'].replace('.', ''))
            indicator_lines.append(bbox)

        elif bad_tesseract_matches:
            bbox['name'] = bad_tesseract_matches.group(0)
            print('  ', bbox['name'].replace('.', ''))
            indicator_lines.append(bbox)

    # Assign a caption to each table, and keep track of which captions are assigned to tables. caption_idx: [area_idx, area_idx, ...]
    caption_areas = {}
    for area_idx, area in enumerate(page['areas']):
        if area['type'] == 'table':
            # Get the distances between the given area and all captions
            distances = [helpers.min_distance(area, line) for line in indicator_lines]

            # The index of the nearest caption
            if len(distances) == 0:
                break

            nearest_caption = distances.index(min(distances))
            # Assign the nearest caption to the area
            area['caption'] = nearest_caption
            # Bookkeep
            try:
                caption_areas[nearest_caption].append(area_idx)
            except:
                caption_areas[nearest_caption] = [area_idx]

    '''
    If a page has tables unassigned to captions, those go in a different pile

    When it comes time to create extract areas from them, they play by different rules:
        + The starting extract area is simply the area(s) determined to be tables
        + Extract areas can eat each other / be combined
    '''

        # Need to go find the tables and create appropriate areas
        # Basically, treat them as extracts that can overlap, and then merge intersecting extracts

        # alternative_captions = []
        #
        # for line in page['lines']:
        #     # First make sure this line doesn't exist any tables
        #     line_bbox = helpers.extractbbox(line.get('title'))
        #     table_intersections = []
        #     for table in all_tables:
        #         if helpers.rectangles_intersect(page['areas'][table], line_bbox):
        #             table_intersections.append(True)
        #         else:
        #             table_intersections.append(False)
        #
        #     # If it does, skip it
        #     if True in table_intersections:
        #         continue
        #
        #     # Remove nonsense
        #     clean_line = line.getText().strip().replace('\n', ' ').replace('  ', ' ').lower()
        #     # mediocre caption matches
        #     ok_matches = re.match('^(.*?) \d+(\.)?', clean_line, flags=re.IGNORECASE)
        #
        #     '''
        #     Caption is good enough if the following are satisfied:
        #         + the average word height is less than the document's average word height - 1/4 average word height std
        #         + The line it is on does not intersect and table
        #     '''
        #     if ok_matches and line_word_height(line) < (doc_stats['word_height_avg'] - (doc_stats['word_height_avg_std']/4)):
        #          line_bbox['name'] = ok_matches.group(0)
        #          print 'Alt caption - ', line_bbox['name']
        #          alternative_captions.append(line_bbox)



    # Sanity check the caption-area assignments
    for caption, areas in caption_areas.items():
        # Only check if the caption is assigned to more than one area
        if len(areas) > 1:
            # draw a line through the middle of the caption that spans the page
            '''
              x1,y1 0 --------------
                    |               |
            - - - - | - - - - - - - | - - - - <-- Create this line
                    |               |
                     -------------- 0 x2,y2
            '''
            caption_line_y = indicator_lines[caption]['y1'] + (indicator_lines[caption]['y2'] - indicator_lines[caption]['y1'])
            caption_line = {
                'x1': page['page']['x1'],
                'y1': caption_line_y,
                'x2': page['page']['x2'],
                'y2': caption_line_y
            }

            # Get a list of unique combinations of areas for this caption (example: [(0,1), (1,3)] )
            area_combinations = list(itertools.combinations(caption_areas[caption], 2))

            # Draw a line between them
            '''
             -----------
            |           |
            |     a     |
            |      \    |
             -------\---
                     \ <------ area_connection_line
                 -----\-
                |      \|
        - - - - | - - -|\ - - - - - - -
                |      | \
                 ------   \
                           \
                    --------\--------------
                   |         \             |
                   |          \            |
                   |           b           |
                   |                       |
                   |                       |
                    -----------------------
            '''

            for pair in area_combinations:
                a = helpers.centroid(page['areas'][pair[0]])
                b = helpers.centroid(page['areas'][pair[1]])
                area_line = {
                    'x1': a['x'],
                    'y1': a['y'],
                    'x2': b['x'],
                    'y2': b['y']
                }
                # Check if the line intersects the caption line. If it does, determine which of the 'tables' is more table-y
                if helpers.lines_intersect(caption_line, area_line):
                    if page['areas'][pair[0]]['table_score'] > page['areas'][pair[1]]['table_score']:
                        caption_areas[caption] = [ area for area in caption_areas[caption] if area != pair[1]]
                    else:
                        page['areas'][pair[0]]['type'] = 'possible table'
                        caption_areas[caption] = [ area for area in caption_areas[caption] if area != pair[0]]

    # Extracts are bounding boxes that will be used to actually extract the tables
    extracts = []
    for caption, areas in caption_areas.items():
        area_of_interest_centroid_y_mean = np.mean([ helpers.centroid(page['areas'][area])['y'] for area in areas ])
        indicator_line_centroid_y = helpers.centroid(indicator_lines[caption])['y']

        areas_of_interest = [ page['areas'][area] for area in areas ]
        areas_of_interest.append(indicator_lines[caption])

        # The extract is designated by the min/max coordinates of the caption and cooresponding table(s)
        extracts.append({
            'name': indicator_lines[caption]['name'],
            'direction': 'below' if  area_of_interest_centroid_y_mean > indicator_line_centroid_y else 'above',
            'indicator_line': indicator_lines[caption],
            'x1': min([a['x1'] for a in areas_of_interest]) - padding,
            'y1': min([a['y1'] for a in areas_of_interest]) - padding,
            'x2': max([a['x2'] for a in areas_of_interest]) + padding,
            'y2': max([a['y2'] for a in areas_of_interest]) + padding
        })

    # Make sure each table was assigned a caption
    assigned_tables = []
    unassigned_tables = []
    for caption_idx, areas in caption_areas.items():
        assigned_tables = assigned_tables + areas

    all_tables = []
    for area_idx, area in enumerate(page['areas']):
        if area['type'] == 'table':
            all_tables.append(area_idx)

    if sorted(assigned_tables) == sorted(all_tables):
        print('all tables have a caption on page', page['page_no'])
    else:
        unassigned_tables = set(all_tables).difference(assigned_tables)
        print('Not all tables have a caption on page', page['page_no'])
        print('Not assigned - ', unassigned_tables)

    orphan_extracts = []
    for table in unassigned_tables:
        if page['areas'][table]['table_score'] > 5:
            orphan_extracts.append(helpers.expand_area(page['areas'][table], page['areas']))

    orphan_extracts = helpers.union_extracts(orphan_extracts)
    
    for extract in orphan_extracts:
        extract['name'] = 'Unknown'
        extract['direction'] = 'None'
    #    extracts.append(extract)


    # Find all areas that overlap in x space and are above and below the extracts
    extract_relations = {}
    for extract_idx, extract in enumerate(extracts):
        extract_relations[extract_idx] = find_above_and_below(extract)

    for extract_idx, extract in enumerate(extracts):
        expand_extraction(extract_idx, find_above_and_below(extract))

    # for extract_idx, props in extract_relations.iteritems():
    #     expand_extraction(extract_idx, props)

    for extract in orphan_extracts:
        # Find out if a good extraction already covers this area
        extract_poly = helpers.make_polygon(extract)
        covers = False
        for each in extracts:
            intersection = extract_poly.intersection(helpers.make_polygon(each))
            if intersection >= (extract_poly.area * 0.9):
                covers = True

        if not covers:
            extracts.append(extract)
            extract_relations[len(extracts) - 1] = find_above_and_below(extract)
            expand_extraction(len(extracts) - 1, extract_relations[len(extracts) - 1])

    return extracts
