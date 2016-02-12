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

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pprint import pprint
log = core.getLogger()
import pox.lib.packet as pkt
from pox.lib.packet.arp import arp
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
    # This binds our PacketIn event listener
    connection.addListeners(self)

    self.mac_to_port = {}

    for po in self.connection.features.ports:
      self.mac_to_port[EthAddr(po.hw_addr)]=po.port_no

    self.arpTable = {}

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
    self.resend_packet(packet_in, of.OFPP_ALL)

    


  def is_router(self):
    return self.dpid<10

  def addEntryOrFlood(self,packet,packet_in):
    if packet.dst in self.mac_to_port[packet.dpid]:
      self.resend_packet(packet_in,self.mac_to_port[packet.dpid][packet.dst])
    else:
      self.resend_packet(packet_in, of.OFPP_ALL)

  def custom_switch(self,packet,packet_in):
    """
    Implement switch-like behavior.
    """
    self.mac_to_port[packet.dpid][packet.src]=packet.port

    
    # if self.is_router():
    #   self.ip=IPAddr("10.0"+str(self.dpid)+".1/24")

    if self.is_router():
      print "next=",packet.next
      if(isinstance(packet.next,arp_plus)):
        a=packet.next
        if a.dpid == self.dpid:
          log.debug("dpid= {0}".format(self.dpid,))
          return
        else:
          #flood arp_plus packets
          log.debug("flodding arp")
          self.act_like_hub(packet,packet_in)
      elif(isinstance(packet.next,arp)):
        if(packet.payload.opcode==arp.REQUEST):
          a=packet.next
          r = arp_plus()
          r.hwtype = a.hwtype
          r.prototype = a.prototype
          r.hwlen = a.hwlen
          r.protolen = a.protolen
          r.opcode = arp.REQUEST
          r.hwdst = a.hwdst
          r.protodst = a.protodst
          r.protosrc = a.protosrc
          r.hwsrc = a.hwsrc
          r.dpid = self.dpid
          log.debug("Transmitting ARP+")
          e = ethernet(type=packet.type, src=self.mac,
                         dst=a.hwsrc)
          e.set_payload(r)
          msg = of.ofp_packet_out()
          msg.data = e.pack()
          msg.actions.append(of.ofp_action_output(port = of.OFPP_IN_PORT))
          msg.in_port = packet.port
          self.connection.send(msg)

    if isinstance(packet.next,arp):
      print self.arpTable
      self.arpTable[packet.next.protosrc]=packet.src
      a=packet.next

      if packet.payload.opcode==arp.REQUEST:
        if a.protodst in self.arpTable:
          r = arp()
          r.hwtype = a.hwtype
          r.prototype = a.prototype
          r.hwlen = a.hwlen
          r.protolen = a.protolen
          r.opcode = arp.REPLY
          r.hwdst = a.hwsrc
          r.protodst = a.protosrc
          r.protosrc = a.protodst
          r.hwsrc = self.arpTable[a.protodst]
          e = ethernet(type=packet.type, src=dpid_to_mac(packet.dpid),
                                 dst=a.hwsrc)
          e.set_payload(r)
          log.debug("%i %i answering ARP for %s" % (packet.dpid, packet.port,
           str(r.protosrc)))
          msg = of.ofp_packet_out()
          msg.data = e.pack()
          msg.actions.append(of.ofp_action_output(port=of.OFPP_IN_PORT))
          msg.in_port = packet.port
          self.connection.send(msg)
        else:
          self.resend_packet(packet_in,of.OFPP_ALL)

      else:
        self.addEntryOrFlood(packet,packet_in)

    else:
      self.addEntryOrFlood(packet,packet_in)



  

  def _handle_PacketIn (self, event):
    """
    Handles packet in messages from the switch.
    """
    # log.debug(event.parsed)
    # print (event.parsed.__dict__)
    packet = event.parsed # This is the parsed packet data.
    # print pkt.ETHERNET.ethernet.getNameForType(packet.type)
    print packet.next
    packet.dpid=event.dpid
    # if packet.type==packet.ARP_TYPE:
    #   print packet.payload.opcode
    packet.port=event.port
    
    if not event.dpid in self.mac_to_port:
      self.mac_to_port[event.dpid]={}

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
    log.debug("Controlling %s %s" % (event.connection,event.dpid))
    
    Tutorial(event.connection,event.dpid)
    # print dir(event.connection)
  core.openflow.addListenerByName("ConnectionUp", start_switch)
