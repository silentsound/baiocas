from unittest import TestCase

from baiocas import errors


class TestBayeuxError(TestCase):

    # The class of the error to test
    ERROR_CLASS = errors.BayeuxError

    # Arguments to pass when creating an instance of the error
    ARGS = ()

    # The expected string representation of the class
    EXPECTED_STRING = ''

    def test_error(self):
        exception = self.ERROR_CLASS(*self.ARGS)
        assert isinstance(exception, Exception)
        assert isinstance(exception, errors.BayeuxError)
        assert str(exception) == self.EXPECTED_STRING

    def test_equality(self):
        exception = self.ERROR_CLASS(*self.ARGS)
        other_exception = self.ERROR_CLASS(*self.ARGS)
        assert exception == other_exception
        other_exception = Exception()
        assert exception != other_exception
        other_exception = self.ERROR_CLASS(*self.ARGS)
        assert exception == other_exception
        message = str(other_exception)
        other_exception.__str__ = lambda: message
        other_exception.args = ('invalid message',)
        assert exception != other_exception
        if len(self.ARGS) > 0:
            other_exception = self.ERROR_CLASS(*self.ARGS)
            assert exception == other_exception
            first_key = list(other_exception.__dict__.keys())[0]
            other_exception.__dict__[first_key] = 'invalid'
            assert exception != other_exception


class TestActionError(TestBayeuxError):
    
    # The class of the error to test
    ERROR_CLASS = errors.ActionError

    # Arguments to pass when creating an instance of the error
    ARGS = ('bad',)

    # The expected string representation of the class
    EXPECTED_STRING = 'Unrecognized advice action "bad"'


class TestBatchError(TestBayeuxError):
    
    # The class of the error to test
    ERROR_CLASS = errors.BatchError


class TestCommunicationError(TestBayeuxError):
    
    # The class of the error to test
    ERROR_CLASS = errors.CommunicationError

    # Arguments to pass when creating an instance of the error
    ARGS = (Exception('Failed connection'),)

    # The expected string representation of the class
    EXPECTED_STRING = 'Communication error: Failed connection'


class TestConnectionStringError(TestBayeuxError):
    
    # The class of the error to test
    ERROR_CLASS = errors.ConnectionStringError

    # Arguments to pass when creating an instance of the error
    ARGS = ('long-polling', 'http://www.example.com')

    # The expected string representation of the class
    EXPECTED_STRING = 'Invalid connection string, "http://www.example.com", for transport long-polling'


class TestServerError(TestBayeuxError):
    
    # The class of the error to test
    ERROR_CLASS = errors.ServerError

    # Arguments to pass when creating an instance of the error
    ARGS = (402,)

    # The expected string representation of the class
    EXPECTED_STRING = 'Server responded with error 402'


class TestStatusError(TestBayeuxError):
    
    # The class of the error to test
    ERROR_CLASS = errors.StatusError

    # Arguments to pass when creating an instance of the error
    ARGS = ('handshaking',)

    # The expected string representation of the class
    EXPECTED_STRING = 'Client status of "handshaking" is not valid for this operation'


class TestTimeoutError(TestBayeuxError):
    
    # The class of the error to test
    ERROR_CLASS = errors.TimeoutError


class TestTransportNegotiationError(TestBayeuxError):
    
    # The class of the error to test
    ERROR_CLASS = errors.TransportNegotiationError

    # Arguments to pass when creating an instance of the error
    ARGS = (['long-polling', 'callback-polling'], ['iframe', 'flash'])

    # The expected string representation of the class
    EXPECTED_STRING = 'Could not negotiate transport with server; ' \
        'client: long-polling, callback-polling; server: iframe, flash'
