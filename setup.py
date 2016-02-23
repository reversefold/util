#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='reversefold.util',
    version='1.13.3',
    description='SSH, Multiproc, tail.py, log.py, stream.py, daemonize.py',
    author='Justin Patrin',
    author_email='papercrane@reversefold.com',
    url='https://github.com/reversefold/util',
    packages=find_packages(),
    scripts=['scripts/tail.py', 'scripts/log.py', 'scripts/stream.py', 'scripts/daemonize.py'],
    license='MIT',
    install_requires=[
        'colorama',
        'docopt',
        'lockfile',
        'python-daemon==2.0.6',
        'watchdog',
    ],
)
