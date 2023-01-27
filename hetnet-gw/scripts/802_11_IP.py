#!/usr/bin/python

'This example shows how to create multiple interfaces in stations'

import sys
from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.link import wmediumd, adhoc
from mn_wifi.wmediumdConnector import interference

BASE_DIR = "/home/priyan/code/githubRepoOffline/sdn-iot-ip-icn/hetnet-gw/"

def topology():
    "Create a network."
    net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference)

    info("*** Creating nodes\n")
    sta1 = net.addStation('sta1', position='200,250,0')
    sta2 = net.addStation('sta2', position='150,250,0')
    sta3 = net.addStation('sta3', position='150,200,0')
    sta4 = net.addStation('sta4', position='150,150,0')
    sta5 = net.addStation('sta5', position='200,150,0')
    ap1 = net.addAccessPoint('ap1', ssid='ssid_1', mode='g', channel='5', failMode="standalone", position='200,200,0')
    # ap1 = net.addAccessPoint('ap1', ssid='ssid_1', mode='g', channel='5', failMode="standalone", position='200,200,0')
    # ap1 = net.addAccessPoint('ap1', ssid='ssid_1', mode='g', channel='5', failMode="standalone", position='200,200,0')
    # ap1 = net.addAccessPoint('ap1', ssid='ssid_1', mode='g', channel='5', failMode="standalone", position='200,200,0')
    # ap1 = net.addAccessPoint('ap1', ssid='ssid_1', mode='g', channel='5', failMode="standalone", position='200,200,0')

    info("*** Configuring Propagation Model\n")
    net.setPropagationModel(model="logDistance", exp=4)

    info("*** Configuring wifi nodes\n")
    net.configureWifiNodes()

    info("*** Associating...\n")
    net.addLink(ap1, sta1)
    net.addLink(ap1, sta2)
    net.addLink(ap1, sta3)
    net.addLink(ap1, sta4)
    net.addLink(ap1, sta5)

    #net.plotGraph(max_x=300, max_y=300)

    info("*** Starting network\n")
    net.build()
    net.addNAT().configDefault()
    ap1.start([])

    ap1.cmd("echo 1 > /proc/sys/net/ipv4/ip_forward")

    info("*** Running User commands\n")
    sta1.cmd(f"{BASE_DIR}scripts/802_11_IP_CL.py 1 &")   # Change Destination and AP IP address ( ... is usually +1 to # of sta nodes)
    sta2.cmd(f"{BASE_DIR}scripts/802_11_IP_CL.py 2 &")   # Not needed default route has been set to AP
    sta3.cmd(f"{BASE_DIR}scripts/802_11_IP_CL.py 3 &")
    sta4.cmd(f"{BASE_DIR}scripts/802_11_IP_CL.py 4 &")
    sta5.cmd(f"{BASE_DIR}scripts/802_11_IP_CL.py 5 &")

    info("*** Running CLI\n")
    CLI(net)
    
    if len(sys.argv) > 1 :
            info("*** Introducing loss ", sys.argv[2], "%\n")
            sta1.cmd("tc qdisc add dev sta11-wlan0 root netem loss " + sys.argv[2] + "%")
            sta2.cmd("tc qdisc add dev sta12-wlan0 root netem loss " + sys.argv[2] + "%")
            sta3.cmd("tc qdisc add dev sta13-wlan0 root netem loss " + sys.argv[2] + "%")
            sta4.cmd("tc qdisc add dev sta14-wlan0 root netem loss " + sys.argv[2] + "%")
            sta5.cmd("tc qdisc add dev sta15-wlan0 root netem loss " + sys.argv[2] + "%")

	
    f = sys.argv[2] if len(sys.argv) > 1 else "0"

    #info("*** Running Test\n")
    #sta1.cmd("ping -c 600 -s 1232 198.51.100.100 | tee log/A_W_6_" + f + "L_6x6_.log")
    #sta22.cmd("ping -c 300 -s 1232 198.51.100.100 | tee log/A_W_6_0L_" + f + "x" + f + "_Stable.log")

    
    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology()
