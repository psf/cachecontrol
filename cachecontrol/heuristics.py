import calendar

from email.utils import formatdate, parsedate

from datetime import datetime, timedelta


def expire_after(delta, date=None):
    date = date or datetime.now()
    return date + delta


def datetime_to_header(dt):
    return formatdate(calendar.timegm(dt.timetuple()))


class BaseHeuristic(object):

    def warning(self, response):
        """
        Return a valid 1xx warning header value describing the cache adjustments.

        The response is provided too allow warnings like 113
        http://tools.ietf.org/html/rfc7234#section-5.5.4 where we need
        to explicitly say response is over 24 hours old.
        """
        return '110 - "Response is Stale"'

    def update_headers(self, response):
        """Update the response headers with any new headers.

        NOTE: This SHOULD always include some Warning header to
              signify that the response was cached by the client, not
              by way of the provided headers.
        """
        return {}

    def apply(self, response):
        warning_header_value = self.warning(response)
        response.headers.update(self.update_headers(response))
        if warning_header_value is not None:
            response.headers.update({'Warning': warning_header_value})
        return response


class OneDayCache(BaseHeuristic):
    """
    Cache the response by providing an expires 1 day in the
    future.
    """
    def update_headers(self, response):
        headers = {}

        if 'expires' not in response.headers:
            date = parsedate(response.headers['date'])
            expires = expire_after(timedelta(days=1),
                                   date=datetime(*date[:6]))
            headers['expires'] = datetime_to_header(expires)
            headers['cache-control'] = 'public'
        return headers


class ExpiresAfter(BaseHeuristic):
    """
    Cache **all** requests for a defined time period.
    """

    def __init__(self, **kw):
        self.delta = timedelta(**kw)

    def update_headers(self, response):
        expires = expire_after(self.delta)
        return {
            'expires': datetime_to_header(expires),
            'cache-control': 'public',
        }

    def warning(self, response):
        tmpl = '110 - Automatically cached for %s. Response might be stale'
        return tmpl % self.delta

_ONE_DAY_IN_SECONDS = timedelta(days=1)

class LastModifiedHeuristic(BaseHeuristic):
    """
    Apply the heuristic suggested by RFC 7234, 4.2.2,
    using the Last-Modified date, when no explicit
    freshness is specified.
    """

    def __init__(self):
        self.cacheable_by_default_statuses = set([200, 203, 204, 206, 300, 301, 404, 405, 410, 414, 501])

    def update_headers(self, response):
        if 'expires' not in response.headers:
            if 'cache-control' not in response.headers or response.headers['cache-control'] == 'public':
                if response.status in self.cacheable_by_default_statuses:
                    if 'last-modified' in response.headers:
                        last_modified = parsedate(response.headers['last-modified'])
                        now = datetime.now()
                        age = now - datetime(*last_modified[:6])
                        expires = now + (age / 10)

                        return {'expires': datetime_to_header(expires)}
        return {}

    def warning(self, response):
        now = datetime.now()
        date = parsedate(response.headers['date'])
        current_age = max(timedelta(), now - datetime(*date[:6]))

        if current_age > _ONE_DAY_IN_SECONDS:
            return '113 - Heuristic Expiration'
        else:
            return None
