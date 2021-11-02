#!/usr/bin/env python3
import sys

import cachecontrol
import requests
from cachecontrol.cache import DictCache
from cachecontrol.heuristics import BaseHeuristic

import logging

clogger = logging.getLogger("cachecontrol")
clogger.addHandler(logging.StreamHandler())
clogger.setLevel(logging.DEBUG)


from pprint import pprint


class NoAgeHeuristic(BaseHeuristic):
    def update_headers(self, response):
        if "cache-control" in response.headers:
            del response.headers["cache-control"]


cache_adapter = cachecontrol.CacheControlAdapter(
    DictCache(), cache_etags=True, heuristic=NoAgeHeuristic()
)


session = requests.Session()
session.mount("https://", cache_adapter)


def log_resp(resp):
    return

    print(f"{resp.status_code} {resp.request.method}")
    for k, v in response.headers.items():
        print(f"{k}: {v}")


for i in range(2):
    response = session.get(
        "https://api.github.com/repos/sigmavirus24/github3.py/pulls/1033"
    )
    log_resp(response)
    print(f"Content length: {len(response.content)}")
    print(response.from_cache)
    if len(response.content) == 0:
        sys.exit(1)
