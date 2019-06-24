#!/usr/bin/env python
"""Connects to a MySQL server and runs a simple query to make sure it is still responding
about every second.

Usage:
  mysqlping.py -h | --help
  mysqlping.py <hostname> [--port=<port>] [--username=<username>] [--password=<password>]

Options:
  -h --help                 Help.
  <hostname>                The hostname of the MySQL server to "ping".
  -P <port> --port=<port>   Port to connect to. [Default: 3306]
  -u <username> --user=<username> --username=<username> Username to authenticate as.
  -p <password> --pass=<password> --password=<password> Password to authenticate with.
"""

import datetime
from docopt import docopt
import MySQLdb
import socket
import sys
import time

i = 0
down_start = None


def log(msg):
    global i
    print("%s [%r] %s" % (datetime.datetime.now(), i, msg))
    sys.stdout.flush()
    i += 1


def mysqlping(hostname, port=3306, username=None, password=None):
    global down_start
    socket.setdefaulttimeout(1)
    while True:
        try:
            if username is None:
                conn = MySQLdb.connect(hostname, port=port, connect_timeout=1)
            else:
                conn = MySQLdb.connect(
                    hostname,
                    port=port,
                    user=username,
                    passwd=password,
                    connect_timeout=1,
                )
            if down_start is not None:
                log("Connected, downtime %s" % (datetime.datetime.now() - down_start,))
                down_start = None
            else:
                log("Connected")
            time.sleep(1)
            while True:
                cur = conn.cursor()
                cur.execute("SELECT NOW()")
                log("Ping %r" % (cur.fetchone(),))
                time.sleep(1)
        except Exception as e:
            if down_start is None:
                down_start = datetime.datetime.now()
            log("Down for %s so far: %s" % (datetime.datetime.now() - down_start, e))
            time.sleep(1)


if __name__ == "__main__":
    args = docopt(__doc__)
    mysqlping(
        args["<hostname>"], int(args["--port"]), args["--username"], args["--password"]
    )
