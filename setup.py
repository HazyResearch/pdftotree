"""For pip."""

from setuptools import setup, find_packages

setup(
    name='pdftotree',
    version='0.1.1',
    description='Parse PDFs into HTML-like trees.',
    packages=find_packages(),
    install_requires=[
        'numpy',
        'wand',
        'pillow',
        'bintrees',
        'beautifulsoup4',
        'lxml',
        'sklearn',
        'pandas',
        'tabula-py',
        'IPython',
        'scipy',
        'six',
    ],
    url='https://github.com/HazyResearch/pdftotree',
    scripts=['bin/extract_tree'],
    author='Hazy Research',
    license='MIT',
)
