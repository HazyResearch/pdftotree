"""For pip."""

from setuptools import setup

setup(
    name='pdftotree',
    version='0.1',
    description='Parse PDFs into HTML-like trees.',
    packages=['pdftotree'],
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
    url='https://github.com/hazyresearch/pdftotree',
    author='Hazy Research',
    license='MIT',
)
