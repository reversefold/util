#!/usr/bin/env python
"""Streams

Usage:
    stream.py -h | --help
    stream.py [--tail] <filename>

Options:
    -h --help   Help.
    --tail      Only stream lines from the end of the file.
"""
from docopt import docopt

from reversefold.util import follow


def main():
    args = docopt(__doc__)
    with follow.Follower(args['<filename>'], args['--tail']) as follower:
        try:
            for data in follower:
                print data
        except KeyboardInterrupt:
            follower.finish = True
        for data in follower:
            print data


if __name__ == '__main__':
    main()
