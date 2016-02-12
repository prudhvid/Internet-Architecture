# Copyright 2012 James McCauley
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This component is for use with the OpenFlow tutorial.

It acts as a simple hub, but can be modified to act like an L2
learning switch.

It's roughly similar to the one Brandon Heller did for NOX.
"""
import struct
from pox.core import core
import pox.openflow.libopenflow_01 as of
from pprint import pprint
log = core.getLogger()
import pox.lib.packet as pkt
from pox.lib.packet.arp import arp
from pox.lib.packet.ipv4 import ipv4
from pox.lib.packet.icmp import unreach,icmp
from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST
from pox.lib.addresses import IPAddr, EthAddr
from arp_plus import arp_plus
from pox.openflow.discovery import Discovery

def dpid_to_mac (dpid):
  return EthAddr("%012x" % (dpid & 0xffFFffFFffFF,))

class Tutorial (object):
  """
  A Tutorial object is created for each switch that connects.
  A Connection object for that switch is passed to the __init__ function.
  """
  def __init__ (self, connection,dpid):
    # Keep track of the connection to the switch so that we can
    # send it messages!
    self.connection = connection
    self.dpid = dpid
    self.mac = EthAddr(dpid_to_mac(dpid))
    self.routeTable = {}
    # This binds our PacketIn event listener
    connection.addListeners(self)

    if self.is_router():
      # print "10.0.{0}.0/24".format(self.dpid)
      self.ip=IPAddr("10.0.{0}.1".format(self.dpid))
      self.network=IPAddr("10.0.{0}.0".format(self.dpid))

    self.mac_to_port = {}

    for po in self.connection.features.ports:
      self.mac_to_port[po.hw_addr]=po.port_no

    self.build_table()

    self.arpTable = {}

    self.arpBuffer = {}

  def build_table(self):
    if self.is_router():
      with open('table_r{0}'.format(self.dpid)) as f:
        rows = f.readlines()
        for row in rows:
          cols=row.split(',')
          self.routeTable[ IPAddr(cols[0]) ]=int(cols[-1])


  def resend_packet (self, packet_in, out_port):
    """
    Instructs the switch to resend a packet that it had sent to us.
    "packet_in" is the ofp_packet_in object the switch had sent to the
    controller due to a table-miss.
    """
    msg = of.ofp_packet_out()
    msg.data = packet_in

    # Add an action to send to the specified port
    action = of.ofp_action_output(port = out_port)
    msg.actions.append(action)

    # Send message to switch
    self.connection.send(msg)


  def act_like_hub (self, packet, packet_in):
    """
    Implement hub-like behavior -- send all packets to all ports besides
    the input port.
    """
    self.resend_packet(packet_in, of.OFPP_FLOOD)

    


  def is_router(self):
    return self.dpid<10

  def addEntryOrFlood(self,packet,packet_in):
    if packet.dst in self.mac_to_port:
      self.resend_packet(packet_in,self.mac_to_port[packet.dst])
    else:
      self.resend_packet(packet_in, of.OFPP_FLOOD)

  def custom_switch(self,packet,packet_in):
    """
    Implement switch-like behavior.
    """
    self.mac_to_port[packet.src]=packet.port

    ip=packet.find('ipv4')

    if self.is_router():
      if isinstance(packet.next,arp):
        a=packet.next
        if packet.payload.opcode==arp.REQUEST:
          if not a.protosrc.inNetwork(self.network,netmask=24):
            log.debug("dropping ARP request from separate subnet")

          elif not a.protodst.inNetwork(self.network,netmask=24):
            r = arp()
            r.hwtype = a.hwtype
            r.prototype = a.prototype
            r.hwlen = a.hwlen
            r.protolen = a.protolen
            r.opcode = arp.REPLY
            r.hwdst = a.hwsrc
            r.protodst = a.protosrc
            r.protosrc = a.protodst
            r.hwsrc = self.mac
            e = ethernet(type=packet.type, src=dpid_to_mac(self.dpid),
                           dst=a.hwsrc)
            e.set_payload(r)
            log.debug("ARP request to different network replying my IP")
            msg = of.ofp_packet_out()
            msg.data = e.pack()
            msg.actions.append(of.ofp_action_output(port = of.OFPP_IN_PORT))
            msg.in_port = packet.port
            self.connection.send(msg)
          else:
            log.debug("ARP Request from same network dropping packet")

        elif packet.payload.opcode==arp.REPLY:
          log.debug("arp reply arrived with %s > %s and my ip=%s"%
            (a.protosrc,a.protodst,self.ip))
          # if a.protodst == self.ip:
            ##send all waiting packets to that mac address through the port
          for waiting_packet in self.arpBuffer[a.protosrc]:

            e = ethernet(type=ethernet.IP_TYPE, 
                      src=dpid_to_mac(self.dpid),
                      dst=a.hwsrc)

            e.set_payload(waiting_packet.payload)
            log.debug("send packet  ")
            msg = of.ofp_packet_out()
            msg.data = e.pack()
            msg.actions.append(of.ofp_action_output(port = of.OFPP_IN_PORT ))
            msg.in_port = packet.port
            self.connection.send(msg)

            # self.resend_packet(waiting_packet,of.OFPP_IN_PORT)
          self.arpBuffer[a.protosrc]=[]

      elif ip is not None:

        if ip.csum == ip.checksum() and ip.iplen >= ipv4.MIN_LEN :
          print 'correct packet with ttl ',ip.ttl
        else:
          print 'Garbled packet'
          return

        ip.ttl-=1
        ip.csum=ip.checksum()


        if(ip.ttl==0):
          print 'TTL 0 throwing packet'
          return


        if ip.dstip not in self.routeTable:
          #send icmp unreachable
          # print self.routeTable
          log.debug("destination unreachable %s",(ip.dstip,))

          ##ICMP packet
          # Make the ping reply
          icm = icmp()
          icm.type=3
          icm.code=0
          d = packet.next.pack()
          d = d[:packet.next.hl * 4]
          d = struct.pack("!HH", 0,0) + d
          icm.payload = d
          # icmp.type = pkt.TYPE_DEST_UNREACH

          # Make the IP packet around it
          ipp = pkt.ipv4()
          ipp.protocol = ipp.ICMP_PROTOCOL
          ipp.srcip = self.ip
          ipp.dstip = ip.srcip

          # Ethernet around that...
          e = pkt.ethernet()
          e.src = self.mac
          e.dst = packet.src
          e.type = e.IP_TYPE

          # Hook them up...
          ipp.set_payload(icm)
          e.set_payload(ipp)

          # Send it back to the input port
          msg = of.ofp_packet_out()
          msg.actions.append(of.ofp_action_output(port = of.OFPP_IN_PORT))
          msg.data = e.pack()
          msg.in_port = packet.port
          self.connection.send(msg)

        else:
          dpid = self.routeTable[ip.dstip]

          if dpid==50:
            #host ip send ARP
            if not ip.dstip in self.arpBuffer:
              self.arpBuffer[ip.dstip]=[]

            self.arpBuffer[ip.dstip].append(packet)

            r = arp()
            r.hwsrc = self.mac
            r.hwdst = ETHER_BROADCAST
            r.opcode = arp.REQUEST
            r.protodst = ip.dstip
            r.protosrc = self.ip
            
            e = ethernet(type=ethernet.ARP_TYPE, 
                      src=dpid_to_mac(self.dpid),
                      dst=ETHER_BROADCAST)


            e.set_payload(r)
            log.debug("ARP request to find host ")
            msg = of.ofp_packet_out()
            msg.data = e.pack()
            msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD ))
            msg.in_port = packet.port
            self.connection.send(msg)


          else:
            # print self.mac,self.mac_to_port
            if dpid_to_mac(dpid) in self.mac_to_port:
              self.resend_packet(packet.pack(),
                self.mac_to_port[ dpid_to_mac(dpid) ])
            else:
              self.act_like_hub(packet, packet_in)

    else:
      self.act_like_hub(packet,packet_in)

    

   

  

  def _handle_PacketIn (self, event):
    """
    Handles packet in messages from the switch.
    """
    # log.debug(event.parsed)
    # print (event.parsed.__dict__)
    packet = event.parsed # This is the parsed packet data.
    # print pkt.ETHERNET.ethernet.getNameForType(packet.type)
    print packet.next, event.dpid
    packet.dpid=event.dpid
    # if packet.type==packet.ARP_TYPE:
    #   print packet.payload.opcode
    packet.port=event.port
    
    

    if not packet.parsed:
      log.warning("Ignoring incomplete packet")
      return

    packet_in = event.ofp # The actual ofp_packet_in message.

    # Comment out the following line and uncomment the one after
    # when starting the exercise.
    # self.act_like_hub(packet, packet_in)
    self.custom_switch(packet, packet_in)

  def _handle_LinkEvent (self, event):
    print 'LINK Event'
  

def launch ():
  """
  Starts the component
  """
  def start_switch (event):

    # print event.connection.features.ports,type(event.connection.features.ports[0].hw_addr)
    log.debug("Controlling %s %s" % (event.connection,event.dpid))
    
    Tutorial(event.connection,event.dpid)
    # print dir(event.connection)
  core.openflow.addListenerByName("ConnectionUp", start_switch)

  import pox.openflow.spanning_tree
  pox.openflow.spanning_tree.launch()