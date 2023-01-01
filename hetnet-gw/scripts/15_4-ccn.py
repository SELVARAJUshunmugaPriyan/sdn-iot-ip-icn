#!/usr/bin/python3

'''
Objective: Develop sophisticated hetnet gateway. This code is used to setup star topology in 15.4 .
Known Flaws: 
- missing reception part
- improper socket usage
'''

import socket
import sys
import time
import binascii
import logging
import select
import random

DATA_INTERVAL = 0.005

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

if __name__ == "__main__" :

    _cache   = {
        'nod': None,    # Node number
        'sat': True,   # Device on/off Status
        'cnt': {},      # Contains actual topic:value pair
        'com': True,   # Communicating Flag
    }
    _rcvPkt = None
    _sndBfr = b'\x41\xc8\x00\xff\xff\xff\xff'                   # Preceeding IEEE 802154 Broadcast Format
                                                                # Incomplete without CRC trailer (avoided for prototyping)

    try:
        _cache['nod'] = int(sys.argv[1])
        _cache['drp'] = int(sys.argv[2])    # Loss percentage
    except ValueError :
        raise Exception("Incorrect value for number of nodes")
    except IndexError :
        raise Exception("No value for number of nodes")
    
    if _cache['nod'] :
        logging.basicConfig(
            filename='/home/priyan/github-repo-offline/sdn-iot-ip-icn/hetnet-gw/logs/15_4-ccn/wpan{}.log'.
                format(_cache['nod']),
            filemode='a',
            level=logging.INFO,
            format=("%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d "
            "%(message)s"),
        )

    l2_sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
    l2_sock.bind(('wpan{}'.format(_cache['nod']), 0, socket.PACKET_BROADCAST))
    l2_sock.setblocking(0)
    logging.info('l2_socket established')

    with open('/sys/class/net/wpan{}/address'.format(_cache['nod']), 'r') as f :
            _strng = f.readline()
            _strng = b''.join(binascii.unhexlify(x) for x in _strng[:-1].split(':'))
            _sndBfr += _strng                   # Appending Device MAC address

    logging.info(_cache['sat'])
    while _cache['sat'] :
        try:
            _rcvPkt = None
            if round(random.random() * 100) > _cache['drp'] :
                _rcvPkt = l2_sock.recvfrom(123)
                _frame = _rcvPkt[0].decode('unicode-escape')
                _data = [ ord(_frame[x]) for x in (-7, -4) ]
                logging.info('{} {}'.format(_data[0], _data[1]))
            emptySocket(l2_sock)
        except BlockingIOError:
            pass
        except IndexError:
            pass
        if _cache['com'] and round(random.random() * 100) > _cache['drp']: # Generating New content
            _cmpltSndBfr = _sndBfr + ndnPktGetter(_cache['nod'], tempVal=round(random.random() * 255))
            _tBytes = l2_sock.send(_cmpltSndBfr)
            logging.info("Total sent bytes {} - message: {} ".format(_tBytes, _cmpltSndBfr))
        
        time.sleep(DATA_INTERVAL)