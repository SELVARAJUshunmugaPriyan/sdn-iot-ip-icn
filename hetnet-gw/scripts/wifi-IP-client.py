#!/usr/bin/python
import socket
import logging
import sys
import time

SERVER_ADDRESS = ('10.0.0.6', 65432)

if __name__ == "__main__" :

    logging.basicConfig(
        filename='/home/priyan/github-repo-offline/sdn-iot-ip-icn/hetnet-gw/logs/wifi-IP/wlan{}.log'.
            format(sys.argv[1]),
        filemode='a',
        level=logging.DEBUG,
        format=("%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d "
        "%(message)s"),
        # datefmt='%d/%m/%Y %H:%M:%S.%m'
        )
    time.sleep(20)
    logging.info(f"Starting UDP connection")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udpSock :
        logging.debug(f"Socket Created")
        while True :
            for i in range(255) :
                logging.debug(f"Sending squence number: {i}")
                _tBytesSent = udpSock.sendto(int.to_bytes(i), SERVER_ADDRESS)
                logging.info(f"Total bytes sent: {_tBytesSent}")
                _dataRecevd = udpSock.recvfrom(1024)
                logging.info(f"Data received: {_dataRecevd}")
                time.sleep(1)