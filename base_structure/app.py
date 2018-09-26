import pathlib

from werkzeug._compat import text_type
from werkzeug.exceptions import abort, InternalServerError
from werkzeug.utils import redirect
from werkzeug.wrappers import Request, Response
from werkzeug.wsgi import SharedDataMiddleware


class MyInternalServerError(InternalServerError):
    def get_body(self, environ=None):
        # text_type()がprotectedなので、使っていいものか...
        return text_type(
            u'<!DOCTYPE html>'
            u'<title>My Internal Server Error</title>'
            u'<h1>Oh, my internal server error!</h1>'
        )


class Application:
    def dispatch_request(self, request):
        """
        favicon.ico の分のリクエストも入ってくるので注意
        本番だと、静的ファイルがNginxで用意されるので問題ないかも
        """
        body = []
        try:
            # リクエストパスの取得
            body.append(f'request.path: {request.base_url}')
            # => http://localhost:5000/

            # 環境変数の取得
            # WSGI環境変数とCGI環境変数の両方が取れそう：型はdict
            body.append(f'environ: {type(request.environ)} / {request.environ}')
            # => <class 'dict'> / {'wsgi.version': (1, 0), ... , 'REQUEST_METHOD': 'GET', ...

            # HTTPリクエストのメソッドを取得
            body.append(f'HTTP method: {request.method}')
            # => GET

            # クエリストリングを取得
            body.append(f'Query String: {request.args}')
            # => [GET] $ curl http://localhost:5000?foo=bar の場合
            #    ImmutableMultiDict([('foo', 'bar')])
            # => [POST] $ curl -w '\n' -X POST 'localhost:5000/?ham=spam' --data 'foo=1&bar=2' の場合
            #    ImmutableMultiDict([('ham', 'spam')])

            # POSTデータを取得
            body.append(f'Form: {request.form}')
            # => [GET] $ curl http://localhost:5000?foo=bar の場合
            #    ImmutableMultiDict([])
            # => [POST] $ curl -w '\n' -X POST 'localhost:5000/?ham=spam' --data 'foo=1&bar=2' の場合
            #    ImmutableMultiDict([('foo', '1'), ('bar', '2')])

            # request.valuesを使えば、クエリストリング/formの両方の値を取得できる
            body.append(f'request.values: {request.values}')
            # => [GET] $ curl http://localhost:5000?foo=bar の場合
            #    CombinedMultiDict([ImmutableMultiDict([('foo', 'bar')]),
            #                       ImmutableMultiDict([])
            #                     ])
            # => [POST] $ curl -w '\n' -X POST 'localhost:5000/?ham=spam' --data 'foo=1&bar=2' の場合
            #    CombinedMultiDict([ImmutableMultiDict([('ham', 'spam')]),
            #                       ImmutableMultiDict([('foo', '1'), ('bar', '2')])
            #                     ])

            # HTTPリクエストヘッダの出力
            for k, v in request.headers.items():
                body.append(f'Request header: key:{k} / value: {v}')
                # => Request header: key:Host / value: localhost:5000 ...

            # 接続元IPアドレスを取得
            # access_routeとremote_addrの違い
            body.append(f'access_route: {request.access_route}')
            # => access_route: ImmutableList(['127.0.0.1'])
            body.append(f'remote_addr: {request.remote_addr}')
            # => remote_addr: 127.0.0.1

            # リクエスト時のCookieの値を取得
            counter = request.cookies.get('counter', 0)

            msg = '\n'.join(body)
            response = Response(msg)

            # 新しくCookieをセットしない場合でも、再リクエスト時には以前のCookieの値が使われる
            if 'one_time' not in request.cookies:
                response.set_cookie('one_time', 'x')

            # Cookieを削除
            if 'delete_cookie' in request.args:
                response.delete_cookie('one_time')
                # => Set-Cookie: one_time=; Expires=Thu, 01-Jan-1970 00:00:00 GMT; Max-Age=0; Path=/

            # 常にセットするCookie
            response.set_cookie('counter', str(int(counter) + 1))

            # 同じCookieキーで、別々の属性をセットする
            response.set_cookie('same_cookie', '1st', httponly=True)
            response.set_cookie('same_cookie', '2nd', secure=True)

            # 独自HTTPヘッダをセット
            response.headers.add('X-headers-add', 'using add')
            response.headers.add_header('X-headers-add_header', 'using add_header')
            response.headers['X-headers-key'] = 'using key'
            # => X-headers-add: using add
            #    X-headers-add_header: using add_header
            #    X-headers-key: using key

            # content_typeを上書き
            response.content_type = 'application/json'

            # リダイレクト
            if 'redirect' in request.args:
                return redirect('https://www.google.co.jp')

            # HTTP 500 エラー
            if '500' in request.args:
                abort(500)

        except InternalServerError as e:
            # 差し替え
            return MyInternalServerError()

        return response

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        """WSGIアプリを直接dispatchすることで、wsgi_app()をWSGIミドルウェアっぽく使える"""
        print('!!! app !!!')
        return self.wsgi_app(environ, start_response)


def create_app(with_static=True):
    application = Application()

    # WSGIミドルウェアの設定ポイント
    if with_static:
        application.wsgi_app = SharedDataMiddleware(
            application.wsgi_app,
            {'/favicon.ico': str(pathlib.Path('./favicon.ico'))}
        )
    return application


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    app = create_app()

    # 外部からアクセス可能とするよう、第一引数は 0.0.0.0 を指定 (Flaskと同様)
    # https://qiita.com/tomboyboy/items/122dfdb41188176e45b5
    run_simple('0.0.0.0', 5000, app, use_debugger=True, use_reloader=True)
    # run_simple('127.0.0.1', 5000, a, use_debugger=True, use_reloader=True)

