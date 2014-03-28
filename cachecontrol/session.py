from lib.requests.sessions import Session

class CacheControlSession(Session):
    def __init__(self, *args, **kw):
        super(CacheControlSession, self).__init__(*args, **kw)

    def request(self, *args, **kw):
        autocache = kw.pop('autocache')

        req = super(CacheControlSession, self).request(*args, **kw)
        return req