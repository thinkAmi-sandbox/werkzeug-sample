import pathlib
import json
from io import StringIO
import csv
from urllib.parse import quote

from werkzeug.exceptions import HTTPException
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request, Response
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.datastructures import Headers


class Application:
    def __init__(self):
        self.url_map = Map([
            Rule('/get-only', endpoint='get_only', methods=['GET']),
            Rule('/post-only', endpoint='post_only', methods=['POST']),
            Rule('/json', endpoint='json'),
            Rule('/upload', endpoint='upload'),
            Rule('/download', endpoint='download'),
            Rule('/extension.html', endpoint='extension'),
        ])

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, f'{endpoint}_handler')(request, **values)
        except HTTPException as e:
            return e

    def get_only_handler(self, request):
        # $ curl --include localhost:5000/get-only
        # HTTP/1.0 200 OK
        # Content-Type: text/plain; charset=utf-8
        # ...
        # GET Only!
        #
        # $ curl -w '\n' --include -X POST 'localhost:5000/get-only' --data 'foo=1'
        # HTTP/1.0 405 METHOD NOT ALLOWED
        # Content-Type: text/html
        # Allow: HEAD, GET
        return Response('GET Only!\n')

    def post_only_handler(self, request):
        # $ curl -w '\n' --include -X POST 'localhost:5000/post-only' --data 'foo=1'
        # HTTP/1.0 200 OK
        # Content-Type: text/plain; charset=utf-8
        # ...
        # POST Only: 1
        #
        # $ curl --include 'localhost:5000/post-only'
        # HTTP/1.0 405 METHOD NOT ALLOWED
        # Content-Type: text/html
        # Allow: POST
        return Response(f'POST Only: {request.form.get("foo")}\n')

    def json_handler(self, request):
        input_data = request.form.get('input')
        result = {
            'foo': 'abc',
            'bar': ['ham', 'spam', 'egg'],
            'result': input_data,
        }
        return Response(json.dumps(result), content_type='application/json')

    def upload_handler(self, request):
        f = request.files.get('upload_file')
        f.save(str(pathlib.Path(f'./uploads/{f.filename}')))
        return Response('hello upload')

    def download_handler(self, request):
        field_names = ['No', 'Name']
        contents = [
            {'No': 1, 'Name': 'Apple'},
            {'No': 2, 'Name': 'Mandarin'},
            {'No': 3, 'Name': 'Grape'},
        ]
        stream = StringIO()
        writer = csv.DictWriter(stream, fieldnames=field_names)

        # CSVヘッダの書込
        writer.writeheader()
        # CSVデータの書込
        writer.writerows(contents)

        # ストリームからデータを取得し、レスポンスとする
        data = stream.getvalue()
        headers = Headers()
        # この書き方の場合、日本語ファイル名はNG(IEを除く)
        # headers.add('Content-Disposition', 'attachment', filename='foo.csv')

        # 日本語ファイルをURLエンコーディング(RFC5987による方法)
        # こうしても、Macだとチルダがアンスコに変換されている：ファイル名として不適切な文字
        encoded_filename = quote(request.form['filename'], safe='~')
        headers.add('Content-Disposition', f"attachment; filename*=UTF-8''{encoded_filename}")

        return Response(
            data,
            headers=headers,
        )

    def extension_handler(self, request):
        return Response('extension request')

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)


def create_app(with_static=True):
    application = Application()

    if with_static:
        application.wsgi_app = SharedDataMiddleware(
            application.wsgi_app, {
                '/static': str(pathlib.Path('./static')),
            })
    return application


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    app = create_app()
    run_simple('0.0.0.0', 5000, app, use_debugger=True, use_reloader=True)
