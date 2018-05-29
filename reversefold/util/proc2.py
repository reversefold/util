import contextlib
import logging
import os
import pwd
import signal

import psutil


LOG = logging.getLogger(__name__)

_SENTINEL = object()


# TODO: support arbitrary signals, not just TERM and KILL.
# Potentially support lists of signals (with wait times for graceful shutdown?).


def _signal_processes(procs, sig):
    for proc in procs:
        if proc.is_running():
            try:
                proc.send_signal(sig)
            except psutil.NoSuchProcess:
                pass
            except Exception as e:
                LOG.error('Exception sending signal %s to %r: %r', sig, proc, e)


def get_process_tree(pid):
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return []
    return [proc] + proc.children(recursive=True)


# Supports any process object with a pid attribute, so supports at least psutil.Process and subprocess.Popen objects.
@contextlib.contextmanager
def signalling(proc, sig, recursive=False, _procs=None):
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
            _signal_processes(procs, sig)
        except Exception as e:
            if exc:
                LOG.exception('Exception sending signal %s to %r: %r', sig, procs, e)
            else:
                raise


def interrupting(proc, recursive=False, _procs=None):
    return signalling(proc, signal.SIGINT, recursive=recursive, _procs=_procs)


def terminating(proc, recursive=False, _procs=None):
    return signalling(proc, signal.SIGTERM, recursive=recursive, _procs=_procs)


def killing(proc, recursive=False, _procs=None):
    return signalling(proc, signal.SIGKILL, recursive=recursive, _procs=_procs)


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


def interrupt(proc, recursive=False):
    with interrupting(proc, recursive=recursive):
        pass


def terminate(proc, recursive=False):
    with terminating(proc, recursive=recursive):
        pass


def kill(proc, recursive=False):
    with killing(proc, recursive=recursive):
        pass


def die(proc, recursive=False):
    with dead(proc, recursive=recursive):
        pass


def get_processes_in_path(path, owner=_SENTINEL):
    if owner is _SENTINEL:
        owner = pwd.getpwuid(os.getuid()).pw_name
    procs = []
    for proc in psutil.process_iter():
        if owner is not None and proc.username() != owner:
            continue
        try:
            if (
                proc.exe().startswith(path)
                or any(
                    f.path.startswith(path)
                    for f in proc.open_files()
                )
            ):
                procs.append(proc)
        except psutil.AccessDenied:
            pass
    return procs
