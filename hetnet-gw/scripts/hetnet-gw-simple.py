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
WLAN_CLIENT_PORT_ADDRESS  = {}

def ndnPktGetter(nodeID, tempVal):
    try:
        nodeID = int(nodeID).to_bytes(1, 'little')
        tempVal = int(tempVal).to_bytes(1, 'little') if type(tempVal) != bytes else tempVal
    except ValueError:
        pass
    return b'\x06\x0d\x07\x03\x08\x01' + nodeID + b'\x14\x01' + tempVal + b'\x16\x01\xff'

def receiveFromWpan(ndn15_4Sock, out_q, stop):
    while True :
        select([ndn15_4Sock], [], []) # Polling read socket
        try :
            _rcvPkt = ndn15_4Sock.recvfrom(123)
            _frame = _rcvPkt[0].decode('unicode-escape')
            _data = [ ord(_frame[x]) for x in (-7, -4) ]                # data[0] = Sender Name in NDN, data[1] = data
            logging.info(f"WPAN: received {_data[1]} from {_data[0]}")
            out_q.put(_data)
        except BlockingIOError:
            pass
        if stop():
            break
    return

def receiveFromWlan(ip80211Sock, out_q, stop):
    while True :
        select([ip80211Sock], [], []) # Polling read socket
        try:
            _data, _addr = ip80211Sock.recvfrom(1024)
            out_q.put(tuple((_data, _addr)))
            logging.info(f"WLAN: received {_data} from {_addr}")
            try:
                if WLAN_CLIENT_PORT_ADDRESS[_addr[0][-1]] :
                    pass
            except KeyError :
                WLAN_CLIENT_PORT_ADDRESS[_addr[0][-1]] = _addr[1]
        except BlockingIOError:
            pass
        if stop():
            break
    return

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
    return

def sendToWlan(ip80211Sock, in_q, stop):
    while True:
        logging.debug(f"WLAN: Entering Txn...")
        select([], [ip80211Sock], [])
        _data = in_q.get(True, None)
        logging.debug(f"Sending {_data[0]} to {_data[1]}") # _data[0] = IP address and _data[1] = data
        ip80211Sock.sendto(_data[0], _data[1])
        if stop():
            break
    return

def ndnIpProtoTrans(in_q, out_q, stop):                    # NDN Name to IP Address Translation
    while True:
        _data = in_q.get(True, None)
        _data[0] = str(_data[0])
        try:
            out_q.put(
                tuple((_data[1].to_bytes(1, 'little'),
                    tuple(('10.0.0.' + _data[0], WLAN_CLIENT_PORT_ADDRESS[_data[0]]))
                ))
            )
        except KeyError :
            logging.debug('Unkown receiver address')
        if stop():
            break
    return

def ipNdnProtoTrans(in_q, out_q, stop):                    # IP Address to NDN Name Translation
    while True:
        _data = in_q.get(True, None)
        out_q.put(tuple((int(_data[1][0][-1]), _data[0])))
        if stop():
            break
    return

if __name__ == "__main__" :

    _stopThreads = False
    _sndBfrTwdNdn15_4 = b'\x41\xc8\x00\xff\xff\xff\xff'
    _openedThreads = []

    logging.basicConfig(
        filename='/home/priyan/github-repo-offline/sdn-iot-ip-icn/hetnet-gw/logs/h_gw/h_gw.log',
        filemode='a',
        level=logging.DEBUG,
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
    wpanEgfrmPtQueue = Queue()
    wpanEgfrmWlanQueue = Queue()
    wlanEgfrmPtQueue = Queue()
    wlanEgfrmWpanQueue = Queue()

    # Individual Thread Creation
    # 15.4 -> wlanEgfrmWpanQueue       -> ndnIP pt ->      wlanEgfrmPtQueue -> 802.11
    _thread_WpanReception = Thread(target=receiveFromWpan, args=(ndn15_4Sock, wlanEgfrmWpanQueue, lambda : _stopThreads, )) # Incoming packets from WPAN is fed through prot. trans. towards WLAN
    _openedThreads.append(_thread_WpanReception)
    # 802.11 -> wpanEgfrmWlanQueue     -> ipNdn pt ->      wpanEgfrmPtQueue -> 15.4
    _thread_WlanReception = Thread(target=receiveFromWlan, args=(ip80211Sock, wpanEgfrmWlanQueue, lambda : _stopThreads, )) # Incoming packets from WLAN is fed through prot. trans. towards WPAN
    _openedThreads.append(_thread_WlanReception)
    # ndnIP pt ->       wpanEgfrmPtQueue -> 15.4
    _thread_WpanTxnsmsion = Thread(target=sendToWpan, args=(ndn15_4Sock, wpanEgfrmPtQueue, _sndBfrTwdNdn15_4, lambda : _stopThreads, )) # Outgoing packets from prot. trans. towards WPAN
    _openedThreads.append(_thread_WpanTxnsmsion)
    # ipNdn pt ->       wlanEgfrmPtQueue -> 802.11
    _thread_WlanTxnsmsion = Thread(target=sendToWlan, args=(ip80211Sock, wlanEgfrmPtQueue, lambda : _stopThreads, )) # Outgoing packets from prot. trans. towards WLAN
    _openedThreads.append(_thread_WlanTxnsmsion)
    # wlanEgfrmWpanQueue -> ndnIP pt -> wlanEgfrmPtQueue
    _thread_NdnIp_Translat = Thread(target=ndnIpProtoTrans, args=(wlanEgfrmWpanQueue, wlanEgfrmPtQueue, lambda : _stopThreads, ))
    _openedThreads.append(_thread_NdnIp_Translat)
    # wpanEgfrmWlanQueue -> ipNdn pt -> wpanEgfrmPtQueue
    _thread_IPNdn_Translat = Thread(target=ipNdnProtoTrans, args=(wpanEgfrmWlanQueue, wpanEgfrmPtQueue, lambda : _stopThreads, ))
    _openedThreads.append(_thread_IPNdn_Translat)
    
    # Thread operations
    for i in _openedThreads :
        i.start()

    try:
        while True :
            sleep(1)
    except KeyboardInterrupt:
        ndn15_4Sock.close()
        ip80211Sock.close()
        stopThreads = False
        # Thread operations
        for i in _openedThreads :
            i.join()