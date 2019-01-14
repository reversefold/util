#!/usr/bin/env python
import os

from setuptools import setup, find_packages


VERSION = '1.19.1'

README_PATH = os.path.join(os.path.dirname(__file__), 'README.md')

DESCRIPTION = 'SSH, Proc, Multiproc, tail.py, log.py, stream.py, daemonize.py, etc.'

if os.path.exists(README_PATH):
    with open(README_PATH, 'r') as f:
        LONG_DESCRIPTION = f.read()
else:
    LONG_DESCRIPTION = DESCRIPTION

setup(
    name='reversefold.util',
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author='Justin Patrin',
    author_email='papercrane@reversefold.com',
    url='https://github.com/reversefold/util',
    packages=find_packages(),
    scripts=[
        'scripts/tail.py',
        'scripts/log.py',
        'scripts/stream.py',
        'scripts/sort_json.py',
    ],
    entry_points={
        'console_scripts': [
            'daemonize.py = reversefold.util.daemonize:main'
        ],
    },
    license='MIT',
    install_requires=[
        'colorama',
        'docopt',
        'lockfile',
        'python-daemon==2.1.1',
        'psutil',
        'watchdog',
    ],
)
