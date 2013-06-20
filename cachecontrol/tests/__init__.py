from pprint import pformat


class SimpleApp(object):

    def __call__(self, env, start_response):
        headers = [
            ('Cache-Control', 'max-age=5000'),
            ('Content-Type', 'text/plain'),
        ]
        start_response('200 OK', headers)
        return pformat(env)
