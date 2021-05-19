

class ClientStatus(object):

    # State assumed after the handshake when the connection is broken
    UNCONNECTED = 'unconnected'

    # State assumed when the handshake is being sent
    HANDSHAKING = 'handshaking'

    # State assumed when a first handshake failed and the handshake is retried,
    # or when the Bayeux server requests a re-handshake
    REHANDSHAKING = 'rehandshaking'

    # State assumed when the connect is being sent for the first time
    CONNECTING = 'connecting'

    # State assumed when the client is connected to the Bayeux server
    CONNECTED = 'connected'

    # State assumed when the disconnect is being sent
    DISCONNECTING = 'disconnecting'

    # State assumed before the handshake and when the disconnect is completed
    DISCONNECTED = 'disconnected'

    @classmethod
    def is_disconnected(cls, status):
        return status in (cls.DISCONNECTING, cls.DISCONNECTED)

    @classmethod
    def is_handshaking(cls, status):
        return status in (cls.HANDSHAKING, cls.REHANDSHAKING)
