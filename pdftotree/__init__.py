#!/usr/bin/env python

# At the top level, prevent logging output in absense of logging config.
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())

from pdftotree.core import parse
