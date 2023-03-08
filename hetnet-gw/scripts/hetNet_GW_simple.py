#!/usr/bin/python3
import socket
import logging
from binascii   import unhexlify
from time       import sleep
from select     import select
from threading  import Thread
from generic_GW_func import ndnPktGetter
import generic_conf

def receiveFromWpan(ndn15_4Sock, ip80211Sock, stop):
    while True :
        select([ndn15_4Sock], [], []) # Polling read socket
        try :
            _rcvPkt = ndn15_4Sock.recvfrom(123)
            _data = []
            _data.append(_rcvPkt[0][21])
            _data.append(_rcvPkt[0][24:24 + generic_conf.DATA_PKT_SIZE])
            logging.info(f"WPAN: received {_data[1]} from {_data[0]}")
            sendToWlan(ip80211Sock, _data)
        except BlockingIOError:
            pass
        if stop():
            break
    return

def receiveFromWlan(ip80211Sock, ndn15_4Sock, sndBfr, stop):
    while True :
        select([ip80211Sock], [], []) # Polling read socket
        try:
            _data, _addr = ip80211Sock.recvfrom(1024)
            sendToWpan(ndn15_4Sock, tuple((_data, _addr)), sndBfr)
            logging.info(f"WLAN: received {_data} from {_addr}")
            # try:
            #     if WLAN_CLIENT_PORT_ADDRESS[_addr[0][-1]] :
            #         pass
            # except KeyError :
            #     WLAN_CLIENT_PORT_ADDRESS[_addr[0][-1]] = _addr[1]
        except BlockingIOError:
            pass
        if stop():
            break
    return

def sendToWpan(ndn15_4Sock, data, sndBfr):
    logging.debug(f"WPAN: Entering Txn...")
    select([], [ndn15_4Sock], [])
    data = ipNdnProtoTrans(data)
    cmpltSndBfr = sndBfr + ndnPktGetter(data[0], data[1])
    logging.debug(f"Sending {cmpltSndBfr}")
    ndn15_4Sock.send(cmpltSndBfr)
    return

def sendToWlan(ip80211Sock, data):
    logging.debug(f"WLAN: Entering Txn...")
    select([], [ip80211Sock], [])
    data = ndnIpProtoTrans(data)
    if data:
        logging.debug(f"Sending {data[0]} to {data[1]}") # _data[0] = IP address and _data[1] = data
        ip80211Sock.sendto(data[0], data[1])
    else:
        logging.debug(f"Unkown client")
    return

def ndnIpProtoEncap(data):                    # NDN Name to IP Address Translation
    return tuple((data, tuple(('10.0.0.' + str(data[0]), generic_conf.WLAN_CLIENT_PORT_ADDRESS))))

def ipNdnProtoEncap(data):                    # IP Address to NDN Name Translation
    return tuple((int(data[1][0][-1]), data))
    
def ndnIpProtoTrans(data):                    # NDN Name to IP Address Translation
    return tuple((data[1], tuple(('10.0.0.' + str(data[0]), generic_conf.WLAN_CLIENT_PORT_ADDRESS))))

def ipNdnProtoTrans(data):                    # IP Address to NDN Name Translation
    return tuple((int(data[1][0][-1]), data[0]))

if __name__ == "__main__" :

    _stopThreads = False
    _sndBfrTwdNdn15_4 = b'\x41\xc8\x00\xff\xff\xff\xff'
    _openedThreads = []

    logging.basicConfig(
        filename='/home/priyan/code/githubRepoOffline/sdn-iot-ip-icn/hetnet-gw/logs/HetNet_GW/HetNet_GW_simple.log',
        filemode='a',
        level=logging.CRITICAL,
        format=("%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d "
        "%(message)s"),
    )

    # IEEE 802.15.4 - NDN Socket Creation
    ndn15_4Sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
    ndn15_4Sock.bind(('wpan0', 0, socket.PACKET_BROADCAST))
    ndn15_4Sock.setblocking(0)

    # IEEE 802.11   - IP Socket Creation
    ip80211Sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ip80211Sock.bind((generic_conf.AP_IP_ADDRESS_EGRESS_WLAN, generic_conf.AP_PT_ADDRESS_EGRESS_WLAN))
    ip80211Sock.setblocking(0)

    with open(f"/sys/class/net/wpan{generic_conf.WPAN_DEV_ID}/address", 'r') as f :
            _strng = f.readline()
            _strng = b''.join(unhexlify(x) for x in _strng[:-1].split(':'))
            _sndBfrTwdNdn15_4 += _strng                   # Appending Device MAC address


    # Individual Thread Creation
    # 15.4 --> 802.11
    _thread_WpanReception = Thread(target=receiveFromWpan, args=(ndn15_4Sock, ip80211Sock, lambda : _stopThreads, ))
    _openedThreads.append(_thread_WpanReception)
    # 802.11 --> 15.4
    _thread_WlanReception = Thread(target=receiveFromWlan, args=(ip80211Sock, ndn15_4Sock, _sndBfrTwdNdn15_4, lambda : _stopThreads, ))
    _openedThreads.append(_thread_WlanReception)

    try:
        # Thread operations
        for i in _openedThreads :
            i.start()
    except KeyboardInterrupt:
        ndn15_4Sock.close()
        ip80211Sock.close()
        stopThreads = True
        # Thread operations
        for i in _openedThreads :
            i.join()