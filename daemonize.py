#!/usr/bin/env python
"""Make a process which runs in the foreground run detached and capture its output.

This script will exit when the command exits.

Usage:
    daemonize.py [--pidfile=<pidfile>] [--stdout-log=<stdout-log>] [--stderr-log=<stderr-log>] -- <command>...

Options:
    -h --help                     Show this help text.
    -p --pidfile=<pidfile>        Path to a pidfile which will hold this script's pid (not the underlying process).
    -o --stdout-log=<stdout-log>  Path to log which will hold the stdout of the command [Default: log/stdout.log]
    -e --stderr-log=<stderr-log>  Path to log which will hold the stderr of the command [Default: log/stderr.log]
                                  The special value STDOUT will put this in the same log as the stdout output.
"""
import logging
import logging.handlers
import os
import subprocess
import threading

import daemon
import daemon.pidfile
from docopt import docopt

from reversefold.util import multiproc


class NoNewlineStream(object):
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        if data[-1:] == '\n':
            data = data[:-1]
        return self.stream.write(data)

    def close(self):
        return self.stream.close()

    def flush(self):
        return self.stream.flush()

    def fileno(self):
        return self.stream.fileno()


class WatchedFileHandlerVerbatim(logging.handlers.WatchedFileHandler):
    def __init__(self, *a, **k):
        super(WatchedFileHandlerVerbatim, self).__init__(*a, **k)
        self.setFormatter(logging.Formatter('%(message)s'))

    # overriding to patch the stream to not accept trailing newlines
    def _open(self):
        return NoNewlineStream(super(WatchedFileHandlerVerbatim, self)._open())


def get_logger(name, filename):
    handler = WatchedFileHandlerVerbatim(filename)
    handler.setLevel(logging.INFO)
    logger = logging.getLogger('daemonize.%s' % (name,))
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger, handler


def main():
    args = docopt(__doc__)
    out_logger, out_handler = get_logger('stdout', args['--stdout-log'])
    preserve = [out_handler.stream]
    if args['--stderr-log'] != 'STDOUT':
        err_logger, err_handler = get_logger('stderr', args['--stderr-log'])
        preserve.append(err_handler.stream)

    with daemon.DaemonContext(
        pidfile=None if args['--pidfile'] is None else daemon.pidfile.TimeoutPIDLockFile(args['--pidfile']),
        working_directory=os.getcwd(),
        files_preserve=preserve,
    ):
        proc = subprocess.Popen(
            args['<command>'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT if args['--stderr-log'] == 'STDOUT' else subprocess.PIPE)
        proc.stdin.close()
        thread = threading.Thread(target=multiproc.Pipe(proc.stdout, out_logger.info).flow)
        thread.start()
        threads = [thread]
        if args['--stderr-log'] != 'STDOUT':
            thread = threading.Thread(target=multiproc.Pipe(proc.stderr, err_logger.info).flow)
            thread.start()
            threads.append(thread)
        proc.wait()
        for thread in threads:
            thread.join()


if __name__ == '__main__':
    main()
