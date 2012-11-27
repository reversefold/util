#!/usr/bin/env python
'''Watches files for new lines and prints them prefixed with the filename.

Usage:
  tail.py -h | --help
  tail.py <filename>...

Options:
  -h --help              Help.
'''

from docopt import docopt
import os
import sys
import threading
import time


def follow(thefile):
    thefile.seek(0, 2)      # Go to the end of the file
    while True:
        line = thefile.readline()
        if not line:
            time.sleep(0.1)    # Sleep briefly
            continue
        yield line[:-1]


def tail_multiple(*filenames):
    prefix_len = max(len(f) for f in filenames) + 3
    threads = []
    for filename in filenames:
        prefix = '[%s] ' % (filename,)
        if len(prefix) < prefix_len:
            prefix += ' ' * (prefix_len - len(prefix))
        thread = threading.Thread(target=tail, args=[filename, prefix])
        thread.daemon = True
        thread.start()
        threads.append(thread)
    try:
        while threads:
            for thread in threads:
                thread.join(0.1)
                if not thread.is_alive():
                    threads.remove(thread)
    except KeyboardInterrupt:
        sys.exit(0)


def tail(filename, prefix=''):
    if not os.path.exists(filename):
        print >> sys.stderr, 'file %s does not exist' % (filename,)
        return
    thefile = open(filename, 'r')
    for line in follow(thefile):
        print prefix + line


if __name__ == '__main__':
    args = docopt(__doc__)
    tail_multiple(*args['<filename>'])
