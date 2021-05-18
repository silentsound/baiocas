from __future__ import absolute_import
from __future__ import unicode_literals

import time
from email.utils import mktime_tz
from email.utils import parsedate_tz


def is_cookie_expired(cookie):
    value = None
    if cookie['max-age']:
        value = cookie['max-age']
    elif cookie['expires']:
        value = cookie['expires']
    if not value:
        return False
    if value.isdigit():
        time_received = getattr(cookie, 'time_received', time.time())
        expires = time_received + int(value)
    else:
        expires = parsedate_tz(value)
        if expires:
            expires = mktime_tz(expires)
    if expires and expires <= time.time():
        return True
    return False
