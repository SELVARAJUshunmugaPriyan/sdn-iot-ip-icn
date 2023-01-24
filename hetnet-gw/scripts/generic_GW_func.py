#!/usr/bin/python3
from select import select
import logging

def emptySocket(sock, bfrSize):
    # Remove the data present on the socket
    while True:
        _inputReady, o, e = select([sock],[],[], 0.0)
        if not _inputReady.__len__(): 
            break
        try:
            sock.recv(bfrSize)
        except BlockingIOError:
            pass
    return

def ndnPktGetter(nodeID, tempVal):
    try:
        nodeID = int(nodeID).to_bytes(1, 'little')
        # tempVal = int(tempVal).to_bytes(1, 'little') if type(tempVal) != bytes else tempVal
    except ValueError:
        logging.debug("ValueError in conversion of nodeID and tempVal")
    return b'\x06' + (13 + tempVal.__len__()).to_bytes(1, 'little') + b'\x07\x03\x08\x01' + nodeID + b'\x14' + tempVal.__len__().to_bytes(1, 'little') + tempVal + b'\x16\x01\xff'
    # _retLst = b'\x06\x0d\x07\x03\x08\x01' + nodeID + b'\x14' # Second byte (_retLst[1]) must change based on the data length. It should be \x0d + LENGTH_OF_DATA. It should be in range between 13 and 116.
                                                             # ninth byte (_retLst[8]) must change based on the data length. It should be in range between 01 and 104.
                                                             # b'\x06\x0d\x07\x03\x08\x01\x01\x14\x01\x00\x16\x01\xff'.__len__() = 13
                                                             # b'\x41\xc8\x00\xff\xff\xff\xff'.__len__() = 7

                                                             # NDN - IP: refer to the packet lengths in ninth byte. It should be used to truncate the data value and it is not needed in building the UDP packet.
                                                             # IP - NDN: measure the data length. It should be used to estimate 2nd and 9th byte values.