#!/usr/bin/python
import socket
import logging
import sys
import time

SERVER_ADDRESS = ('10.0.0.6', 65432)
DATA_INTERVAL  = 10

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
    time.sleep(5)
    logging.info(f"Starting UDP connection")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udpSock :
        udpSock.setblocking(0)
        logging.debug(f"Socket Created")
        while True :
            for i in range(255) :
                logging.info(f"Sending squence number: {i}")
                _tBytesSent = udpSock.sendto(i.to_bytes(1, 'little'), SERVER_ADDRESS)
                logging.info(f"Total bytes sent: {_tBytesSent}")
                try:
                    _dataRecevd = udpSock.recvfrom(1024)
                    logging.info(f"Data received: {_dataRecevd}")
                except BlockingIOError:
                    pass

                time.sleep(DATA_INTERVAL)