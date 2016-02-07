#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.node import Node


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



class CustomTopo(Topo):

    def build(self, n=2):
        

        # r1 = self.addNode( 'r1', cls=LinuxRouter, ip=defaultIP )
        # r2 = self.addNode( 'r2', cls=LinuxRouter, ip=defaultIP )
        # r2 = self.addNode( 'r3', cls=LinuxRouter, ip=defaultIP )
        # r4 = self.addNode( 'r4', cls=LinuxRouter, ip=defaultIP )

        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        r1=self.addHost('r1',ip="10.0.1.1")
        r2=self.addHost('r2',ip="10.0.2.1")
        r3=self.addHost('r3',ip="10.0.3.1")
        r4=self.addHost('r4',ip="10.0.4.1")

        self.addLink(r1,r3)
        self.addLink(r1,r2)
        self.addLink(r2,r4)
        self.addLink(r4,r3)

        self.addLink(s1,r1)
        self.addLink(r4,s2)

        h1 = self.addHost('h1', ip="10.0.1.2" )
        h2 = self.addHost('h2', ip="10.0.1.3" )
        h3 = self.addHost('h3', ip="10.0.3.2" )
        h4 = self.addHost('h4', ip="10.0.2.2" )
        h5 = self.addHost('h5', ip="10.0.4.2" )
        h6 = self.addHost('h6', ip="10.0.4.3" )

        self.addLink(h1,s1)
        self.addLink(h2,s1)
        self.addLink(h3,r3)
        self.addLink(h4,r2)
        self.addLink(h5,s2)
        self.addLink(h6,s2)


        


topos = { 'custopo': ( lambda: CustomTopo() ) }   


# def simpleTest():
#     "Create and test a simple network"
#     topo = CustomTopo()
#     net = Mininet(topo)
#     net.start()
#     print "Dumping host connections"
#     dumpNodeConnections(net.hosts)
#     print "Testing network connectivity"
#     net.pingAll()
#     net.stop()

# if __name__ == '__main__':
#     # Tell mininet to print useful information
#     setLogLevel('info')
#     simpleTest()

