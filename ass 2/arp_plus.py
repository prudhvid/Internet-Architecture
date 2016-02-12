import struct

from pox.lib.packet.packet_base import packet_base

from pox.lib.packet.ipv4 import ipv4

from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.ethernet import ETHER_ANY
from pox.lib.packet.ethernet import ETHER_BROADCAST

from pox.lib.packet.ipv4 import IP_ANY
from pox.lib.packet.ipv4 import IP_BROADCAST

from pox.lib.addresses import IPAddr, EthAddr

from pox.lib.packet.packet_utils import *
from pox.core import core
log = core.getLogger()

class arp_plus (packet_base):
    "ARP/RARP packet struct"

    MIN_LEN = 28

    HW_TYPE_ETHERNET = 1
    PROTO_TYPE_IP    = 0x0800

    # OPCODES
    REQUEST     = 1 # ARP
    REPLY       = 2 # ARP
    REV_REQUEST = 3 # RARP
    REV_REPLY   = 4 # RARP

    def __init__(self, raw=None, prev=None, **kw):
        packet_base.__init__(self)

        self.prev = prev

        self.hwtype     = arp_plus.HW_TYPE_ETHERNET
        self.prototype  = arp_plus.PROTO_TYPE_IP
        self.hwsrc      = ETHER_ANY
        self.hwdst      = ETHER_ANY
        self.hwlen      = 6
        self.opcode     = 0
        self.protolen   = 4
        self.protosrc   = IP_ANY
        self.protodst   = IP_ANY
        self.next       = b''
        self.dpid       = 0

        if raw is not None:
            self.parse(raw)

        self._init(kw)

    def parse (self, raw):
        assert isinstance(raw, bytes)
        self.next = None # In case of unfinished parsing
        self.raw = raw
        dlen = len(raw)
        if dlen < arp_plus.MIN_LEN:
            self.msg('(arp parse) warning IP packet data too short to parse header: data len %u' % dlen)
            return

        (self.hwtype, self.prototype, self.hwlen, self.protolen,self.opcode) =\
        struct.unpack('!HHBBH', raw[:8])

        if self.hwtype != arp_plus.HW_TYPE_ETHERNET:
            self.msg('(arp parse) hw type unknown %u' % self.hwtype)
            return
        if self.hwlen != 6:
            self.msg('(arp parse) unknown hw len %u' % self.hwlen)
            return
        else:
            self.hwsrc = EthAddr(raw[8:14])
            self.hwdst = EthAddr(raw[18:24])
        if self.prototype != arp_plus.PROTO_TYPE_IP:
            self.msg('(arp parse) proto type unknown %u' % self.prototype)
            return
        if self.protolen != 4:
            self.msg('(arp parse) unknown proto len %u' % self.protolen)
            return
        else:
            self.protosrc = IPAddr(struct.unpack('!I',raw[14:18])[0])
            self.protodst = IPAddr(struct.unpack('!I',raw[24:28])[0])

        self.dpid = struct.unpack('!q',raw[28:36])[0]
        self.next = raw[36:]
        self.parsed = True

    def hdr(self, payload):
        buf = struct.pack('!HHBBH', self.hwtype, self.prototype,
            self.hwlen, self.protolen,self.opcode)
        if type(self.hwsrc) == bytes:
            buf += self.hwsrc
        else:
            buf += self.hwsrc.toRaw()
        if type(self.protosrc) is IPAddr:
          buf += struct.pack('!I',self.protosrc.toUnsigned())
        else:
          buf += struct.pack('!I',self.protosrc)
        if type(self.hwdst) == bytes:
            buf += self.hwdst
        else:
            buf += self.hwdst.toRaw()
        if type(self.protodst) is IPAddr:
          buf += struct.pack('!I',self.protodst.toUnsigned())
        else:
          buf += struct.pack('!I',self.protodst)

        buf += struct.pack('!q', self.dpid )
        
        return buf

    def _to_str(self):
        op = str(self.opcode)

        eth_type = None
        # Ethernet
        if hasattr(self.prev, 'type'):
            eth_type = self.prev.type
        # Vlan
        elif hasattr(self.prev, 'eth_type'):
            eth_type = self.prev.eth_type
        else:
            self.err('(arp) unknown datalink type')
            eth_type = ethernet.ARP_TYPE

        if eth_type == ethernet.ARP_TYPE:
            if self.opcode == arp_plus.REQUEST:
                op = "REQUEST"
            elif self.opcode == arp_plus.REPLY:
                op = "REPLY"
        elif eth_type == ethernet.RARP_TYPE:
            if self.opcode == arp_plus.REV_REQUEST:
                op = "REV_REQUEST"
            elif self.opcode == arp_plus.REV_REPLY:
                op = "REV_REPLY"

        s = "[ARP {0} hw:{1} p:{2} {3}>{4} {5}>{6}] dpid={7}".format(op,
                                                  self.hwtype,
                                                  self.prototype,
                                                  EthAddr(self.hwsrc),
                                                  EthAddr(self.hwdst),
                                                  IPAddr(self.protosrc),
                                                  IPAddr(self.protodst),
                                                  self.dpid)
        return s