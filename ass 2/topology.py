#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel,info
from mininet.node import Node
from mininet.node import Controller, RemoteController
from mininet.cli import CLI
from mininet.node import OVSKernelSwitch, UserSwitch

##may be we can use later
# class LinuxRouter( Node ):
#     "A Node with IP forwarding enabled."

#     def config( self, **params ):
#         super( LinuxRouter, self).config( **params )
#         # Enable forwarding on the router
#         self.cmd( 'sysctl net.ipv4.ip_forward=1' )

#     def terminate( self ):
#         self.cmd( 'sysctl net.ipv4.ip_forward=0' )
#         super( LinuxRouter, self ).terminate()

def int2dpid( dpid ):
        try:
            dpid = hex( dpid )[ 2: ]
            dpid = '0' * ( 16 - len( dpid ) ) + dpid
            return dpid
        except IndexError:
            raise Exception( 'Unable to derive default datapath ID - '
                             'please either specify a dpid or use a '
                             'canonical switch name such as s23.' )

class CustomTopo(Topo):

    def build(self, n=2):

        r1=self.addSwitch('r1',dpid=int2dpid(1))
        r2=self.addSwitch('r2',dpid=int2dpid(2))
        r3=self.addSwitch('r3',dpid=int2dpid(3))
        r4=self.addSwitch('r4',dpid=int2dpid(4))

        s1 = self.addSwitch('s1',dpid=int2dpid(10))
        s2 = self.addSwitch('s2',dpid=int2dpid(20))

        self.addLink(r1,r3)
        self.addLink(r1,r2)
        self.addLink(r2,r4)
        self.addLink(r4,r3)

        self.addLink(s1,r1)
        self.addLink(r4,s2)

        h1 = self.addHost('h1', ip="10.0.1.2" ,defaultRoute = "via 10.0.1.1" )
        h2 = self.addHost('h2', ip="10.0.1.3" ,defaultRoute = "via 10.0.1.1" )
        h3 = self.addHost('h3', ip="10.0.3.2" ,defaultRoute = "via 10.0.3.1" )
        h4 = self.addHost('h4', ip="10.0.2.2" ,defaultRoute = "via 10.0.2.1" )
        h5 = self.addHost('h5', ip="10.0.4.2" ,defaultRoute = "via 10.0.4.1" )
        h6 = self.addHost('h6', ip="10.0.4.3" ,defaultRoute = "via 10.0.4.1" )

        self.addLink(h1,s1)
        self.addLink(h2,s1)
        self.addLink(h3,r3)
        self.addLink(h4,r2)
        self.addLink(h5,s2)
        self.addLink(h6,s2)


        # print "Port:",self.port('h1','s1')


topos = { 'custopo': ( lambda: CustomTopo() ) }   


def simpleTest():
    "Create and test a simple network"
    # topo = CustomTopo()
    net = Mininet( controller=lambda a: RemoteController(a, ip='127.0.0.1' ))
    #net = Mininet( controller=Controller )

    info( '*** Adding controller\n' )
    net.addController( 'c0' )
    
    
    
    r1=net.addSwitch('r1',cls=OVSKernelSwitch,dpid=int2dpid(1))
    r2=net.addSwitch('r2',dpid=int2dpid(2))
    r3=net.addSwitch('r3',dpid=int2dpid(3))
    r4=net.addSwitch('r4',dpid=int2dpid(4))

    s1 = net.addSwitch('s1',dpid=int2dpid(10))
    s2 = net.addSwitch('s2',dpid=int2dpid(20))

    net.addLink(r1,r3)
    net.addLink(r1,r2)
    net.addLink(r2,r4)
    net.addLink(r4,r3)

    net.addLink(s1,r1)
    net.addLink(r4,s2)

    h1 = net.addHost('h1', ip="10.0.1.2" ,defaultRoute = "via 10.0.1.1" )
    h2 = net.addHost('h2', ip="10.0.1.3" ,defaultRoute = "via 10.0.1.1" )
    h3 = net.addHost('h3', ip="10.0.3.2" ,defaultRoute = "via 10.0.3.1" )
    h4 = net.addHost('h4', ip="10.0.2.2" ,defaultRoute = "via 10.0.2.1" )
    h5 = net.addHost('h5', ip="10.0.4.2" ,defaultRoute = "via 10.0.4.1" )
    h6 = net.addHost('h6', ip="10.0.4.3" ,defaultRoute = "via 10.0.4.1" )

    net.addLink(h1,s1)
    net.addLink(h2,s1)
    net.addLink(h3,r3)
    net.addLink(h4,r2)
    net.addLink(h5,s2)
    net.addLink(h6,s2)

    # net.pingAll()
    # net.stop()

    net.start()
    CLI(net)

if __name__ == '__main__':
    # Tell mininet to print useful information
    setLogLevel('info')
    simpleTest()

