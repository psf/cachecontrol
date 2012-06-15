from __future__ import print_function
import cherrypy


class CacheTestingServer(object):

    def index(self):
        return 'foo'
    index.exposed = True

    def max_age(self):
        cherrypy.response.headers['Cache-Control'] = 'max-age=300'
        return 'max age'
    max_age.exposed = True

    def no_cache(self):
        cherrypy.response.headers['Cache-Control'] = 'no-cache'
        return 'no cache'
    no_cache.exposed = True

    def must_revalidate(self):
        cherrypy.response.headers['Cache-Control'] = 'must-revalidate'
        return 'must revalidate'
    must_revalidate.exposed = True


if __name__ == '__main__':
    cherrypy.tree.mount(CacheTestingServer(), '/')
    cherrypy.engine.start()
    cherrypy.engine.block()
