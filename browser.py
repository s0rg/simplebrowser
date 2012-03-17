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

try:
    from lxml.html import document_fromstring
except ImportError:
    document_fromstring = lambda a: a


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
        uri = '{}?{}'.format(parsed.path, parsed.query) if parsed.query \
                                                        else parsed.path or '/'
        return uri

    def __build_headers(self):
        if self._head_changed:
            self._head_cache = []
            for h in self._headers:
                self._head_cache.append(h)
            cs = self._cookies.output(attrs=[], header='', sep=';').strip()
            if cs:
                self._head_cache.append(('Cookie', cs))
            self._head_changed = False
        return self._head_cache

    def __parse_headers(self, headers):
        head_dict = {}
        for item, value in headers:
            item = item.lower()
            if item in ('set-cookie', 'set-cookie2'):
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
        self._headers.append((name, value))

    def add_cookie(self, name, value):
        self._head_changed = True
        self._cookies[name] = value

    def request(self, req, url, data=None):
        if isinstance(data, dict):
            data = urlencode(data)

        uri = self.__prepare_url(url)
        self._conn.putrequest(req, uri)

        headers = self.__build_headers()
        for hi in headers:
            self._conn.putheader(*hi)
        self._conn.endheaders(data)

        resp = self._conn.getresponse()
        headers = self.__parse_headers(resp.getheaders())
        resp_body = resp.read()

        if resp.status == client.OK:
            return (client.OK, document_fromstring(resp_body))
        elif resp.status in (client.MOVED_PERMANENTLY, client.FOUND):
            return self.request(req, headers['location'], data)
        else:
            return (resp.status, resp.reason)

    def get(self, url):
        return self.request('GET', url)

    def post(self, url, data):
        return self.request('POST', url, data)


if __name__ == '__main__':
    sb = SimpleBrowser()
    sb.get('http://ya.ru/')
    res, doc = sb.get('http://pogoda.yandex.ru/moscow/')
    if res == client.OK:
        for div in doc.cssselect("div.b-forecast__tday"):
            print (div.text)
    else:
        print ('OH SHI~')

