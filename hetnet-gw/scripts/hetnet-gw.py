#!/usr/bin/python3
import socket
import logging
from binascii   import unhexlify
from time       import sleep
from select     import select
from queue      import Queue
from threading  import Thread

AP_IP_ADDRESS_EGRESS_WLAN = '10.0.0.6'
AP_PT_ADDRESS_EGRESS_WLAN = 65432
WPAN_DEV_ID               = 0

def ndnPktGetter(nodeID, tempVal):
    return b'\x06\x0d\x07\x03\x08\x01' + int(nodeID).to_bytes(1, 'big') + b'\x14\x01' + int(tempVal).to_bytes(1, 'big') + b'\x16\x01\xff'

def receiveFromWpan(ndn15_4Sock, out_q, stop):
    while True :
        select([ndn15_4Sock], [], []) # Polling read socket
        try :
            _rcvPkt = ndn15_4Sock.recvfrom(123)
            _frame = _rcvPkt[0].decode('unicode-escape')
            _data = [ ord(_frame[x]) for x in (-7, -4) ]
            logging.info(f"WPAN: received {_data[0]} from {_data[1]}")
            out_q.put(_data)
        except BlockingIOError:
            pass
        if stop():
            break

def receiveFromWlan(ip80211Sock, out_q, stop):
    while True :
        select([ip80211Sock], [], []) # Polling read socket
        try:
            _data, _addr = ip80211Sock.recvfrom(1024)
            out_q.put(tuple((_data, _addr)))
            logging.info(f"WLAN: received {_data} from {_addr}")
        except BlockingIOError:
            pass
        if stop():
            break


def sendToWpan(ndn15_4Sock, in_q, _sndBfr, stop):
    while True:
        logging.debug(f"WPAN: Entering Txn...")
        select([], [ndn15_4Sock], [])
        _data = in_q.get(True, None)
        _cmpltSndBfr = _sndBfr + ndnPktGetter(_data[0], _data[1])
        logging.debug(f"Sending {_cmpltSndBfr}")
        ndn15_4Sock.send(_cmpltSndBfr)
        if stop():
            break

def sendToWlan(ip80211Sock, in_q, stop):
    while True:
        logging.debug(f"WLAN: Entering Txn...")
        select([], [ip80211Sock], [])
        _data = in_q.get(True, None)
        logging.debug(f"Sending {_data[0]} to {_data[1]}")
        ip80211Sock.sendto(_data[0], _data[1])
        if stop():
            break

def ndnIpProtoTrans():
    pass

def ipNdnProtoTrans():
    pass

if __name__ == "__main__" :

    stopThreads = False
    _sndBfrTwdNdn15_4 = b'\x41\xc8\x00\xff\xff\xff\xff' 

    logging.basicConfig(
        filename='/home/priyan/github-repo-offline/sdn-iot-ip-icn/hetnet-gw/logs/h_gw/h_gw.log',
        filemode='a',
        level=logging.INFO,
        format=("%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d "
        "%(message)s"),
    )

    # IEEE 802.15.4 - NDN Socket Creation
    ndn15_4Sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
    ndn15_4Sock.bind(('wpan0', 0, socket.PACKET_BROADCAST))
    ndn15_4Sock.setblocking(0)

    # IEEE 802.11   - IP Socket Creation
    ip80211Sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ip80211Sock.bind((AP_IP_ADDRESS_EGRESS_WLAN, AP_PT_ADDRESS_EGRESS_WLAN))
    ip80211Sock.setblocking(0)

    with open(f"/sys/class/net/wpan{WPAN_DEV_ID}/address", 'r') as f :
            _strng = f.readline()
            _strng = b''.join(unhexlify(x) for x in _strng[:-1].split(':'))
            _sndBfrTwdNdn15_4 += _strng                   # Appending Device MAC address

    # Individual Queue Creation
    wpanInQueue = Queue()
    wpanOtQueue = Queue()
    wlanInQueue = Queue()
    wlanOtQueue = Queue()

    # Individual Thread Creation
    threadWpanReception = Thread(target=receiveFromWpan, args=(ndn15_4Sock, wlanOtQueue, lambda : stopThreads, )) # Incoming packets from WPAN is fed into WLAN through prot. trans.
    threadWlanReception = Thread(target=receiveFromWlan, args=(ip80211Sock, wpanOtQueue, lambda : stopThreads, )) # Incoming packets from WLAN is fed into WPAN through prot. trans.
    threadWpanTxnsmsion = Thread(target=sendToWpan, args=(ndn15_4Sock, wlanOtQueue, _sndBfrTwdNdn15_4, lambda : stopThreads, )) # Incoming packets from WLAN is fed into WPAN through prot. trans.
    threadWlanTxnsmsion = Thread(target=sendToWlan, args=(ip80211Sock, wpanOtQueue, lambda : stopThreads, )) # Incoming packets from WLAN is fed into WPAN through prot. trans.
    
    # Thread operations
    threadWpanReception.start()
    threadWlanReception.start()
    threadWpanTxnsmsion.start()
    threadWlanTxnsmsion.start()

    try:
        while True :
            sleep(1)
    except KeyboardInterrupt:
        stopThreads = False