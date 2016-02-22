#!/usr/bin/env python
"""Watches files for new lines and prints them prefixed with the filename.

Usage:
  tail.py -h | --help
  tail.py [--no-force-line-buffer] [--rate-limit=<count> --rate-period=<seconds>] <filename>...

Options:
  -h --help                             Help.
  --no-force-line-buffer                Don't force stdout to be line-buffered.
  -l <count> --rate-limit=<count>       A limit to the number of lines to be output within rate-period [Default: 100]
  -p <seconds> --rate-period=<seconds>  The period in seconds that the rate-limit is applied to. [Default: 1]

If more than `rate-limit` lines are received within `rate-period` seconds then a single line of "..." will be output and
all subsequent lines received within that period will be ignored.
"""
from __future__ import print_function
from datetime import datetime, timedelta
import os
from Queue import Empty, Queue
import sys
import threading
import time

from docopt import docopt

import reversefold.util.follow

# TODO: Add option to output partial lines after 1s of being buffered.
#       Keep partial line in buffer to output with more data later.
# TODO: Rate limiting. If more than N lines within 1s, drop remaining.
#       Support this overall and per-file?
# TODO: Handle file truncation
# TODO: Handle file disappearing
# TODO: Handle file appearing


RATE_LIMIT_SENTINEL = object()


def rate_limit_gen(gen, period, limit):
    start = datetime.now()
    # start at -1 since we pre-increment below and we actually want to allow up to `limit` values to be generated
    # within `period` before we yield RATE_LIMIT_SENTINEL.
    count = -1
    for value in gen:
        count += 1
        if datetime.now() - start < period:
            if count == limit:
                yield RATE_LIMIT_SENTINEL
                continue
            elif count > limit:
                continue
        else:
            start = datetime.now()
            count = 0
        yield value


class Master(object):
    def __init__(self, rate_limit, rate_period):
        self.queue = Queue()
        self.stop = threading.Event()
        self.rate_limit = rate_limit
        self.rate_period = timedelta(seconds=rate_period)

    def handle_line(self, line):
        self.queue.put(line)

    def _line_gen(self):
        while not self.stop.is_set():
            try:
                yield self.queue.get(block=False, timeout=0.1)
            except Empty:
                pass

    def run(self):
        gen = self._line_gen()
        if self.rate_limit is not None and self.rate_period is not None:
            gen = rate_limit_gen(gen, self.rate_period, self.rate_limit)
        for line in gen:
            if line is RATE_LIMIT_SENTINEL:
                line = '...'
            print(line)


try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    class TailHandler(FileSystemEventHandler):
        def __init__(self, filename, thefile, master, prefix=''):
            super(TailHandler, self).__init__()
            self.prefix = prefix
            self.filename = filename
            self.thefile = thefile
            self.line = ''
            self.master = master

        def on_modified(self, event):
            if event.src_path != self.filename:
                return
            while True:
                new_line = self.thefile.readline()
                if not new_line:
                    return
                self.line += new_line
                if self.line[-1] == '\n':
                    self.master.handle_line(self.prefix + self.line[:-1])
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


def tail(filename, master, prefix=''):
    if not os.path.exists(filename):
        sys.stderr.write('file %s does not exist\n' % (filename,))
        return

    if TailHandler is None:
        with reversefold.util.follow.Follower(filename) as follower:
            for line in follower:
                master.handle_line(prefix + line)
    else:
        with open(filename, 'r') as thefile:
            thefile.seek(0, 2)  # Go to the end of the file
            filename = os.path.abspath(filename)
            handler = TailHandler(filename, thefile, master, prefix)
            observer = Observer()
            observer.schedule(handler, path=os.path.dirname(filename))
            observer.start()
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
            observer.join()


def tail_multiple(filenames, rate_limit=None, rate_period=None):
    prefix_len = max(len(f) for f in filenames) + 3
    threads = []
    master = Master(rate_limit, rate_period)
    master_thread = threading.Thread(target=master.run)
    master_thread.start()
    for filename in filenames:
        prefix = '[%s] ' % (filename,)
        if len(prefix) < prefix_len:
            prefix += ' ' * (prefix_len - len(prefix))
        thread = threading.Thread(target=tail, args=[filename, master, prefix])
        thread.daemon = True
        thread.start()
        threads.append(thread)
    try:
        while threads:
            for thread in threads:
                thread.join(0.1)
                if not thread.is_alive():
                    threads.remove(thread)
        master.stop.set()
        master_thread.join()
    except KeyboardInterrupt:
        master.stop.set()
        sys.exit(0)


def main():
    args = docopt(__doc__)
    if not args['--no-force-line-buffer']:
        if hasattr(sys.stdout, 'fileno'):
            sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)
    rate_limit = int(args['--rate-limit']) if args['--rate-limit'] is not None else None
    rate_period = int(args['--rate-period']) if args['--rate-period'] is not None else None
    tail_multiple(args['<filename>'], rate_limit=rate_limit, rate_period=rate_period)


if __name__ == '__main__':
    main()
