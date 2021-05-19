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
        for name, value in self.__dict__.items():
            if other.__dict__.get(name) != value:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)


class ActionError(BayeuxError):
    """Raised when an invalid advice action is encountered."""

    def __init__(self, action):
        message = 'Unrecognized advice action "%s"' % action
        super(ActionError, self).__init__(message)
        self.action = action


class BatchError(BayeuxError):
    """Raised when batches are not started/stopped in the right order."""


class CommunicationError(BayeuxError):
    """Raised when a communication error occurs with a transport."""

    def __init__(self, transport_exception):
        message = 'Communication error: %s' % transport_exception
        super(CommunicationError, self).__init__(message)
        self.transport_exception = transport_exception


class ConnectionStringError(BayeuxError):
    """Raised when an invalid connection string is encountered."""

    def __init__(self, transport, value):
        message = 'Invalid connection string, "%s", for transport %s' % (value, transport)
        super(ConnectionStringError, self).__init__(message)
        self.transport = transport
        self.value = value


class ServerError(BayeuxError):
    """Raised when a server responds with a non-successful status."""

    def __init__(self, code):
        message = 'Server responded with error %s' % code
        super(ServerError, self).__init__(message)
        self.code = code


class StatusError(BayeuxError):
    """Raised when the Bayeux client has an invalid status for an operation."""

    def __init__(self, status):
        message = 'Client status of "%s" is not valid for this operation' % status
        super(StatusError, self).__init__(message)
        self.status = status


class TimeoutError(BayeuxError):
    """Raised when the Bayeux client times out during an operation."""


class TransportNegotiationError(BayeuxError):
    """Raised when the Bayeux client and server could not agree on a transport."""

    def __init__(self, client_types, server_types):
        message = 'Could not negotiate transport with server; client: %s; server: %s' % \
            (', '.join(client_types), ', '.join(server_types))
        super(TransportNegotiationError, self).__init__(message)
        self.client_types = client_types
        self.server_types = server_types
