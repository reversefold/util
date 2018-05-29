import os
import time


class FileLineFollower(object):
    def __init__(self, file):
        self.file = file
        self.finish = False

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
                # Don't include the trailing newline in the output
                yield ''.join(buf)[:-1]
                buf = []


class FilenameLineFollower(FileLineFollower):
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
        # Explicitly setting file to None as we set it in __enter__
        super(FilenameLineFollower, self).__init__(file=None)
        self.filename = filename
        self.tail_only = tail_only

    def __enter__(self):
        self.file = open(self.filename, 'r')
        if self.tail_only:
            # Go to the end of the file
            self.file.seek(0, 2)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.file.close()
        self.file = None


LineFollower = FilenameLineFollower


class FDFollower(object):
    def __init__(self, fd, chunk_size):
        self.fd = fd
        self.chunk_size = chunk_size
        self.finish = False

    def __iter__(self):
        while True:
            data = os.read(self.fd, self.chunk_size)
            if not data:
                if self.finish:
                    raise StopIteration()
                time.sleep(0.1)
                continue
            yield data


class FilenameFollower(FDFollower):
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
        # Setting fd to None as we set it in __enter__
        super(FilenameFollower, self).__init__(fd=None, chunk_size=chunk_size)
        self.filename = filename
        self.tail_only = tail_only

    def __enter__(self):
        self.fd = os.open(self.filename, os.O_RDONLY | os.O_NONBLOCK)
        if self.tail_only:
            # Go to the end of the file
            os.lseek(self.fd, 0, os.SEEK_END)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.close(self.fd)


Follower = FilenameFollower
