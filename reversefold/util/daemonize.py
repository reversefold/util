#!/usr/bin/env python
"""Make a process which runs in the foreground run detached and capture its output.

This script will exit when the command exits.

Usage:
    %(script)s [--stdout-log=<stdout-log>] [--stderr-log=<stderr-log>]
               [--pidfile=<pidfile>] [--app-pidfile=<pidfile>]
               [--log-format=<fmt> [--date-format=<fmt>]]
               [(--log-handler=watched | --log-handler=timed [--when=<w>] [--interval=<i>] [--backup-count=<b>])]
               [--debug]
               -- <command>...

Options:
    -h --help                     Show this help text.
    -p --pidfile=<pidfile>        Path to a pidfile which will hold this script's pid (not the underlying process).
    -d --app-pidfile=<pidfile>    Path to a pidfile which will hold the pid of <command>.
    -o --stdout-log=<stdout-log>  Path to log which will hold the stdout of the command [Default: log/stdout.log]
    -e --stderr-log=<stderr-log>  Path to log which will hold the stderr of the command [Default: log/stderr.log]
                                  The special value STDOUT will put this in the same log as the stdout output.
    --log-format=<fmt>            The format that will be applied to the stdout and stderr logs. [Default: %%(message)s]
                                  For example, if you wanted to prepend a timestamp to each line you could use:
                                  %%(asctime)s %%(message)s
                                  For a full reference see the Python documentation:
                                  https://docs.python.org/2/library/logging.html#logrecord-attributes
    --date-format=<fmt>           The format to apply to the logging timestamp [Default: %%Y-%%m-%%d %%H:%%M:%%S]
                                  Note that this option won't take effect unless --log-format is given with a date
                                  identifier (like %%(asctime)s) in it.
                                  For a full reference see the Python documentation:
                                  https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior
    --log-handler=<type>          Set the log handler type. [Default: watched]
                                  Options:
                                    "watched": WatchedFileHandler. If the log is rotated via an outside process
                                      such as logrotate this handler will detect that and create a new file with the
                                      original name.
                                    "timed": TimedRotatingFileHandler. Will automatically rotate the log file at time
                                      intervals.
    --when=<w>                    Sets the when parameter of the TimedRotatingFileHandler. [Default: h]
                                  Valid options:
                                    s (second)
                                    m (minute)
                                    h (hour)
                                    d (day)
                                    w0-w6 (weekday, 0=Monday)
                                    midnight
    --interval=<i>                Sets the interval parameter of the TimedRotatingFileHandler. [Default: 1]
    --backup-count=<b>            Sets the backupCount parameter of the TimedRotatingFileHandler. [Default: 24]
    --debug                       More output.
"""
from __future__ import print_function
from datetime import datetime, timedelta
import functools
import io
import logging
import logging.handlers
import os
import subprocess
import sys
import threading
import time

import daemon
from docopt import docopt
from fasteners import process_lock
import psutil


from reversefold.util import multiproc


LOG = logging.getLogger(__name__)


class Error(Exception):
    pass


def get_logger(
    name, filename, log_format, date_format, log_handler, when, interval, backup_count
):

    if log_handler == "watched":
        handler = logging.handlers.WatchedFileHandler(filename)
    elif log_handler == "timed":
        handler = logging.handlers.TimedRotatingFileHandler(
            filename, when=when, interval=interval, backupCount=backup_count
        )
    formatter = logging.Formatter(log_format, datefmt=date_format)
    handler.setFormatter(formatter)

    handler.setLevel(logging.INFO)
    logger = logging.getLogger("daemonize.%s" % (name,))
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger, handler


class LockedPidFile(object):
    def __init__(self, pidfile_path):
        self.pidfile_path = pidfile_path
        self.pidfile_lock_path = self.pidfile_path + ".lock"
        self.pidfile = None
        self.pidfile_lock = None

    def acquire(self, pid=None):
        self.pidfile_lock = process_lock.InterProcessLock(self.pidfile_lock_path)
        if not self.pidfile_lock.acquire():
            LOG.error("Unable to acquire pifile_lock %s", self.pidfile_lock_path)
            return False
        if pid is None:
            pid = os.getpid()
        if os.path.exists(self.pidfile_path):
            try:
                with open(self.pidfile_path) as f:
                    stalepid = int(f.read())
                if stalepid in psutil.pids():
                    raise Error(
                        "Pidfile %s exists and is not locked but pid %s is still alive"
                        % (self.pidfile_path, stalepid)
                    )
            except Exception as exc:
                LOG.exception("Exception %r checking the stale pidfile, ignoring", exc)
            LOG.warning(
                "Pidfile exists but is not locked, removing %s", self.pidfile_path
            )
            os.unlink(self.pidfile_path)

        self.pidfile = open(
            self.pidfile_path, "x", opener=functools.partial(os.open, mode=0o600)
        )
        self.pidfile.write(str(pid))
        self.pidfile.flush()
        return True

    def release(self):
        if not self.pidfile_lock.acquired:
            raise Error("Lock is not locked")
        self.pidfile.close()
        if os.path.exists(self.pidfile_path):
            os.unlink(self.pidfile_path)
        os.unlink(self.pidfile_lock_path)
        self.pidfile_lock.release()

    def __enter__(self):
        acquired = self.acquire()
        if acquired:
            return self.pidfile
        raise Error("Could not acquire lock")

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()


def main():
    docstr = __doc__ % {"script": os.path.basename(__file__)}
    args = docopt(docstr)
    if args["--when"] not in (
        "s",
        "m",
        "h",
        "d",
        "w0",
        "w1",
        "w2",
        "w3",
        "w4",
        "w5",
        "w6",
        "midnight",
    ):
        sys.stderr.write(
            "Value %r for --when parameter not understood.\n" % (args["--when"],)
        )
        sys.stderr.write(docstr)
        sys.exit(1)
    if args["--debug"]:
        print(args)
    os.umask(0o077)
    out_logger, out_handler = get_logger(
        "stdout",
        args["--stdout-log"],
        args["--log-format"],
        args["--date-format"],
        args["--log-handler"],
        args["--when"],
        int(args["--interval"]),
        int(args["--backup-count"]),
    )
    preserve = [out_handler.stream]
    if args["--stderr-log"] == "STDOUT":
        err_logger = out_logger
        err_handler = out_handler
    else:
        err_logger, err_handler = get_logger(
            "stderr",
            args["--stderr-log"],
            args["--log-format"],
            args["--date-format"],
            args["--log-handler"],
            args["--when"],
            int(args["--interval"]),
            int(args["--backup-count"]),
        )
        preserve.append(err_handler.stream)

    if args["--pidfile"]:
        pidfile = LockedPidFile(args["--pidfile"])
    else:
        pidfile = None

    if args["--app-pidfile"]:
        applock = LockedPidFile(args["--app-pidfile"])
    else:
        applock = None

    # DaemonContext is about to close all of our file handles so our logger will stop working. Add the error handler
    # to our logger so any logging after this won't be lost.
    LOG.addHandler(err_handler)
    with daemon.DaemonContext(
        pidfile=pidfile, working_directory=os.getcwd(), files_preserve=preserve
    ):
        try:
            proc = subprocess.Popen(
                args["<command>"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
                if args["--stderr-log"] == "STDOUT"
                else subprocess.PIPE,
            )
            if applock and not applock.acquire(proc.pid):
                try:
                    proc.terminate()
                    start = datetime.datetime.now()
                    while proc.poll() is None and datetime.datetime.now() - start < datetime.timedelta(
                        seconds=1
                    ):
                        time.sleep(0.1)
                    if proc.poll() is None:
                        proc.kill()
                except Exception:
                    LOG.exception(
                        "Exception killing the app process after acquiring the pidfile failed."
                    )
                raise Error(
                    "Could not acquire app pidfile lock %s" % (applock.file_path,)
                )
            proc.stdin.close()
            thread = threading.Thread(
                target=multiproc.LinePipe(
                    "",
                    io.TextIOWrapper(proc.stdout, errors="backslashreplace"),
                    None,
                    out_logger.info,
                    "",
                    False,
                ).flow
            )
            thread.start()
            threads = [thread]
            if args["--stderr-log"] != "STDOUT":
                thread = threading.Thread(
                    target=multiproc.LinePipe(
                        "",
                        io.TextIOWrapper(proc.stderr, errors="backslashreplace"),
                        None,
                        err_logger.info,
                        "",
                        False,
                    ).flow
                )
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
        except Exception:
            LOG.exception("Exception within DaemonContext")
        finally:
            if applock:
                applock.release()
        sys.exit()


if __name__ == "__main__":
    main()
