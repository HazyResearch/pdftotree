TOLERANCE = 5


def reorder_lines(lines, tol=TOLERANCE):
    """
    Changes the line coordinates to be given as (top, left, bottom, right)
    :param lines: list of lines coordinates
    :return: reordered list of lines coordinates
    """
    reordered_lines = []
    for line in lines:
        # we divide by tol and multiply by tol to truncate numbers, stairs function
        reordered_lines += [(int(round(line.y0 / tol) * tol), int(round(line.x0 / tol) * tol),
                             int(round(line.y1 / tol) * tol), int(round(line.x1 / tol) * tol))]
    return reordered_lines


def merge_vertical_lines(lines, tol=TOLERANCE):
    """
    This function merges lines segment when they are vertically aligned
    :param lines: list of lines coordinates (top, left, bottom, right)
    :return: list of merged lines coordinates
    """
    if len(lines) == 0:
        return []
    merged_lines = [lines[0]]
    for line in lines[1:]:
        last_line = merged_lines[-1]
        if line[1] == last_line[1]:  # lines are vertically aligned
            if line[0] <= last_line[2] + tol:  # lines intersect
                y0, x0, y1, x1 = merged_lines[-1]
                merged_lines[-1] = (y0, x0, line[2], x1)
            else:
                merged_lines.append(line)  # lines are vertically aligned but do not intersect
        else:
            merged_lines.append(line)
    return merged_lines


def merge_horizontal_lines(lines, tol=TOLERANCE):
    """
    This function merges horizontal lines when they are horizontally aligned
    :param lines: list of lines coordinates (top, left, bottom, right)
    :return: list of merged lines coordinates
    """
    if len(lines) == 0:
        return []
    merged_lines = [lines[0]]
    for line in lines[1:]:
        last_line = merged_lines[-1]
        if line[0] == last_line[0]:  # lines are horizontally aligned
            if line[1] <= last_line[3] + tol:  # lines intersect
                y0, x0, y1, x1 = merged_lines[-1]
                merged_lines[-1] = (y0, x0, y1, line[3])
            else:
                merged_lines.append(line)  # lines are horizontally aligned but do not intersect
        else:
            merged_lines.append(line)
    return merged_lines


def get_vertical_and_horizontal(lines):
    """
    Extracts vertical and horizontal lines lists
    :param lines: list of lines coordinates
    :return: vertical_lines, horitontal_lines (2 lists of coordinates)
    """
    # TODO: add some angle tolerance when lines are not perfectly aligned (eg: scanned pdf)
    vertical_lines = sorted([e for e in lines if e[1] == e[3]], key=lambda tup: (tup[1], tup[0]))
    horitontal_lines = sorted([e for e in lines if e[0] == e[2]])
    if len(vertical_lines) > 0:
        vertical_lines = merge_vertical_lines(vertical_lines)
    if len(horitontal_lines) > 0:
        horitontal_lines = merge_horizontal_lines(horitontal_lines)
    return vertical_lines, horitontal_lines


# def extend_vertical_lines_(vertical_lines, horizontal_lines):
#     j = 0
#     i = 0
#     new_vertical_lines = []
#     while i < len(horizontal_lines) and j < len(vertical_lines):
#         if int(horizontal_lines[i][0]) == int(vertical_lines[j][0]):
#             if int(vertical_lines[j][1]) > int(horizontal_lines[i][1]) and int(vertical_lines[j][1]) < int(
#                     horizontal_lines[i][3]):
#                 v = vertical_lines[j]
#                 h = horizontal_lines[i]
#                 new_vertical_lines.append((h[0], h[1], v[2], h[1]))
#                 new_vertical_lines.append((h[0], h[3], v[2], h[3]))
#                 j += 1
#                 i += 1
#             else:
#                 i += 1
#         elif int(horizontal_lines[i][0]) < int(vertical_lines[j][0]):
#             i += 1
#         else:
#             j += 1
#     return new_vertical_lines


def extend_vertical_lines(horizontal_lines, tol=TOLERANCE):
    widths = {}
    for i, line in enumerate(horizontal_lines):
        try:
            widths[(line[1], line[3])] += [i]
        except KeyError:
            widths[(line[1], line[3])] = [i]
    new_vertical_lines = []
    for (x0, x1) in widths.keys():
        if len(widths[(x0, x1)]) > 1:
            lines = [horizontal_lines[i] for i in widths[(x0, x1)]]
            y0 = min([h[0] for h in lines])
            y1 = max([h[2] for h in lines])
            new_vertical_lines += [(y0, x0, y1, x0), (y0, x1, y1, x1)]
    return new_vertical_lines


def extend_horizontal_lines(vertical_lines, tol=TOLERANCE):
    heights = {}
    for i, line in enumerate(vertical_lines):
        try:
            heights[(line[0], line[2])] += [i]
        except KeyError:
            heights[(line[0], line[2])] = [i]
    new_horizontal_lines = []
    for (y0, y1) in heights.keys():
        if len(heights[(y0, y1)]) > 1:
            lines = [vertical_lines[i] for i in heights[(y0, y1)]]
            x0 = min([h[1] for h in lines])
            x1 = max([h[3] for h in lines])
            new_horizontal_lines += [(y0, x0, y0, x1), (y1, x0, y1, x1)]
    return new_horizontal_lines
