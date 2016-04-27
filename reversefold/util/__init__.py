from datetime import datetime
import logging
import os
import sys


LOG = logging.getLogger(__name__)


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


def chunked(seq, chunk_size):
    """Take an input sequence (any iterable, including generators) and yield it in chunks of the given size.
        [i for i in chunked(xrange(1, 10), 2)]
        [[1, 2], [3, 4], [5, 6], [7, 8], [9]]
    """
    chunk = []
    i = 0
    for val in seq:
        chunk.append(val)
        i += 1
        if i == chunk_size:
            yield chunk
            chunk = []
            i = 0
    if i > 0:
        yield chunk


def force_stdout_line_buffer():
    if hasattr(sys.stdout, 'fileno'):
        # Force stdout to be line-buffered
        sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)
    else:
        LOG.warning('sys.stdout has no fileno attribute, it cannot be line-buffered')
