#!/usr/bin/env python
'''A simple script which takes stdin and writes it to a logfile using the WatchedFileHandler so that
stdout/err of programs can be captured while also allowing log rotation of these files.

Usage:
  log.py -h | --help
  log.py <filename> [--format=<format>] [--datefmt=<damefmt>] [--tee]

Options:
  -h --help              Help.
  -f --format=<format>   Logging format to use. [Default: %(message)s]
  -d --datefmt=<damefmt> Date format to use. [Default: %Y-%m-%d %H:%M:%S].
  -t --tee               Write input to stdout as well as the file.

'datefmt' Won't take effect unless 'format' is given with a date identifier (like %(asctime)s)
 in it.
'''

from docopt import docopt
import logging
import logging.handlers
import sys


def main():
    '''Main'''
    args = docopt(__doc__)
    tee = args['--tee']
    formatter = logging.Formatter(
        args.get('--format', '%(message)s'),
        datefmt=args.get('--datefmt', '%Y-%m-%d %H:%M:%S'))
    handler = logging.handlers.WatchedFileHandler(args['<filename>'], 'a', 'utf-8')
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    log = logging.getLogger(__name__)
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    if tee:
        streamhandler = logging.StreamHandler()
        streamhandler.setLevel(logging.INFO)
        streamhandler.setFormatter(logging.Formatter('%(message)s'))
        log.addHandler(streamhandler)
    for line in iter(sys.stdin.readline, ''):
        log.info(line.rstrip())


if __name__ == '__main__':
    main()
