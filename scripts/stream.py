#!/usr/bin/env python
"""Streams

Usage:
    stream.py -h | --help
    stream.py [--tail] [--byte [--bufsize=<bufsize>]] <filename>

Options:
    -h --help           Help.
    --tail              Only stream lines from the end of the file.
    --byte              Don't buffer, output new bytes as soon as they are
                        read.
    --bufsize=<bufsize> The number of bytes that will be attempted to be read
                        at a time. [Default: 1024]
"""
from __future__ import print_function
import os
import sys

from docopt import docopt

from reversefold.util import follow


def main():
    args = docopt(__doc__)
    if args['--byte']:
        if hasattr(sys.stdout, 'fileno'):
            # Force stdout to be un-buffered
            sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

        with follow.Follower(
            args['<filename>'], args['--tail'], int(args['--bufsize'])
        ) as follower:
            try:
                for data in follower:
                    sys.stdout.write(data)
                    sys.stdout.flush()
            except KeyboardInterrupt:
                follower.finish = True
                for data in follower:
                    sys.stdout.write(data)
                sys.stdout.flush()
                raise

    else:
        with follow.LineFollower(
            args['<filename>'], args['--tail']
        ) as follower:
            try:
                for data in follower:
                    print(data)
            except KeyboardInterrupt:
                follower.finish = True
                for data in follower:
                    print(data)
                raise


if __name__ == '__main__':
    main()
