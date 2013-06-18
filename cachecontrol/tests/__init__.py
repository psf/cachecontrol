class SimpleApp(object):

    def __call__(self, env, start_response):
        handler = filter(bool, env['PATH_INFO'].split('/'))[-1].lower()
        return getattr(self, handler)(env, start_response)

    def max_age(self, env, start_response):
        headers = [
            ('Cache-Control', 'max-age=5000')
        ]
        start_response('200 OK', headers)
        return 'Hello World!'
