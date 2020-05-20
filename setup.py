import os
from setuptools import setup, find_packages

__version__ = '0.0.2'

setup(
    name='gmap_retrieval',
    version=__version__,
    author='Takao Shimizu',
    author_email='tshimizu.midd@gmail.com',
    url='https://github.com/TShim/gmap_retrieval',
    description='Package to retrieve geographical data using Google Maps API based on a list of locations',
    long_description=open('README.md').read(),
    license='MIT',
    packages=find_packages(exclude=('tests')),
    install_requires=['numpy', 'pandas'],
)
