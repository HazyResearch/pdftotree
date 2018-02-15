from bs4 import BeautifulSoup
from plot import plot
import math
import re
import numpy as np
import itertools
import helpers

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


def areaSummary(area):
    summary = {}

    # Bounding box (x1, y1, x2, y2)
    summary.update(helpers.extractbbox(area.get('title')))

    # Number of lines
    summary['lines'] = len(area.find_all('span', 'ocr_line'))

    # Number of words
    summary['words'] = len(filter(None, area.getText().strip().replace('\n', ' ').replace('  ', ' ').split(' ')))

    # Area
    summary['area'] = (summary['x2'] - summary['x1']) * (summary['y2'] - summary['y1'])

    # Get spacing of words
    summary['x_gaps'] = np.zeros(summary['x2'] - summary['x1'], dtype=np.int)

    # Count whitespace gaps
    summary['gaps'] = helpers.get_gaps(summary['x_gaps'])

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

    # Get the mean of the differences of the word distances (all the same == 0, difference increases away from 0)
    summary['word_separation_index'] = 0 if summary['words'] == 0 else helpers.meanOfDifferences(summary['word_distances'])

    # Quantify the variation in the height of words in this area
    summary['word_height_index'] = 0 if summary['words'] == 0 else helpers.meanOfDifferences(summary['word_heights'])

    # Get the average word height of this area
    summary['word_height_avg'] = 0 if summary['words'] == 0 else np.nanmean(summary['word_heights'])

    # Get word/area ratio
    summary['word_area_index'] = 0 if summary['words'] == 0 else np.sum(summary['word_areas']) / float(summary['area'])

    return summary

# Summarize the area stats of a given document
def summarizeDocument(area_stats):
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
        'word_height_avg_std': np.nanstd([area['word_height_avg'] for area in area_stats if area['words'] > 0 and area['lines'] > 1])
    }


def tess():
    # Open the file with Tesseract output
    with open('test_files/two_tables_equations.html.hocr') as hocr:
        text = hocr.read()

    soup = BeautifulSoup(text, 'html.parser')
    # Extract the page
    page = helpers.extractbbox(soup.find_all('div', 'ocr_page')[0].get('title'))
    # Get all "areas"
    areas = soup.find_all('div', 'ocr_carea')

    # Find the captions/titles for charts, figures, maps, tables
    indicator_lines = []

    for line in soup.find_all('span', 'ocr_line'):
        # Remove nonsense
        clean_line = line.getText().strip().replace('\n', ' ').replace('  ', ' ').lower()
        # Find all lines that contain only a target word plus a number
        dedicated_line_matches = re.match('(table|figure|fig|map)(\.)? \d+(\.)?', clean_line, flags=re.IGNORECASE)
        # Find all the lines that start with one of the target words and a number
        caption_matches = re.match('(table|figure|fig|map)(\.)? \d+(\.)', clean_line, flags=re.IGNORECASE)
        # dedicated line (ex: Table 1)
        if dedicated_line_matches and dedicated_line_matches.group(0) == clean_line:
            print dedicated_line_matches.group(0)
            indicator_lines.append(helpers.extractbbox(line.get('title')))
        # Other
        elif caption_matches:
            print caption_matches.group(0)
            bbox = helpers.extractbbox(line.get('title'))
            bbox['name'] = caption_matches.group(0)
            indicator_lines.append(helpers.extractbbox(line.get('title')))


    area_stats = [ areaSummary(area) for area in areas ]
    doc_stats = summarizeDocument(area_stats)

    print 'Document Summary:'
    print '    Word separation avg (mean): %s' % ('%.2f' % doc_stats['word_separation_mean'], )
    print '    Word separation avg (median): %s' % ('%.2f' % doc_stats['word_separation_median'], )
    print '    Word separation avg (std): %s' % ('%.2f' % doc_stats['word_separation_std'], )

    print '    Word separation index (mean): %s' % ('%.2f' % doc_stats['word_separation_index_mean'], )
    print '    Word separtion index (median): %s' % ('%.2f' % doc_stats['word_separation_index_median'], )
    print '    Word separtion index (std): %s' % ('%.2f' % doc_stats['word_separation_index_std'], )
    print '    Word height index (mean): %s' % ('%.2f' % doc_stats['word_height_index_mean'], )
    print '    Word height index (median): %s' % ('%.2f' % doc_stats['word_height_index_median'], )
    print '    Word height index (std): %s' % ('%.2f' % doc_stats['word_height_index_std'], )
    print '    Word area index (mean): %s%%' % (int(doc_stats['word_area_index_mean'] * 100), )
    print '    Word area index (median): %s%%' % (int(doc_stats['word_area_index_median'] * 100), )
    print '    Word area index (std): %s%%' % (int(doc_stats['word_area_index_std'] * 100), )
    print '    Word height avg (mean): %s' % ('%.2f' % doc_stats['word_height_avg'], )
    print '    Word height avg (median): %s' % ('%.2f' % doc_stats['word_height_avg_median'], )
    print '    Word height avg (std): %s' % ('%.2f' % doc_stats['word_height_avg_std'], )

    '''
    table definition:
        word separation index > document median + 1 std
        word area index < document median - 1 std
        never one line
    '''

    '''
    text block:
        word separation index < document median + 1 std
        word area index === document median +/- (1 std / 2)
        never one line
    '''
    for area in area_stats:
        # The table_score keeps track of how "table-y" an area is, i.e. how many characteristics it has consistent with tables
        area['table_score'] = 0
        # Remove gaps smaller than the median gap between words
        area['gaps'] = [gap for gap in area['gaps'] if gap > doc_stats['word_separation_median']]

        # Add to the table score for each gap (each gap adds one point)
        for gap in area['gaps']:
            area['table_score'] += 1

        # Separator lines are only one line, have no words or other attributes
        if area['lines'] == 1 and area['words'] == 0 and area['word_separation_index'] == 0 and area['word_height_index'] == 0 and area['word_height_avg'] == 0:
            area['type'] = 'line'

        elif (area['word_separation_index'] >= (doc_stats['word_separation_index_median'] + doc_stats['word_separation_index_std'])) and (area['word_area_index'] <= (doc_stats['word_area_index_median'] - doc_stats['word_area_index_std'])) and area['lines'] > 1:
            area['type'] = 'table'


        elif (area['word_separation_index'] < (doc_stats['word_separation_index_median'] + doc_stats['word_separation_index_std'])) and (area['word_area_index'] > (doc_stats['word_area_index_median'] - (doc_stats['word_area_index_std']/float(2))) and area['word_area_index'] < (doc_stats['word_area_index_median'] + (doc_stats['word_area_index_std']/float(2)))) and area['lines'] > 1:
            area['type'] = 'text block'

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

    # Find lines - can be line breaks between paragraphs or divider lines in tables
    lines = [area for area in area_stats if area['type'] == 'line']

    # If a line intersects an area, classify that area as a table
    for area in area_stats:
        if area['type'] != 'line':
            for line in lines:
                if helpers.rectangles_intersect(area, line):
                    area['type'] = 'table'
                    area['table_score'] += 1

    # Assign a caption to each table, and keep track of which captions are assigned to tables. caption_idx: [area_idx, area_idx, ...]
    caption_areas = {}
    for area_idx, area in enumerate(area_stats):
        if area['type'] == 'table':
            distances = [helpers.distance(area, line) for line in indicator_lines]

            nearest_caption = distances.index(min(distances))
            area['caption'] = nearest_caption
            try:
                caption_areas[nearest_caption].append(area_idx)
            except:
                caption_areas[nearest_caption] = [area_idx]

    # Sanity check the caption-area assignments
    for caption, areas in caption_areas.iteritems():
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
                'x1': page['x1'],
                'y1': caption_line_y,
                'x2': page['x2'],
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
                a = helpers.centroid(area_stats[pair[0]])
                b = helpers.centroid(area_stats[pair[1]])
                area_line = {
                    'x1': a['x'],
                    'y1': a['y'],
                    'x2': b['x'],
                    'y2': b['y']
                }
                # Check if the line intersects the caption line. If it does, determine which of the 'tables' is more table-y
                if lines_intersect(caption_line, area_line):
                    if area_stats[pair[0]]['table_score'] > area_stats[pair[1]]['table_score']:
                        area_stats[pair[1]]['type'] = 'not a table'
                        caption_areas[caption] = [ area for area in areas if area != pair[1]]
                    else:
                        area_stats[pair[0]]['type'] = 'not a table'
                        caption_areas[caption] = [ area for area in areas if area != pair[0]]


    extracts = []
    for caption, areas in caption_areas.iteritems():
        areas_of_interest = [area_stats[area] for area in areas]
        areas_of_interest.append(indicator_lines[caption])

        extracts.append({
            'x1': min([a['x1'] for a in areas_of_interest]) - padding,
            'y1': min([a['y1'] for a in areas_of_interest]) - padding,
            'x2': max([a['x2'] for a in areas_of_interest]) + padding,
            'y2': max([a['y2'] for a in areas_of_interest]) + padding
        })

    # Find all areas that overlap in x space and are above and below the extracts
    extract_relations = {}
    for extract_idx, extract in enumerate(extracts):
        extract_relations[extract_idx] = {
            'above': [],
            'below': []
        }

        for area_idx, area in enumerate(area_stats):
            # Check if they overlap in x space
            if area['x1'] <= extract['x2'] and extract['x1'] <= area['x2']:
                # Check how * much * they overlap in
                percent_overlap = (abs(area['x2'] - extract['x1'])) / float(extract['x2'] - extract['x1'])
                if percent_overlap >= 0.9:
                    # Check if this area is above or below the extract area
                    area_centroid = helpers.centroid(area)
                    extract_centroid = helpers.centroid(extract)

                    if area_centroid['y'] <= extract_centroid['y']:
                        # Work backwards so that when we iterate we start at the area closest to the extract
                        extract_relations[extract_idx]['above'].insert(0, area_idx)
                    else:
                        extract_relations[extract_idx]['below'].append(area_idx)


    for extract_idx, props in extract_relations.iteritems():
        for area_idx in extract_relations[extract_idx]['above']:
            if area_stats[area_idx]['type'] != 'text block' and area_stats[area_idx]['type'] != 'not a table' and area_stats[area_idx]['type'] != 'other' :
                # [Grow] the extract area
                extracts[extract_idx].update(helpers.enlarge_extract(extracts[extract_idx], area_stats[area_idx]))
            else:
                break

        for area_idx in extract_relations[extract_idx]['below']:
            if area_stats[area_idx]['type'] != 'text block' and area_stats[area_idx]['type'] != 'not a table' and area_stats[area_idx]['type'] != 'other' :
                # [Grow] the extract area
                print extract_idx, area_stats[area_idx]['type']
                extracts[extract_idx].update(helpers.enlarge_extract(extracts[extract_idx], area_stats[area_idx]))
            else:
                break

    plot(soup, extracts)


    # for idx, area in enumerate(area_stats):
    #     print 'Area %s -- %s (%s)' % (idx, area['type'], area['table_score'])
    #     print '    Lines: %s' % (area['lines'], )
    #     print '    Words: %s' % (area['words'], )
    #     print '    Area: %s' % (area['area'], )
    #     print '    Word separation index: %s' % ('%.2f' % area['word_separation_index'], )
    #     print '    Word height index: %s' % ('%.2f' % area['word_height_index'], )
    #     print '    Word height avg: %s' % ('%.2f' % area['word_height_avg'], )
    #     print '    Area covered by words: %s%%' % (int(area['word_area_index'] * 100), )
    #     print '    Average word height: %s' % ('%.2f' % area['word_height_avg'])
    #     print '    Gaps: %s' % (area['gaps'])


tess()
