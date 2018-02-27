"""For pip."""
from setuptools import setup, find_packages

exec(open('pdftotree/_version.py').read())
setup(
    name='pdftotree',
    version=__version__,
    description='Parse PDFs into HTML-like trees.',
    packages=find_packages(),
    install_requires=[
        'IPython',
        'beautifulsoup4',
        'bintrees',
        'future',
        'lxml',
        'numpy',
        'pandas',
        'pdfminer.six',
        'pillow',
        'scipy',
        'six',
        'sklearn',
        'spacy',
        'tabula-py',
        'wand',
    ],
    url='https://github.com/HazyResearch/pdftotree',
    scripts=['bin/extract_tree'],
    author='Hazy Research',
    license='MIT',
)
