"""For pip."""

from setuptools import setup, find_packages

setup(
    name='pdftotree',
    version='0.1.3',
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
        'tabula-py',
        'wand',
    ],
    url='https://github.com/HazyResearch/pdftotree',
    scripts=['bin/extract_tree'],
    author='Hazy Research',
    license='MIT',
)
