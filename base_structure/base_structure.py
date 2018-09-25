import os

from werkzeug.wrappers import Request, Response
from werkzeug.wsgi import SharedDataMiddleware


class BaseStructure:
    """Werkzeugのチュートリアルにあった、Werkzeugアプリの基本的な構成
    http://werkzeug.pocoo.org/docs/0.14/tutorial/#step-2-the-base-structure
    """
    def dispatch_request(self, request):
        return Response('Hello world!')

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        """WSGIアプリを直接dispatchすることで、wsgi_app()をWSGIミドルウェアっぽく使える"""
        return self.wsgi_app(environ, start_response)


def create_app(with_static=True):
    application = BaseStructure()

    if with_static:
        application.wsgi_app = SharedDataMiddleware(
            application.wsgi_app,
            {'/static': os.path.join(os.path.dirname(__file__), 'static')}
        )
    return application


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    app = create_app()
    run_simple('127.0.0.1', 5000, app, use_debugger=True, use_reloader=True)
