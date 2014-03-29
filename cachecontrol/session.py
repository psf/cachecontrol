from requests.sessions import Session

class CacheControlSession(Session):
    def __init__(self):
        super(CacheControlSession, self).__init__()

    def request(self, *args, **kw):
        # set this so we know its our cache session handler and not requests
        self.cache_session_handler = True

        # auto-cache response
        self.cache_auto = False
        if kw.has_key('cache_auto'):
            self.cache_auto = kw.pop('cache_auto')

        # urls allowed to cache
        self.cache_urls = []
        if kw.has_key('cache_urls'):
            self.cache_urls = [str(args[1])] + kw.pop('cache_urls')

        # timeout for cached responses
        self.cache_max_age = None
        if kw.has_key('cache_max_age'):
            self.cache_max_age = int(kw.pop('cache_max_age'))

        return super(CacheControlSession, self).request(*args, **kw)