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
        'matplotlib',
        'numpy',
        'pandas',
        'pdfminer.six',
        'pillow',
        'scipy',
        'shapely',
        'six',
        'sklearn',
        'tabula-py',
        'wand',
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    url='https://github.com/HazyResearch/pdftotree',
    scripts=[
        'bin/extract_tree',
        'bin/extract_tables',
    ],
    author='Hazy Research',
    license='MIT',
)
