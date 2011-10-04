import Cookie

from base import Transport
from util import is_cookie_expired


class HttpTransport(Transport):

    DEFAULT_HEADERS = {
        'Content-Type': ['application/json;charset=UTF-8']
    }

    OPTION_HEADERS = 'request_headers'

    def __init__(self, *args, **kwargs):
        super(HttpTransport, self).__init__(*args, **kwargs)
        self._cookies = Cookie.SimpleCookie()

    def get_cookie(self, name):
        self.log.debug('Getting cookie with name "%s"' % name)
        return self._cookies.get(name)

    def get_cookie_headers(self, include_expired=False):
        cookies = []
        for key, cookie in sorted(self._cookies.items()):
            if include_expired or not is_cookie_expired(cookie):
                cookies.append(cookie.OutputString(attrs=[]))
        return cookies

    def get_headers(self):
        headers = self.DEFAULT_HEADERS.copy()
        headers.update(self.options.get(self.OPTION_HEADERS, {}))
        cookies = self.get_cookie_headers()
        if cookies:
            self.log.debug('Appending cookie header: %s' % cookies)
            headers.setdefault('Cookie', []).extend(cookies)
        return headers

    def set_cookie(self, name, value, **attrs):
        self._cookies[name] = value
        cookie = self._cookies[name]
        cookie.update(attrs)
        self.log.debug('Set cookie "%s" = "%s"' % (name, value))
        return cookie

    def update_cookies(self, values):
        for value in values:
            self._cookies.load(value)
        self.log.debug('Updated cookie headers: %s' % values)
