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

def dpid_to_mac (dpid):
  return EthAddr("%012x" % (dpid & 0xffFFffFFffFF,))

class Tutorial (object):
  """
  A Tutorial object is created for each switch that connects.
  A Connection object for that switch is passed to the __init__ function.
  """
  def __init__ (self, connection):
    # Keep track of the connection to the switch so that we can
    # send it messages!
    self.connection = connection

    # This binds our PacketIn event listener
    connection.addListeners(self)

    self.mac_to_port = {}

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

    # We want to output to all ports -- we do that using the special
    # OFPP_ALL port as the output port.  (We could have also used
    # OFPP_FLOOD.)
    self.resend_packet(packet_in, of.OFPP_ALL)

    # Note that if we didn't get a valid buffer_id, a slightly better
    # implementation would check that we got the full data before
    # sending it (len(packet_in.data) should be == packet_in.total_len)).


  def act_like_switch (self, packet, packet_in):
    """
    Implement switch-like behavior.
    """
    if packet.src not in self.mac_to_port:
      print "Installing flow...",packet.src, "port:",packet.port
    self.mac_to_port[packet.src]=packet.port
    
    # if isinstance(packet.next,arp):
    #   a=packet.next
    #   if a.prototype == arp.PROTO_TYPE_IP:
    #       if a.hwtype == arp.HW_TYPE_ETHERNET:
    #         if a.protosrc != 0:
    #           self.arpTable[a.protosrc] = packet.src

    if isinstance(packet.next,arp) and packet.payload.opcode == arp.REQUEST:  
        a=packet.next
        print self.arpTable
        if a.prototype == arp.PROTO_TYPE_IP:
          if a.hwtype == arp.HW_TYPE_ETHERNET:
            if a.protosrc != 0:
              self.arpTable[a.protosrc] = packet.src

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
                msg.actions.append(of.ofp_action_output(port =
                                                        of.OFPP_IN_PORT))
                msg.in_port = packet.port
                self.connection.send(msg)

              else:
                print 'flood for ARP'
                self.resend_packet(packet_in,of.OFPP_ALL)

    elif packet.dst in self.mac_to_port:
      # Send packet out the associated port
      # self.resend_packet(packet_in , self.mac_to_port[packet.dst])

      # Maybe the log statement should have source/destination/port?
      # if(packet.type==packet.IP_TYPE or (packet.type==packet.ARP_TYPE and 
      #           packet.payload.opcode==arp.REPLY)):
      msg = of.ofp_flow_mod()
      #
      ## Set fields to match received packet
      msg.match.dl_dst=packet.dst
      msg.priority = 42
      # msg.match.dl_type=packet.IP_TYPE
      #
      #< Set other fields of flow_mod (timeouts? buffer_id?) >
      msg.idle_timeout=10000
      msg.hard_timeout=10000
      #< Add an output action, and send -- similar to resend_packet() >
      action=of.ofp_action_output(port=self.mac_to_port[packet.dst])
      msg.actions.append(action)      
      self.connection.send(msg)
      # else:
      #   self.resend_packet(packet_in,of.OFPP_ALL)

    else:
      # Flood the packet out everything but the input port
      self.resend_packet(packet_in, of.OFPP_ALL)

  def addEntryOrFlood(self,packet,packet_in):
    if packet.dst in self.mac_to_port[packet.dpid]:
      # msg = of.ofp_flow_mod()
      # msg.match.dl_dst=packet.dst
      # msg.priority = 42
      # msg.match.dl_type=packet.IP_TYPE

      # msg.idle_timeout=10000
      # msg.hard_timeout=10000
      # #< Add an output action, and send -- similar to resend_packet() >
      # action=of.ofp_action_output(port=self.mac_to_port[packet.dpid][packet.dst])
      # msg.actions.append(action)      
      # self.connection.send(msg)
      self.resend_packet(packet_in,self.mac_to_port[packet.dpid][packet.dst])
    else:
      self.resend_packet(packet_in, of.OFPP_ALL)

  def custom_switch(self,packet,packet_in):
    """
    Implement switch-like behavior.
    """
    self.mac_to_port[packet.dpid][packet.src]=packet.port

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



def launch ():
  """
  Starts the component
  """
  def start_switch (event):
    log.debug("Controlling %s" % (event.connection,))
    Tutorial(event.connection)
    # print dir(event.connection)
  core.openflow.addListenerByName("ConnectionUp", start_switch)
