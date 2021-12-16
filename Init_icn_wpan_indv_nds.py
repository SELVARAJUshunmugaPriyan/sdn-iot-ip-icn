#!/usr/bin/python3
from socket import *
from sys import argv
from binascii import unhexlify
from math import ceil
from time import sleep

cache = {
        'ctr': {
                'rcv': 1,
                'brd': 0,
                'pri': []
            }
    }

def recv_callback() :
    pass

macAddress = ''

with open('/sys/class/net/wpan{}/address'.format(argv[1]), 'r') as f :
    macAddress = f.readline()

macAddress = b''.join(unhexlify(x) for x in macAddress[:-1].split(':'))

with socket(AF_PACKET, SOCK_RAW, ntohs(0x0003)) as s :
    s.bind(('wpan{}'.format(argv[1]), 0, PACKET_BROADCAST))
    s.setblocking(0)
    pkt = b'\x41\xc8\x93\xff\xff\xff\xff' + macAddress + bytes(':rnk:2:ctr/brd:1:', 'utf8')
    #rootPkt = b'\x41\xc8\x93\xff\xff\xff\xff' + macAddress + bytes(':rnk:1:ctr/brd:1:', 'utf8')
    while True :
        #print(cache)
        rcv_pkt = None
        if cache['ctr']['rcv'] :
            try:
                rcv_pkt = s.recvfrom(123)
                #print(rcv_pkt)
            except BlockingIOError:
                pass
            if rcv_pkt != None :
                placeHolder = str(rcv_pkt[0]).split(':')[1:]
                #print('wpan{}: '.format(argv[1]), placeHolder)
                for i in range(0, ceil(placeHolder.__len__()/2), 2):
                    #print(placeHolder[i], placeHolder[i+1])
                    cache[placeHolder[i].split('/')[0]][placeHolder[i].split('/')[1]] = int(placeHolder[i + 1])
        
        if cache['ctr']['brd'] :
            s.send(pkt)

        sleep(1)