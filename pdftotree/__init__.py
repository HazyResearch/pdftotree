#!/usr/bin/env python
from pdftotree._version import __version__

# At the top level, prevent logging output in absense of logging config.
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())

from pdftotree.core import parse
