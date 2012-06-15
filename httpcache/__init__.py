"""
A caching wrapper for the requests session.
"""
import re
import email
import calendar
import time

import requests


URI = re.compile(r"^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?")


def parse_uri(uri):
    """Parses a URI using the regex given in Appendix B of RFC 3986.

        (scheme, authority, path, query, fragment) = parse_uri(uri)
    """
    groups = URI.match(uri).groups()
    return (groups[1], groups[3], groups[4], groups[6], groups[8])


def urlnorm(uri):
    (scheme, authority, path, query, fragment) = parse_uri(uri)
    if not scheme or not authority:
        raise Exception("Only absolute URIs are allowed. uri = %s" % uri)
    authority = authority.lower()
    scheme = scheme.lower()
    if not path:
        path = "/"
    # Could do syntax based normalization of the URI before
    # computing the digest. See Section 6.2.2 of Std 66.
    request_uri = query and "?".join([path, query]) or path
    scheme = scheme.lower()
    defrag_uri = scheme + "://" + authority + request_uri
    return scheme, authority, request_uri, defrag_uri


class CacheControl(object):

    def __init__(self, session, cache=None):
        self.session = session
        self.cache = cache

    def __getattr__(self, key):
        if hasattr(self.session, key):
            return getattr(self.session, key)
        raise AttributeError('%s not found' % key)

    def from_cache(f):
        """
        See if we should use a cached response. We are looking for
        client conditions such as no-cache.
        """
        def cached_handler(self, *args, **kw):
            req = requests.Request(*args, **kw)
            cache_url = req.full_url
            scheme, authority, request_uri, defrag_uri = urlnorm(cache_url)

            cc = self._parse_cache_control(req.headers)
            if not cc or 'no-cache' in cc:
                return f(self, *args, **kw)

            if defrag_uri in self.cache:
                return self.cache[defrag_uri]['response']
        return cached_handler

    @from_cache
    def get(self, url, headers=None, *args, **kw):
        # See if we should use the cache
        resp = self.session.get(url, headers=headers, *args, **kw)
        self.cache_response(resp)
        return resp

    def cache_response(self, resp):
        """
        We are going to see if we should cache the response.
        """
        if 'cache-control' not in resp.headers:
            return

        cc = self._parse_cache_control(resp.headers)
        if 'date' in resp.headers:
            date = calendar.timegm(
                email.Utils.parsedate_tz(resp.headers['date']))
            if 'max-age' in cc:
                resp.from_cache = True
                self.cache[resp.request.full_url] = {
                    'max-age': date + int(cc['max-age']),
                    'response': resp
                }

    def _parse_cache_control(self, headers):
        retval = {}
        if 'cache-control' in headers:
            parts = headers['cache-control'].split(',')
            parts_with_args = [
                tuple([x.strip().lower() for x in part.split("=", 1)])
                for part in parts if -1 != part.find("=")]
            parts_wo_args = [(name.strip().lower(), 1)
                             for name in parts if -1 == name.find("=")]
            retval = dict(parts_with_args + parts_wo_args)
        return retval

    def match(self, req, resp):
        retval = "STALE"
        cc = self._parse_cache_control(req)
        cc_response = self._parse_cache_control(resp)

        if 'pragma' in req and req['pragma'].lower().find('no-cache') != -1:
            retval = "TRANSPARENT"
            if 'cache-control' not in req:
                req['cache-control'] = 'no-cache'
        elif 'no-cache' in cc:
            retval = "TRANSPARENT"
        elif 'no-cache' in cc_response:
            retval = "STALE"
        elif 'only-if-cached' in cc:
            retval = "FRESH"
        elif 'date' in resp:
            date = calendar.timegm(email.Utils.parsedate_tz(resp['date']))
            now = time.time()
            current_age = max(0, now - date)
            if 'max-age' in cc_response:
                try:
                    freshness_lifetime = int(cc_response['max-age'])
                except ValueError:
                    freshness_lifetime = 0
            elif 'expires' in resp:
                expires = email.Utils.parsedate_tz(resp['expires'])
                if None == expires:
                    freshness_lifetime = 0
                else:
                    end = calendar.timegm(expires) - date
                    freshness_lifetime = max(0, end)
            else:
                freshness_lifetime = 0
            if 'max-age' in cc:
                try:
                    freshness_lifetime = int(cc['max-age'])
                except ValueError:
                    freshness_lifetime = 0
            if 'min-fresh' in cc:
                try:
                    min_fresh = int(cc['min-fresh'])
                except ValueError:
                    min_fresh = 0
                current_age += min_fresh
            if freshness_lifetime > current_age:
                retval = "FRESH"
        return retval
