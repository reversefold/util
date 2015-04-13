import threading
import sys

from colorama import Fore, Style


class Pipe(object):
    # TODO: input and output_func are not symmetric, perhaps
    # they should use the same interface?
    def __init__(self, prefix, input, buf, output_func, pre, post):
        self.prefix = prefix
        self.input = input
        self.buf = buf
        self.output_func = output_func
        self.pre = pre
        self.post = post

    def flow(self):
        # NOTE: 'for line in self.input' seems correct but will
        #  implicitly do extra buffering in Python 2.7, which won't
        #  give you a line immediately every time one is available.
        # This is supposedly fixed in Python 3.2.
        for line in iter(self.input.readline, b''):
            self.buf.append(line)
            self.output_func('%s%s%s%s' % (self.prefix, self.pre, line.rstrip(), self.post))


def run_subproc(proc, prefix='', wait=True, output_func=None):
    """
    Runs a single subprocess, outputting then returning the stderr and stdout

    returns: stdout, stderr
    """
    if output_func is None:
        output_func = sys.stdout.write
    stdout = []
    stderr = []
    threads = []
    try:
        for (prefix, pipe, buf, pre, post) in [
            ('%s%s[%s%serr%s%s]%s ' % (prefix, Style.BRIGHT, Style.NORMAL,
                                       Fore.RED, Fore.RESET, Style.BRIGHT, Style.NORMAL),
                proc.stderr, stderr, Fore.RED, Fore.RESET),
            ('%s%s[%s%sout%s%s]%s ' % (prefix, Style.BRIGHT, Style.NORMAL,
                                       Fore.GREEN, Fore.RESET, Style.BRIGHT, Style.NORMAL),
                proc.stdout, stdout, '', ''),
        ]:
            if pipe is None or pipe.closed:
                continue
            thread = threading.Thread(
                name=prefix,
                target=Pipe(prefix, pipe, buf, output_func, pre, post).flow)
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
    except:
        pass
    try:
        proc.wait()
    except:
        pass
