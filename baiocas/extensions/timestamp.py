from email.utils import formatdate

from baiocas.extensions.base import Extension


class TimestampExtension(Extension):

    def send(self, message):
        message.timestamp = formatdate(usegmt=True)
        return message
