import os
import threading
import sys

from colorama import Fore, Style


DEFAULT_OUT_PREFIX = '%s[%s%sout%s%s]%s ' % (
    Style.BRIGHT, Style.NORMAL, Fore.GREEN, Fore.RESET, Style.BRIGHT, Style.NORMAL)
DEFAULT_OUT_POSTFIX = ''
DEFAULT_ERR_PREFIX = '%s[%s%serr%s%s]%s%s ' % (
    Style.BRIGHT, Style.NORMAL, Fore.RED, Fore.RESET, Style.BRIGHT, Style.NORMAL, Fore.RED)
DEFAULT_ERR_POSTFIX = Fore.RESET


class Pipe(object):
    def __init__(self, input_stream, output_func):
        self.input_stream = input_stream
        self.output_func = output_func

    def flow(self):
        while True:
            data = os.read(self.input_stream.fileno(), 65536)
            if data == b'':
                break
            self.output_func(data)


class LinePipe(object):
    # TODO: input and output_func are not symmetric, perhaps they should
    # use the same interface?
    def __init__(self, prefix, input_stream, buf, output_func, postfix):
        self.prefix = prefix
        self.input_stream = input_stream
        self.buf = buf
        self.output_func = output_func
        self.postfix = postfix

    def flow(self):
        # NOTE: 'for line in self.input' seems correct but will
        #  implicitly do extra buffering in Python 2.7, which won't
        #  give you a line immediately every time one is available.
        # This is supposedly fixed in Python 3.2.
        for line in iter(self.input_stream.readline, b''):
            self.buf.append(line)
            self.output_func('%s%s%s\n' % (self.prefix, line.rstrip(), self.postfix))


def run_subproc(
    proc, prefix='', wait=True, output_func=None,
    out_prefix=None,
    out_postfix=None,
    err_prefix=None,
    err_postfix=None,
):
    """
    Runs a single subprocess, outputting then returning the stderr and stdout

    returns: stdout, stderr
    """
    if out_prefix is None:
        out_prefix = DEFAULT_OUT_PREFIX
    if out_postfix is None:
        out_postfix = DEFAULT_OUT_POSTFIX
    if err_prefix is None:
        err_prefix = DEFAULT_ERR_PREFIX
    if err_postfix is None:
        err_postfix = DEFAULT_ERR_POSTFIX
    if output_func is None:
        output_func = sys.stdout.write
    stdout = []
    stderr = []
    threads = []
    try:
        for (prefix, pipe, buf, postfix) in [
            ('%s%s' % (prefix, err_prefix),
                proc.stderr, stderr, err_postfix),
            ('%s%s' % (prefix, out_prefix),
                proc.stdout, stdout, out_postfix),
        ]:
            if pipe is None or pipe.closed:
                continue
            thread = threading.Thread(
                name=prefix,
                target=LinePipe(prefix, pipe, buf, output_func, postfix).flow)
            threads.append(thread)
            thread.start()
        if wait and proc.returncode is None:
            proc.wait()
        if wait:
            return (stdout, stderr)
        return (stdout, stderr, threads)
    finally:
        if wait:
            # by this time the proc should be finished and all pipes should be closed
            # but just in case...
            terminate_subproc(proc, threads)


def terminate_subproc(proc, threads):
    for thread in threads:
        thread.join()
    for pipe in [proc.stdin, proc.stderr, proc.stdout]:
        if pipe is None or pipe.closed:
            continue
        pipe.close()
    try:
        proc.terminate()
    except Exception:
        pass
    try:
        proc.wait()
    except Exception:
        pass
