#!/usr/bin/env python

import re
from pdfminer.psparser import PSLiteral
from pdfminer.glyphlist import glyphname2unicode
from pdfminer.latin_enc import ENCODING


STRIP_NAME = re.compile(r'[0-9]+')


##  name2unicode
##
def name2unicode(name):
    """Converts Adobe glyph names to Unicode numbers."""
    if name in glyphname2unicode:
        return glyphname2unicode[name]
    m = STRIP_NAME.search(name)
    if not m:
        raise KeyError(name)
    code_str = m.group(0)
    # max code_str should be '65536'
    if len(code_str) > 5:
        raise KeyError(name)
    code_point = int(code_str)
    # check if code point is a valid unicode
    if code_point > 0x1000:
        raise KeyError(name)
    return unichr(code_point)


##  EncodingDB
##
class EncodingDB(object):

    std2unicode = {}
    mac2unicode = {}
    win2unicode = {}
    pdf2unicode = {}
    for (name, std, mac, win, pdf) in ENCODING:
        c = name2unicode(name)
        if std:
            std2unicode[std] = c
        if mac:
            mac2unicode[mac] = c
        if win:
            win2unicode[win] = c
        if pdf:
            pdf2unicode[pdf] = c

    encodings = {
        'StandardEncoding': std2unicode,
        'MacRomanEncoding': mac2unicode,
        'WinAnsiEncoding': win2unicode,
        'PDFDocEncoding': pdf2unicode,
    }

    @classmethod
    def get_encoding(klass, name, diff=None):
        cid2unicode = klass.encodings.get(name, klass.std2unicode)
        if diff:
            cid2unicode = cid2unicode.copy()
            cid = 0
            for x in diff:
                if isinstance(x, int):
                    cid = x
                elif isinstance(x, PSLiteral):
                    try:
                        cid2unicode[cid] = name2unicode(x.name)
                    except KeyError:
                        pass
                    cid += 1
        return cid2unicode
