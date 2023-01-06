#!/usr/bin/python3

'''
Objective: Develop sophisticated hetnet gateway. This code is used to setup star topology in 15.4 .
Known Flaws: 
- missing reception part
- improper socket usage
'''

import socket
import sys
import logging
from time import sleep
from binascii import unhexlify
from select import select
from random import random
from threading import Thread

DATA_INTERVAL = 0.001

def emptySocket(sock):
    # Remove the data present on the socket
    _input = [sock]
    while True:
        _inputReady, o, e = select.select(_input,[],[], 0.0)
        if not _inputReady.__len__(): 
            break
        for _sck in _inputReady:
            try:
                _sck.recv(123)
            except BlockingIOError:
                pass
    return

def ndnPktGetter(nodeID, tempVal):
    return b'\x06\x0d\x07\x03\x08\x01' + int(nodeID).to_bytes(1, 'big') + b'\x14\x01' + int(tempVal).to_bytes(1, 'big') + b'\x16\x01\xff'

def receive(devStat, drpPrcnt, l2_sock, nodeId, stop):
    while devStat :
        _rcvPkt = None
        if round(random() * 100) > drpPrcnt :
            while True:
                _inputReady, o, e = select([l2_sock],[],[], 0.0)
                if not _inputReady.__len__(): 
                    break
                try:
                    _rcvPkt = l2_sock.recvfrom(123)
                    _frame = _rcvPkt[0].decode('unicode-escape')
                    _data = [ ord(_frame[x]) for x in (-7, -4) ]
                    logging.debug('Received for {}. Data: {}'.format(_data[0], _data[1]))
                    if _data[0] == int(nodeId) :
                        logging.info(f"Received: {_data[1].to_bytes(1, 'big')}")
                except BlockingIOError:
                    pass
                except IndexError:
                    pass
                #emptySocket(l2_sock)
        if stop():
            break
    return

def send(commStat, drpPrcnt, sndBfr, nodeID, l2_sock, stop):
    while True :
        if commStat and round(random() * 100) > drpPrcnt: # Generating new content for topic of node ID
            _cmpltSndBfr = sndBfr + ndnPktGetter(nodeID, tempVal=round(random() * 255))
            select([],[l2_sock],[], 0.0)
            _tBytes = l2_sock.send(_cmpltSndBfr)
            logging.debug(f"Total sent bytes {_tBytes}")
            logging.info(f"Sending random squence: {_cmpltSndBfr[24:25]}")

        sleep(DATA_INTERVAL)
        if stop():
            break
    return

if __name__ == "__main__" :

    _cache   = {
        'nod': None,   # Node ID
        'sat': True,   # Device on/off Status
        'cnt': {},     # Contains actual topic:value pair
        'com': True,   # Communicating Flag
        'drp': 0,
    }
    _sndBfr = b'\x41\xc8\x00\xff\xff\xff\xff'   # Preceeding IEEE 802154 Broadcast Format
                                                # Incomplete without CRC trailer (avoided for prototyping)
    _stopThreads = False

    # Retreiving node ID
    try:
        _cache['nod'] = int(sys.argv[1])    # Node ID
    except ValueError :
        raise Exception("Incorrect value for node ID")
    except IndexError :
        raise Exception("No value given for the node ID")

    if _cache['nod'] :
        logging.basicConfig(
            filename='/home/priyan/code/githubRepoOffline/sdn-iot-ip-icn/hetnet-gw/logs/802_15_4_CCN/WPAN_node_{}.log'.format(_cache['nod']),
            filemode='a',
            level=logging.INFO,
            format=("%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d %(message)s"),
        )

    # Retreiving loss percentage
    try:
        _cache['drp'] = int(sys.argv[2])    # Loss percentage
    except ValueError :
        logging.warning("Incorrect value for loss percentage")
    except IndexError :
        logging.warning("No value given for loss percentage")

    l2_sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
    l2_sock.bind(('wpan{}'.format(_cache['nod']), 0, socket.PACKET_BROADCAST))
    l2_sock.setblocking(0)
    logging.debug('l2_socket established')

    with open('/sys/class/net/wpan{}/address'.format(_cache['nod']), 'r') as f :
            _strng = f.readline()
            _strng = b''.join(unhexlify(x) for x in _strng[:-1].split(':'))
            _sndBfr += _strng                   # Appending Device MAC address

    logging.debug(f"Device status 'ON' : {_cache['sat']}")

    # Creation of receive thread
    # Thread(target=receive, args=(_cache['sat'], _cache['drp'], l2_sock, _cache['nod'], lambda : _stopThreads)).start()
    Thread(target=send, args=(_cache['com'], _cache['drp'], _sndBfr, _cache['nod'], l2_sock, lambda : _stopThreads)).start()
    
    try:
        while True :
            sleep(1)            # Need a proper program shutdown
    except KeyboardInterrupt:
        l2_sock.close()
        stopThreads = True