#!/usr/bin/env python
# At the top level, prevent logging output in absense of logging config.
import logging

from pdftotree._version import __version__
from pdftotree.core import parse

logging.getLogger(__name__).addHandler(logging.NullHandler())


__all__ = ["__version__", "parse"]
