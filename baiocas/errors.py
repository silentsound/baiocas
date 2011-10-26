"""
Exceptions used with Baiocas.

All exceptions inherit from :class:`.BayeuxError`. Exceptions not inheriting
from this class are not raised directly by Baiocas.
"""

class BayeuxError(Exception):
    """Generic base error class for Baiocas."""

    def __eq__(self, other):
        if not isinstance(other, self.__class__) or \
            str(other) != str(self) or \
            other.args != self.args:
            return False
        for name, value in self.__dict__.iteritems():
            if other.__dict__.get(name) != value:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)


class ActionError(BayeuxError):
    """Raised when an invalid advice action is encountered."""

    def __init__(self, action):
        super(ActionError, self).__init__()
        self.action = action

    def __str__(self):
        return 'Unrecognized advice action "%s"' % self.action


class BatchError(BayeuxError):
    """Raised when batches are not started/stopped in the right order."""


class CommunicationError(BayeuxError):
    """Raised when a communication error occurs with a transport."""

    def __init__(self, transport_exception):
        self.transport_exception = transport_exception

    def __str__(self):
        return 'Communication error: %s' % self.transport_exception


class ConnectionStringError(BayeuxError):
    """Raised when an invalid connection string is encountered."""

    def __init__(self, transport, value):
        super(ConnectionStringError, self).__init__()
        self.transport = transport
        self.value = value

    def __str__(self):
        return 'Invalid connection string, "%s", for transport %s' % \
            (self.value, self.transport)


class ServerError(BayeuxError):
    """Raised when a server responds with a non-successful status."""

    def __init__(self, code, description):
        self.code = code
        self.description = description

    def __str__(self):
        return 'Server responded with error "%s: %s"' % (self.code, self.description)


class StatusError(BayeuxError):
    """Raised when the Bayeux client has an invalid status for an operation."""

    def __init__(self, status):
        super(StatusError, self).__init__()
        self.status = status

    def __str__(self):
        return 'Client status of "%s" is not valid for this operation' % self.status


class TimeoutError(BayeuxError):
    """Raised when the Bayeux client times out during an operation."""


class TransportNegotiationError(BayeuxError):
    """Raised when the Bayeux client and server could not agree on a transport."""

    def __init__(self, client_types, server_types):
        super(TransportNegotiationError, self).__init__()
        self.client_types = client_types
        self.server_types = server_types

    def __str__(self):
        return 'Could not negotiate transport with server; client: %s; server: %s' % \
            (', '.join(self.client_types), ', '.join(self.server_types))
