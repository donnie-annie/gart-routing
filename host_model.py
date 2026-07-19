"""Host data model shared by controller events and server messages."""

class Host(object):
    def __init__(self, mac, port, ipv4):
        super(Host, self).__init__()
        self.port = port
        self.mac = mac
        self.ipv4 = ipv4

    def to_dict(self):
        d = {
            'mac': self.mac,
            'ipv4': self.ipv4,
            'port': self.port.to_dict()
        }
        return d

    def __eq__(self, host):
        return self.mac == host.mac and self.port == host.port

    def __str__(self):
        msg = 'Host<mac=%s, port=%s,' % (self.mac, str(self.port))
        msg += ','.join(self.ipv4)
        msg += '>'
        return msg
