#!/usr/bin/python
import socket
import logging
import sys
from time import sleep
from threading import Thread
from select import select
from random import random
from generic_conf import SERVER_ADDRESS, DATA_INTERVAL, DATA_PKT_SIZE, CLIENT_UDP_PORT

def receive(udpSock, stop):
    while True:
        select([udpSock], [], [])
        try:
            _dataRecevd = udpSock.recvfrom(1024)
            logging.info(f"Received: {_dataRecevd[0][:5]}")
        except BlockingIOError:
            pass
        if stop():
            break
    return

def send(udpSock, pktSize, stop):
    while True :
        select([], [udpSock], [])
        _seqByts = b''
        for i in range(5):
            _seqByts += int(random() * 255).to_bytes(1,'little')
        for i in range(pktSize - 5):
            _seqByts += b'\x00'
        # _tBytesSent = udpSock.sendto(_seqByts, SERVER_ADDRESS)
        logging.debug(f"Total bytes sent: {udpSock.sendto(_seqByts, SERVER_ADDRESS)}")
        logging.info(f"Sending random squence: {_seqByts[:5]}")
        
        sleep(DATA_INTERVAL)
        if stop():
            return

if __name__ == "__main__" :

    logging.basicConfig(
        filename='/home/priyan/code/githubRepoOffline/sdn-iot-ip-icn/hetnet-gw/logs/802_11_IP/WLAN_node_{}.log'.format(sys.argv[1]),
        filemode='a',
        level=logging.INFO,
        format=("%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d %(message)s"),
        )

    _stopThreads = False

    logging.debug(f"Starting UDP connection")
    udpSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udpSock.bind(("", CLIENT_UDP_PORT))
    udpSock.setblocking(0)
    logging.debug(f"Socket Created")
    
    try:
        Thread(target=receive, args=(udpSock, lambda : _stopThreads)).start()
        Thread(target=send, args=(udpSock, DATA_PKT_SIZE, lambda : _stopThreads)).start()    
    except KeyboardInterrupt:
        udpSock.close()
        _stopThreads = True