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
