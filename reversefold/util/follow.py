import os
import time


class LineFollower(object):
    """
    Implements a simple (naive) file streamer which will emit lines
    until the finish property is set to False.

    Ex:
    with Follower('a') as f:
        for line in f:
            print line
            if line == 'a':
                f.finish = True
    """
    def __init__(self, filename, tail_only=False):
        self.filename = filename
        self.tail_only = tail_only
        self.file = None
        self.finish = False

    def __enter__(self):
        self.file = open(self.filename, 'r')
        if self.tail_only:
            # Go to the end of the file
            self.file.seek(0, 2)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.file.close()

    def __iter__(self):
        buf = []
        while True:
            new_line = self.file.readline()
            if not new_line:
                if self.finish:
                    raise StopIteration()
                time.sleep(0.1)
                continue
            buf.append(new_line)
            if buf[-1][-1] == '\n':
                yield ''.join(buf)[:-1]
                buf = []


class Follower(object):
    """
    Implements a simple (naive) file streamer which will emit bytes
    until the finish property is set to False.

    Ex:
    with Follower('a') as f:
        i = 0
        for data in f:
            sys.stdout.write(data)
            i += 1
            if i == 50:
                f.finish = True
    """
    def __init__(self, filename, tail_only=False, chunk_size=1024):
        self.filename = filename
        self.tail_only = tail_only
        self.chunk_size = chunk_size

        self.fd = None
        self.finish = False

    def __enter__(self):
        self.fd = os.open(self.filename, os.O_RDONLY | os.O_NONBLOCK)
        if self.tail_only:
            # Go to the end of the file
            os.lseek(self.fd, 0, os.SEEK_END)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.close(self.fd)

    def __iter__(self):
        while True:
            data = os.read(self.fd, self.chunk_size)
            if not data:
                if self.finish:
                    raise StopIteration()
                time.sleep(0.1)
                continue
            yield data
