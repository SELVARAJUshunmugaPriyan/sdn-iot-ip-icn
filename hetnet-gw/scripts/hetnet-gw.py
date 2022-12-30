#!/usr/bin/python3
import socket
import logging
import sys
import binascii
from select import select
from queue import Queue
from threading import Thread

def recieveFromWpan(ndn15_4Sock, out_q):
    #ndn15_4SockList = list(ndn15_4Sock)
    while True :
        select(ndn15_4Sock, [], []) # Polling read socket
        try :
            _rcvPkt = ndn15_4Sock.recvfrom(123)
            _frame = _rcvPkt[0].decode('unicode-escape')
            _data = [ ord(_frame[x]) for x in (-7, -4) ]
            logging.info('{} {}'.format(_data[0], _data[1]))
            out_q.put(_data)
        except BlockingIOError:
            pass

def sendToWpan(ndn15_4Sock, in_q, _sndBfr):
    while True:
        select([], ndn15_4Sock, [])
        _data = in_q.get(None)
        _cmpltSndBfr = _sndBfr + ndnPktGetter(_data[0], _data[1])
        logging.info(_cmpltSndBfr)
        ndn15_4Sock.send(_cmpltSndBfr)

def receiveFromWlan(ip802_11Sock, out_q, _sndBfr=None):
    while True :
        try:
            _rcvPkt = ip802_11Sock.recvfrom(123)
            print(_rcvPkt)
        except BlockingIOError:
            pass
    pass

def ndnPktGetter(nodeID, tempVal):
    return b'\x06\x0d\x07\x03\x08\x01' + int(nodeID).to_bytes(1, 'big') + b'\x14\x01' + int(tempVal).to_bytes(1, 'big') + b'\x16\x01\xff'

def ndnIpProtoTrans():
    pass

if __name__ == "__main__" :

    _cache   = {
        'nod': 0,    # Node number
        'sat': True,   # Device on/off Status
        'cnt': {},      # Contains actual topic:value pair
        'com': True,   # Communicating Flag
    }
    _rcvPkt = None
    _sndBfrTwdNdn15_4 = b'\x41\xc8\x00\xff\xff\xff\xff' 

    logging.basicConfig(
        filename='/home/priyan/github-repo-offline/sdn-iot-ip-icn/hetnet-gw/logs/15_4-ccn/wpan0.log',
        filemode='a',
        level=logging.INFO,
        format=("%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d "
        "%(message)s"),
    )

    ndn15_4Sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
    ndn15_4Sock.bind(('wpan0', 0, socket.PACKET_BROADCAST))
    ndn15_4Sock.setblocking(0)

    with open('/sys/class/net/wpan{}/address'.format(_cache['nod']), 'r') as f :
            _strng = f.readline()
            _strng = b''.join(binascii.unhexlify(x) for x in _strng[:-1].split(':'))
            _sndBfrTwdNdn15_4 += _strng                   # Appending Device MAC address

    wpanQueue = Queue()
    wlanQueue = Queue()

    threadWpanReception = Thread(target=recieveFromWpan, args=(ndn15_4Sock, wpanQueue, _sndBfrTwdNdn15_4))
    threadWpanReception.start()

    threadWlanReception = Thread(target=receiveFromWlan, args=(ip802_11Sock, wlanQueue, ))