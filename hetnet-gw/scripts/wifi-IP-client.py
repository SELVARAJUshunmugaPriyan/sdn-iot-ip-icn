#!/usr/bin/python
import socket
import logging
import sys
from time import sleep
from threading import Thread
from select import select

SERVER_ADDRESS = ('10.0.0.6', 65432)
DATA_INTERVAL  = 10

def receive(udpSock, stop):
    while True:
        select([udpSock], [], [], 0.0)
        try:
            _dataRecevd = udpSock.recvfrom(1024)
            logging.info(f"Data received: {_dataRecevd}")
        except BlockingIOError:
            pass
        if stop():
            break
    return

def send(udpSock, stop):
    while True :
        for i in range(255) :
            select([], [udpSock], [], 0.0)
            _tBytesSent = udpSock.sendto(i.to_bytes(1, 'little'), SERVER_ADDRESS)
            logging.info(f"Sending squence number: {i}. Total bytes sent: {_tBytesSent}")
            
            sleep(DATA_INTERVAL)
            if stop():
                return

if __name__ == "__main__" :

    logging.basicConfig(
        filename='/home/priyan/github-repo-offline/sdn-iot-ip-icn/hetnet-gw/logs/wifi-IP/wlan{}.log'.
            format(sys.argv[1]),
        filemode='a',
        level=logging.INFO,
        format=("%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d "
        "%(message)s"),
        # datefmt='%d/%m/%Y %H:%M:%S.%m'
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