#!/usr/bin/env python
import sys
import os
import signal

from supervisor.childutils import listener


def write_stdout(s):
    sys.stdout.write(s)
    sys.stdout.flush()


def write_stderr(s):
    sys.stderr.write(s)
    sys.stderr.flush()


def main():
    while True:
        headers, body = listener.wait(sys.stdin, sys.stdout)
        body = dict([pair.split(":") for pair in body.split(" ")])

        if body["groupname"] == "concierge":
            try:
                pidfile = open('/run/supervisor.pid', 'r')
                pid = int(pidfile.readline())
                os.kill(pid, signal.SIGQUIT)
            except Exception as e:
                write_stdout('could not kill supervisor: %s\n' % e.strerror)

        write_stdout('RESULT 2\nOK')


if __name__ == '__main__':
    main()
