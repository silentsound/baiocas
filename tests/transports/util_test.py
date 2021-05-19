import time
from email.utils import formatdate
from http.cookies import Morsel
from unittest import TestCase

from baiocas.transports.util import is_cookie_expired


class TestExpiredCookie(TestCase):

    def setUp(self):
        self.cookie = Morsel()
        self.cookie.set('foo', 'bar', 'bar')
        self.cookie.time_received = time.time() - 1

    def test_no_expiration_information(self):
        assert not is_cookie_expired(self.cookie)

    def test_valid_max_age(self):
        self.cookie['max-age'] = '86400'
        assert not is_cookie_expired(self.cookie)

    def test_valid_max_age_missing_time_received(self):
        self.cookie['max-age'] = '1'
        del self.cookie.time_received
        assert not is_cookie_expired(self.cookie)

    def test_expired_max_age(self):
        self.cookie['max-age'] = '1'
        assert is_cookie_expired(self.cookie)
        self.cookie['max-age'] = '0'
        assert is_cookie_expired(self.cookie)

    def test_expired_max_age_missing_time_received(self):
        self.cookie['max-age'] = '0'
        del self.cookie.time_received
        assert is_cookie_expired(self.cookie)
        self.cookie['max-age'] = '1'
        assert not is_cookie_expired(self.cookie)

    def test_invalid_max_age(self):
        self.cookie['max-age'] = 'invalid'
        assert not is_cookie_expired(self.cookie)

    def test_valid_expires(self):
        self.cookie['expires'] = formatdate(time.time() + 86400, localtime=True)
        assert not is_cookie_expired(self.cookie)

    def test_expired_expires(self):
        self.cookie['expires'] = formatdate(usegmt=True)
        assert is_cookie_expired(self.cookie)

    def test_invalid_expires(self):
        self.cookie['expires'] = 'invalid'
        assert not is_cookie_expired(self.cookie)

    def test_valid_max_age_and_expired_expires(self):
        self.cookie['max-age'] = '86400'
        self.cookie['expires'] = formatdate(usegmt=True)
        assert not is_cookie_expired(self.cookie)

    def test_expired_max_age_and_valid_expires(self):
        self.cookie['max-age'] = '1'
        self.cookie['expires'] = formatdate(time.time() + 86400, localtime=True)
        assert is_cookie_expired(self.cookie)
