import requests
from cachecontrol.adapter import CacheControlAdapter
from cachecontrol.cache import DictCache

from argparse import ArgumentParser


def get_session():
    adapter = CacheControlAdapter(
        DictCache(),
        cache_etags=True,
        serializer=None,
        heuristic=None,
    )
    sess = requests.Session()
    sess.mount('http://', adapter)
    sess.mount('https://', adapter)

    sess.cache_controller = adapter.controller
    return sess


def get_args():
    parser = ArgumentParser()
    parser.add_argument('--url', '-u', help='A URL to try and cache')
    return parser.parse_args()


def main(args=None):
    args = get_args()
    sess = get_session()

    if args.url:
        resp = sess.get(args.url)

        # try setting the cache
        sess.cache_controller.cache_response(resp.request, resp.raw)

        # Now try to get it
        if sess.cache_controller.cached_request(resp.request):
            print('Cached!')
        else:
            print('Not cached :(')



if __name__ == '__main__':
    main()
