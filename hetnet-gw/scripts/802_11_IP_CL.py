#!/usr/bin/python
import socket
import logging
import sys
from time import sleep
from threading import Thread
from select import select
from random import random

SERVER_ADDRESS = ('10.0.0.6', 65432)
DATA_INTERVAL  = 0.001

def receive(udpSock, stop):
    while True:
        select([udpSock], [], [], 0.0)
        try:
            _dataRecevd = udpSock.recvfrom(1024)
            logging.info(f"Received: {_dataRecevd[0]}")
        except BlockingIOError:
            pass
        if stop():
            break
    return

def send(udpSock, stop):
    while True :
        select([], [udpSock], [], 0.0)
        _seqByts = int(random() * 255).to_bytes(1, 'little')
        _tBytesSent = udpSock.sendto(_seqByts, SERVER_ADDRESS)
        logging.debug(f"Total bytes sent: {_tBytesSent}")
        logging.info(f"Sending random squence: {_seqByts}")
        
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
    udpSock.setblocking(0)
    logging.debug(f"Socket Created")
    
    Thread(target=receive, args=(udpSock, lambda : _stopThreads)).start()
    Thread(target=send, args=(udpSock, lambda : _stopThreads)).start()

    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        udpSock.close()
        _stopThreads = True