from requests.sessions import Session

class CacheControlSession(Session):
    def __init__(self, *args, **kw):
        super(CacheControlSession, self).__init__(*args, **kw)

    def request(self, *args, **kw):
        # auto-cache response
        self.autocache = False
        if kw.has_key('autocache'):
            self.autocache = kw.pop('autocache')

        return super(CacheControlSession, self).request(*args, **kw)