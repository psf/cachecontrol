import sys
import requests
import argparse

from multiprocessing import Process
from datetime import datetime
from wsgiref.simple_server import make_server
from cachecontrol import CacheControl

HOST = "localhost"
PORT = 8050
URL = "http://{}:{}/".format(HOST, PORT)


class Server(object):

    def __call__(self, env, sr):
        body = "Hello World!"
        status = "200 OK"
        headers = [
            ("Cache-Control", "max-age=%i" % (60 * 10)), ("Content-Type", "text/plain")
        ]
        sr(status, headers)
        return body


def start_server():
    httpd = make_server(HOST, PORT, Server())
    httpd.serve_forever()


def run_benchmark(sess):
    proc = Process(target=start_server)
    proc.start()

    start = datetime.now()
    for i in xrange(0, 1000):
        sess.get(URL)
        sys.stdout.write(".")
    end = datetime.now()
    print()

    total = end - start
    print("Total time for 1000 requests: %s" % total)
    proc.terminate()


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n",
        "--no-cache",
        default=False,
        action="store_true",
        help="Do not use cachecontrol",
    )
    args = parser.parse_args()

    sess = requests.Session()
    if not args.no_cache:
        sess = CacheControl(sess)

    run_benchmark(sess)


if __name__ == "__main__":
    run()
