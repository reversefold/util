import contextlib
import logging

import psutil


LOG = logging.getLogger(__name__)


# TODO: support arbitrary signals, not just TERM and KILL.
# Potentially support lists of signals (with wait times for graceful shutdown?).


def _signal_processes(procs, func_name):
    for proc in procs:
        if proc.is_running():
            try:
                getattr(proc, func_name)()
            except psutil.NoSuchProcess:
                pass
            except Exception, e:
                LOG.error('Exception running %s on %r: %r', func_name, proc, e)


def get_process_tree(pid):
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return []
    return [proc] + proc.children(recursive=True)


# Supports any process object with a pid attribute, so supports at least psutil.Process and subprocess.Popen objects.
@contextlib.contextmanager
def signalling(proc, signal_func_name, recursive=False, _procs=None):
    exc = False
    try:
        yield proc
    except:
        exc = True
        raise
    finally:
        try:
            if recursive:
                procs = get_process_tree(proc.pid)
                # if _procs was passed in, add our processes to the list and use the combined list for signalling below
                if _procs is not None:
                    for child in procs:
                        _procs.add(child)
                    procs = list(_procs)
            else:
                try:
                    procs = [psutil.Process(proc.pid)]
                except psutil.NoSuchProcess:
                    procs = []
            _signal_processes(procs, signal_func_name)
        except Exception, e:
            if exc:
                LOG.exception('Exception calling %s on %r: %r', signal_func_name, procs, e)
            else:
                raise


def terminating(proc, recursive=False, _procs=None):
    return signalling(proc, 'terminate', recursive=recursive, _procs=_procs)


def killing(proc, recursive=False, _procs=None):
    return signalling(proc, 'kill', recursive=recursive, _procs=_procs)


@contextlib.contextmanager
def dead(proc, recursive=False):
    if recursive:
        # This object is passed into the killing and terminating contextmanagers, allowing them to pass the list of
        # processes they are working on between them so that if the parent process dies in the terminating context
        # manager but a child process does not die, it will still get the kill signal from the killing contextmanager.
        procs = set()
    else:
        procs = None
    with killing(proc, recursive=recursive, _procs=procs) as kproc:
        with terminating(kproc, recursive=recursive, _procs=procs) as tproc:
            yield tproc


def terminate(proc, recursive=False):
    with terminating(proc, recursive=recursive):
        pass


def kill(proc, recursive=False):
    with killing(proc, recursive=recursive):
        pass


def die(proc, recursive=False):
    with dead(proc, recursive=recursive):
        pass
