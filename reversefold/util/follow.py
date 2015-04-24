import time


class Follower(object):
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
