import contextlib
import logging

import psutil


LOG = logging.getLogger(__name__)


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


@contextlib.contextmanager
def signalling(proc, signal_func_name, recursive=False):
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


def terminating(proc, recursive=False):
    return signalling(proc, 'terminate', recursive=recursive)


def killing(proc, recursive=False):
    return signalling(proc, 'kill', recursive=recursive)
