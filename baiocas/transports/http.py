import http.cookies
import time
from email.utils import mktime_tz
from email.utils import parsedate_tz

from baiocas.transports.base import Transport
from baiocas.transports.util import is_cookie_expired


class HttpTransport(Transport):

    DEFAULT_HEADERS = {
        'content-type': ['application/json; charset=UTF-8']
    }

    OPTION_HEADERS = 'request_headers'

    def __init__(self, *args, **kwargs):
        super(HttpTransport, self).__init__(*args, **kwargs)
        self._cookies = http.cookies.SimpleCookie()

    def add_header(self, name, value):
        headers = self._options.setdefault(self.OPTION_HEADERS, {})
        headers.setdefault(name.lower(), []).append(value)

    def configure(self, **options):
        if self.OPTION_HEADERS in options:
            headers = dict((name.lower(), values) for name, values
                           in options[self.OPTION_HEADERS].items())
            options[self.OPTION_HEADERS] = headers
        super(HttpTransport, self).configure(**options)

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
        headers.update(self._options.get(self.OPTION_HEADERS, {}))
        cookies = self.get_cookie_headers()
        if cookies:
            headers.setdefault('cookie', []).extend(cookies)
        return headers

    def remove_header(self, name, value):
        headers = self._options.get(self.OPTION_HEADERS, {})
        if name not in headers:
            return False
        del headers[name]
        return True

    def set_cookie(self, name, value, **attrs):
        self._cookies[name] = value
        cookie = self._cookies[name]
        cookie.update(attrs)
        cookie.time_received = time.time()
        self.log.debug('Set cookie %s = %s' % (name, value))
        return cookie

    def set_header(self, name, values):
        if not isinstance(values, (list, tuple)):
            values = [values]
        else:
            values = list(values)
        headers = self._options.setdefault(self.OPTION_HEADERS, {})
        headers[name.lower()] = values

    def update_cookies(self, values, time_received=None):
        cookies = http.cookies.SimpleCookie()
        if isinstance(time_received, (list, tuple)):
            time_received = time_received[0] if time_received else None
        if isinstance(time_received, str):
            time_received = parsedate_tz(time_received)
            if time_received:
                time_received = mktime_tz(time_received)
        if time_received is None:
            time_received = time.time()
        for value in values:
            cookies.load(value)
        for cookie in cookies.values():
            cookie.time_received = time_received
        self._cookies.update(cookies)
        self.log.debug('Updated cookie headers: %s' % values)
