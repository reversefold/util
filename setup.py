#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='reversefold.util',
    version='1.16.0',
    description='SSH, Proc, Multiproc, tail.py, log.py, stream.py, daemonize.py, etc.',
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
