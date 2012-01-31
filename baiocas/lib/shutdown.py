import signal

from baiocas.lib.namedtuple import namedtuple


# Keep track of whether we've already registered the signal handlers
_signal_handlers_registered = False


# Collection of registered callbacks
_callbacks = []


# Definition of a callback
Callback = namedtuple('Callback', 'function args kwargs')


def _handle_signal(signal, frame):
    for callback in _callbacks:
        callback.function(*callback.args, **callback.kwargs)


def _register_signal_handlers():

    # Make sure we haven't already registered these
    global _signal_handlers_registered
    if _signal_handlers_registered:
        return
    _signal_handlers_registered = True

    # Only handle SIGINT if there isn't already a handler (e.g., PDB)
    if signal.getsignal(signal.SIGINT) == signal.default_int_handler:
        signal.signal(signal.SIGINT, _handle_signal)

    # Handle standard termination
    signal.signal(signal.SIGTERM, _handle_signal)

    # Handle Ctrl+Break on Windows
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, _handle_signal)


def register_callback(function, *args, **kwargs):
    _register_signal_handlers()
    _callbacks.append(Callback(
        function=function,
        args=args,
        kwargs=kwargs
    ))
