#!/usr/bin/python3
from socket     import *
from sys        import argv
from binascii   import unhexlify
from math       import ceil
from time       import sleep
import logging

class IcnForwarder :

    def __init__(self, flowType='ctrl')  :
        self.macAdrs = None
        self.sktHdlr = None
        self.pktBffr = b'\x41\xc8\x93\xff\xff\xff\xff'
        self.rcvdPkt = None
        if flowType == 'ctrl' :
            self.nodeRnk = 255 # by defining inside a if block, we can control the declaration and definition of data memebers in class
        # Temporary cache storage with limited capability of python dict
        self.cache = {
                'ctr': {
                    'rcv': 1,
                    'rnk': {
                        'brd': 0
                    },
                    'pri': []
                }
            }
        self.topic = None
        # key : value

    def __macAddressGetter (self) :
        with open('/sys/class/net/wpan{}/address'.format(argv[1]), 'r') as f :
            self.macAdrs = f.readline()
            self.macAdrs = b''.join(
                unhexlify(x) for x in 
                    self.macAdrs[:-1].split(':'))

    def processRcpTxn (self):
        with socket(AF_PACKET, SOCK_RAW, ntohs(0x0003)) as self.sktHdlr :
            self.sktHdlr.bind(('wpan{}'.format(argv[1]), 0, PACKET_BROADCAST))
            self.sktHdlr.setblocking(0)
            
            IcnForwarder.__macAddressGetter(self)
            logging.debug('[MAC][ADRS] : {}'.format(self.macAdrs))
            self.topic = self.macAdrs[-1:]
            logging.debug('[TPC][SELF] : {}'.format(bytes(self.topic)))
            self.pktBffr += self.macAdrs + bytes(':rnk:', 'utf8')

            if argv[1] == '0' and self.nodeRnk == 255 :
                # Root node
                self.nodeRnk = 1
                self.pktBffr += bytes(str(self.nodeRnk) + ':', 'utf8')
                self.cache['ctr']['rnk']['brd'] = 3

            while True :
                logging.debug(self.cache)
                self.rcvdPkt = None
                if self.cache['ctr']['rcv'] :
                    try:
                        self.rcvdPkt = self.sktHdlr.recvfrom(123)
                        logging.info('[RCVD][PKT] : {}'.format(self.rcvdPkt))
                    except BlockingIOError:
                        pass
                    if self.rcvdPkt != None :
                        tmp_hld = str(self.rcvdPkt[0]).split(':')[1:]
                        logging.debug('[PKT] : {}'.format(tmp_hld))
                        for i in range(0, ceil(tmp_hld.__len__()/2), 2):
                            attr = tmp_hld[i]
                            val = tmp_hld[i+1]

                            logging.debug('[PKT] : {} {}'.format(attr, val)) # Debug takes only str as argument

                            if 'rnk' in attr :
                                if (2 * int(val)) < self.nodeRnk :
                                    self.nodeRnk = 2 * int(val)
                                    logging.info('[SETG][RNK] : my rank is {}'.format(self.nodeRnk))
                                    self.cache['ctr']['rnk']['brd'] = 3 # We're going to introduce ttl-like 
                                                                   # concept
                                #else :
                                    #cache['ctr']['rnk']['brd'] = 0
                            # if there is a topic in the msg
                            #cache[tmp_hld[i].split('/')[0]][tmp_hld[i].split('/')[1]] = int(tmp_hld[i + 1])
                
                if self.cache['ctr']['rnk']['brd'] :
                    Tbytes = self.sktHdlr.send(self.pktBffr + bytes(str(self.nodeRnk) + ':', 'utf8'))
                    logging.info('[SENT][PKT] : Total sent {} bytes'.format(Tbytes))
                    self.cache['ctr']['rnk']['brd'] -= 1

                sleep(1)

if __name__ == "__main__" :
    # Create logging
    logging.basicConfig(
            filename='/home/priyan/code/sdn-iot-ip-icn/log/wpan{}.log'.
                format(argv[1]),
            filemode='a',
            level=logging.INFO,
            format=("%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d "
            "%(message)s"),
            datefmt='%d/%m/%Y %H:%M:%S'
        )

    # we've created a class because in future we may have two separate sockets to
    # deal with control and data packets separately
    fwdr = IcnForwarder()
    fwdr.processRcpTxn()