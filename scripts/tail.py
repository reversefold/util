#!/usr/bin/env python
"""Watches files for new lines and prints them prefixed with the filename.

Usage:
  tail.py -h | --help
  tail.py <filename>...

Options:
  -h --help              Help.
"""

from docopt import docopt
import os
import sys
import threading
import time

import reversefold.util.follow

# TODO: Handle file truncation
# TODO: Handle file disappearing
# TODO: Handle file appearing

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    class TailHandler(FileSystemEventHandler):
        def __init__(self, filename, thefile, prefix=''):
            super(TailHandler, self).__init__()
            self.prefix = prefix
            self.filename = filename
            self.thefile = thefile
            self.line = ''

        def on_modified(self, event):
            if event.src_path != self.filename:
                return
            while True:
                new_line = self.thefile.readline()
                if not new_line:
                    return
                self.line += new_line
                if self.line[-1] == '\n':
                    print self.prefix + self.line[:-1]
                    self.line = ''

except ImportError:
    TailHandler = None


def follow(thefile):
    thefile.seek(0, 2)  # Go to the end of the file
    line = ''
    while True:
        new_line = thefile.readline()
        if not new_line:
            time.sleep(0.1)  # Sleep briefly
            continue
        line += new_line
        if line[-1] == '\n':
            yield line[:-1]
            line = ''


def tail(filename, prefix=''):
    if not os.path.exists(filename):
        print >> sys.stderr, 'file %s does not exist' % (filename,)
        return

    if TailHandler is None:
        with reversefold.util.follow.Follower(filename) as f:
            for line in f:
                print prefix + line

    with open(filename, 'r') as thefile:
        thefile.seek(0, 2)  # Go to the end of the file
        filename = os.path.abspath(filename)
        handler = TailHandler(filename, thefile, prefix)
        observer = Observer()
        observer.schedule(handler, path=os.path.dirname(filename))
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


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


if __name__ == '__main__':
    args = docopt(__doc__)
    tail_multiple(*args['<filename>'])
