#-*- coding: utf8 -*-

import platform

version = platform.python_version_tuple()

if version[0] == '3':
    from http import cookies, client
    from urllib.parse import urlencode, urlsplit
elif version[0] == '2':
    import httplib as client
    import Cookie as cookies
    from urlparse import urlsplit
    from urllib import urlencode
else:
    raise ImportError('Bad python version: ', version)


class Response(object):
    __slots__ = ['code' ,'headers', 'body']

    def __init__(self, code, headers, body=None):
        self.code = code
        self.headers = headers
        self.body = body


class SimpleBrowser(object):
    def __init__(self, headers=None, timeout=10, debug=0):
        self._cookies = cookies.SimpleCookie()
        self._host, self._conn = None, None
        self._timeout = timeout
        self._debug = debug
        self._headers = headers if (headers is not None) \
                                else [('User-Agent', 'SimpleBrowser/0.2')]
        self._headers.append(('Connection', 'keep-alive'))
        self._head_cache = None
        self._head_changed = True

    def __ensure_connection(self, host, port, scheme):
        if self._host == host:
            return

        if self._conn is not None:
            self._conn.close()

        if scheme == 'http':
            self._conn = client.HTTPConnection(host, port, timeout=self._timeout)
        elif scheme == 'https':
            self._conn = client.HTTPSConnection(host, port, timeout=self._timeout)
        else:
            raise ValueError('Unknown scheme: %s' % scheme)
        self._host = host
        self._conn.set_debuglevel(self._debug)

    def __prepare_url(self, url):
        parsed = urlsplit(url, scheme='http')
        host = parsed.netloc if parsed.netloc \
                             else self._host
        scheme = parsed.scheme.lower()
        if parsed.port:
            port = parsed.port
        elif scheme == 'http':
            port = client.HTTP_PORT
        elif scheme == 'https':
            port = client.HTTPS_PORT

        self.__ensure_connection(host, port, scheme)

        if parsed.query:
           uri = '{}?{}'.format(parsed.path, parsed.query)
        else:
           uri = parsed.path or '/'

        return uri

    def __build_headers(self):
        if self._head_changed:
            self._head_cache = [h for h in self._headers]
            cs = self._cookies.output(attrs=[], header='', sep=';').strip()
            if cs:
                self._head_cache.append(('Cookie', cs))
            self._head_changed = False
        return self._head_cache

    def __parse_headers(self, headers):
        head_dict = {}
        for item, value in headers:
            item = item.lower()
            if item.startswith('set-cookie'):
                self._cookies.load(value)
                self._head_changed = True
            else:
                head_dict[item] = value
        return head_dict

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        self._host = None

    def add_header(self, name, value):
        self._head_changed = True
        for n, h_name, _ in enumerate(self._headers[:]):
            if h_name == name:
                self._headers.insert(n, (name, value))
                return
        self._headers.append((name, value))

    def add_cookie(self, name, value):
        self._head_changed = True
        self._cookies[name] = value

    def request(self, req, url, data=None, allow_redirect=True):
        uri = self.__prepare_url(url)
        self._conn.putrequest(req, uri)

        headers = self.__build_headers()
        for hi in headers:
            self._conn.putheader(*hi)
        if req == 'POST' and data is not None:
            self._conn.putheader('Content-Type', 'application/x-www-form-urlencoded')
            self._conn.putheader('Content-Length', len(data))
        self._conn.endheaders(data)

        resp = self._conn.getresponse()
        resp_headers = resp.getheaders()
        resp_body = resp.read()

        headers = self.__parse_headers(resp_headers)

        if resp.status == client.OK:
            return Response(client.OK, resp_headers, resp_body)
        elif resp.status in (client.MOVED_PERMANENTLY, client.FOUND):
            if allow_redirect:
                return self.request(req, headers['location'], data)
            else:
                return Response(resp.status, headers)
        else:
            return Response(resp.status, resp_headers, resp.reason)

    def get(self, url, params=None, allow_redirect=True):
        if params is not None:
            if isinstance(params, dict):
                params = urlencode(params)
            url = '{}?{}'.format(url, params)
        return self.request('GET', url, allow_redirect=allow_redirect)

    def post(self, url, data, allow_redirect=True):
        if isinstance(data, dict):
            data = urlencode(data)
        return self.request('POST', url, data=data,
                            allow_redirect=allow_redirect)


if __name__ == '__main__':
    # FIXME: Example too old!
    sb = SimpleBrowser()
    res, doc = sb.get('http://pogoda.yandex.ru/moscow/')
    if res == client.OK:
        print doc
    else:
        print ('OH SHI~')

