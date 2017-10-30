# reversefold.util

[Available on pypi](https://pypi.python.org/pypi/reversefold.util)

This is a connection of various command-line scripts and libraries which have come in useful over the years I've worked with Python.


## log.py

Captures stdout of a process and enables transformation the output (such as adding a timestamp to each line) and is compatible with external logrotate through `WatchedFileHandler`.

## daemonize.py

Useful for daemonizing another process which either does not daemonize itself or for which you want to capture stdout and stderr to log files. Uses `WatchedFileHandler` for output to log files to allow for external log rotation.

## stream.py

Similar to `tail -f` but with some more options for type of buffering and supports streaming the entire current contents of the file before then following the tail of the file.

## reversefold.util

### rate_limit_gen

A generator wrapper which rate-limits another generator. If the rate is exceeded, further values received within the `period` are discarded. Useful, for example, for making sure that the number of lines you display from a log file you're following don't cause your terminal to block while displaying a huge amount of output.

### chunked

Breaks up an iterable into equal-sized chunks.

## reversefold.util.ssh

### SSHHost

A programmatic interface to ssh. Allows easily running a single command or a shell script or interactively sending input and displaying output. Originally written as a drop-in monkeypatch for fabric's use of paramiko.

## reversefold.util.multiproc

### run_subproc

Takes a subprocess as input and sets up threads for handling and displaying stdout and stderr from the process. Defaults to blocking until the process is finished but also supports immediately returning and including the threads in the return value. Also defaults to capturing the stdout and stderr and returning them as lists of lines.

## reversefold.util.proc

Provides context managers to ensure that a process is sent a TERM or KILL signal (or both) to a process when the context block exits. Can optionally find child processes recursively and send the same signal(s) to them. Also provides functions for the same functionality.
