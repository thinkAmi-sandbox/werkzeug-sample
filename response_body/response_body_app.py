from werkzeug.exceptions import HTTPException
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request, Response


class Application:
    def __init__(self):
        self.url_map = Map([
            Rule('/', endpoint='index', methods=['GET']),
            Rule('/response', endpoint='response', methods=['GET']),
            Rule('/data', endpoint='data', methods=['GET']),
            Rule('/set_data', endpoint='set_data', methods=['GET']),
        ])

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, f'{endpoint}_handler')(request, **values)
        except HTTPException as e:
            return e

    def index_handler(self, request):
        return Response('Hello world\n')

    def response_handler(self, request):
        response = Response('Hello world\n')
        response.response = 'update response body\n'
        return response

    def data_handler(self, request):
        response = Response('Hello world\n')
        response.data = 'update response body\n'
        return response

    def set_data_handler(self, request):
        response = Response('Hello world\n')
        response.set_data('update response body\n')
        return response

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    app = Application()
    run_simple('0.0.0.0', 5000, app, use_debugger=True, use_reloader=True)
