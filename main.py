import os
import signal
import sys
import time

# supervisord xml-rpc connection
from xmlrpc.client import ServerProxy
svd = ServerProxy('http://127.0.0.1:9001/RPC2')
identity = os.environ.get('CONCIERGE_IDENTITY', default="develop")


def sigterm_handler(signum, frame):
    print("concierge shutting down.")
    # if concierge dies, all tasks need to die as well!

    sys.exit(0)


def loop(config):
    while True:
        # do stuff
        print(svd.supervisor.getAllProcessInfo())

        time.sleep(1)


def main():
    # program setup
    signal.signal(signal.SIGTERM, sigterm_handler)

    # check connection to supervisord
    print(svd.supervisor.getState())
    loop()


main()
