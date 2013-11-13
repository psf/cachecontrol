"""
The httplib2 algorithms ported for use with requests.
"""
import re
import email
import calendar
import time

from cachecontrol.cache import DictCache


URI = re.compile(r"^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?")


def parse_uri(uri):
    """Parses a URI using the regex given in Appendix B of RFC 3986.

        (scheme, authority, path, query, fragment) = parse_uri(uri)
    """
    groups = URI.match(uri).groups()
    return (groups[1], groups[3], groups[4], groups[6], groups[8])


class CacheController(object):
    """An interface to see if request should cached or not.
    """
    def __init__(self, cache=None):
        self.cache = cache or DictCache()

    def _urlnorm(self, uri):
        """Normalize the URL to create a safe key for the cache"""
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

        return defrag_uri

    def cache_url(self, uri):
        return self._urlnorm(uri)

    def parse_cache_control(self, headers):
        """
        Parse the cache control headers returning a dictionary with values
        for the different directives.
        """
        retval = {}

        cc_header = 'cache-control'
        if 'Cache-Control' in headers:
            cc_header = 'Cache-Control'

        if cc_header in headers:
            parts = headers[cc_header].split(',')
            parts_with_args = [
                tuple([x.strip().lower() for x in part.split("=", 1)])
                for part in parts if -1 != part.find("=")]
            parts_wo_args = [(name.strip().lower(), 1)
                             for name in parts if -1 == name.find("=")]
            retval = dict(parts_with_args + parts_wo_args)
        return retval

    def cached_request(self, url, headers):
        cache_url = self.cache_url(url)
        cc = self.parse_cache_control(headers)

        # non-caching states
        no_cache = True if 'no-cache' in cc else False
        if 'max-age' in cc and cc['max-age'] == 0:
            no_cache = True

        # see if it is in the cache anyways
        in_cache = self.cache.get(cache_url)
        if no_cache or not in_cache:
            return False

        # It is in the cache, so lets see if it is going to be
        # fresh enough
        resp = self.cache.get(cache_url)

        # Check our Vary header to make sure our request headers match
        # up. We don't delete it from the though, we just don't return
        # our cached value.
        #
        # NOTE: Because httplib2 stores raw content, it denotes
        #       headers that were sent in the original response by
        #       adding -varied-$name. We don't have to do that b/c we
        #       are storing the object which has a reference to the
        #       original request. If that changes, then I'd propose
        #       using the varied headers in the cache key to avoid the
        #       situation all together.
        if 'vary' in resp.headers:
            varied_headers = resp.headers['vary'].replace(' ', '').split(',')
            original_headers = resp.request.headers
            for header in varied_headers:
                # If our headers don't match for the headers listed in
                # the vary header, then don't use the cached response
                if headers.get(header, None) != original_headers.get(header):
                    return False

        now = time.time()
        date = calendar.timegm(
            email.Utils.parsedate_tz(resp.headers['date']))
        current_age = max(0, now - date)

        # TODO: There is an assumption that the result will be a
        # requests response object. This may not be best since we
        # could probably avoid instantiating or constructing the
        # response until we know we need it.
        resp_cc = self.parse_cache_control(resp.headers)

        # determine freshness
        freshness_lifetime = 0
        if 'max-age' in resp_cc and resp_cc['max-age'].isdigit():
            freshness_lifetime = int(resp_cc['max-age'])
        elif 'expires' in resp.headers:
            expires = email.Utils.parsedate_tz(resp.headers['expires'])
            if expires is not None:
                expire_time = calendar.timegm(expires) - date
                freshness_lifetime = max(0, expire_time)

        # determine if we are setting freshness limit in the req
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
            # adjust our current age by our min fresh
            current_age += min_fresh

        # see how fresh we actually are
        fresh = (freshness_lifetime > current_age)

        if fresh:
            # make sure we set the from_cache to true
            resp.from_cache = True
            return resp

        # we're not fresh, clean out the junk
        self.cache.delete(cache_url)

        # return the original handler
        return False

    def cache_response(self, request, resp):
        """
        Algorithm for caching requests.

        This assumes a requests Response object.
        """
        # From httplib2: Don't cache 206's since we aren't going to
        # handle byte range requests
        if resp.status_code not in [200, 203]:
            return

        cc_req = self.parse_cache_control(request.headers)
        cc = self.parse_cache_control(resp.headers)

        cache_url = self.cache_url(request.url)

        # Delete it from the cache if we happen to have it stored there
        no_store = cc.get('no-store') or cc_req.get('no-store')
        if no_store and self.cache.get(cache_url):
            self.cache.delete(cache_url)

        # Add to the cache if the response headers demand it. If there
        # is no date header then we can't do anything about expiring
        # the cache.
        if 'date' in resp.headers:
            # cache when there is a max-age > 0
            if cc and cc.get('max-age'):
                if int(cc['max-age']) > 0:
                    self.cache.set(cache_url, resp)

            # If the request can expire, it means we should cache it
            # in the meantime.
            elif 'expires' in resp.headers:
                if resp.headers['expires']:
                    self.cache.set(cache_url, resp)
