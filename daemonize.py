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
from datetime import datetime, timedelta
import logging
import logging.handlers
import os
import subprocess
import sys
import threading
import time

import daemon
from daemon import runner
from docopt import docopt
from lockfile import pidlockfile, LockError

from reversefold.util import multiproc


class TrimTrailingNewlinesStream(object):
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

    # overriding to patch the stream to get rid of the trailing newlines added by the logging system
    def _open(self):
        return TrimTrailingNewlinesStream(super(WatchedFileHandlerVerbatim, self)._open())


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
    if args['--stderr-log'] == 'STDOUT':
        err_logger = args['--stderr-log']
    else:
        err_logger, err_handler = get_logger('stderr', args['--stderr-log'])
        preserve.append(err_handler.stream)

    if args['--pidfile'] is None:
        pidfile = None
    else:
        acquire_pidfile_path = args['--pidfile'] + '.acquirelock'
        pidfile = pidlockfile.PIDLockFile(args['--pidfile'], timeout=0)
        # If the first pidfile is stale, use another pid lockfile to make sure we're not
        # racing someone else. This lockfile should be far less likely to be stale since
        # it is only kept during this check and breaking the stale lock.
        try:
            with pidlockfile.PIDLockFile(acquire_pidfile_path, timeout=0):
                if pidfile.is_locked():
                    if runner.is_pidfile_stale(pidfile):
                        print('Stale lockfile detected, breaking the stale lock %s' % (args['--pidfile'],))
                        pidfile.break_lock()
                    else:
                        print('Another process has already acquired the pidfile %s, daemon not started' % (
                            args['--pidfile'],))
                        sys.exit(1)
        except LockError:
            print('Got an exception while attempting to check for a stale main pidfile.')
            print('There is likely to be a stale acquire pidfile at %s' % (acquire_pidfile_path,))
            raise

    # There is a small chance of a race condition here which can cause multiple processes to try to acquire
    # the pidfile. One will succeed and the others will fail but daemonize.py will exit with an exitcode of 0
    # as the condition was not detected above. This could be fixed if we could start the DaemonContext within
    # the acquire pidfile's lock context, but since DaemonContext calls os._exit the acquire pidfile will never
    # be unlocked. If a solution can be found to keep the lock on the acquire pidfile until the main pidfile is
    # acquired, then release the acquire pidfile, then the race condition would not exist.
    with daemon.DaemonContext(
        pidfile=pidfile,
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
        while proc.returncode is None:
            time.sleep(0.1)
            proc.poll()
        start = datetime.now()
        wait_time = timedelta(seconds=5)
        while threads and datetime.now() - start < wait_time:
            alive_threads = []
            for thread in threads:
                thread.join(timeout=0.1)
                if thread.is_alive():
                    alive_threads.append(thread)
            threads = alive_threads
        sys.exit()


if __name__ == '__main__':
    main()
