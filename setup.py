#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='reversefold.util',
    version='1.1.0',
    description='SSH, Multiproc, tail.py, log.py, stream.py',
    author='Justin Patrin',
    author_email='papercrane@reversefold.com',
    url='https://github.com/reversefold/util',
    packages=find_packages(),
    scripts=['tail.py', 'log.py', 'stream.py'],
    license='MIT',
    install_requires=[
        'colorama',
        'docopt',
        'watchdog',
    ],
)
