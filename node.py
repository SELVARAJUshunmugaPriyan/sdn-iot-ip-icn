#!/usr/bin/python3
from socket     import *
from sys        import argv
from binascii   import unhexlify
from math       import ceil
from time       import sleep
import logging
import _thread

SDN_CONTROLLER_ADDRESS = '10.0.254.1' 
SDN_CONTROLLER_PORT = 5001

class priCmmnForwarder :
    def __init__(self, nodeNum=argv[1], macAdrs=None, sktHdlr=None, pktBffr=b'\x41\xc8\x93\xff\xff\xff\xff', rcvdPkt=None, nodeType='ccn') :    
        self.macAdrs = macAdrs
        self.sktHdlr = sktHdlr
        self.pktBffr = pktBffr
        self.rcvdPkt = rcvdPkt
        self.rootCon = None
        self.nodeNum = int(nodeNum)
        if nodeType == 'ccn' :
            self.topic = None
        # Preconfigured values
        self.univClk = 300
        self.nodeRnk = 255
        # Temporary cache storage with limited capability of python dict
        self.cache = {
                'ctr': {
                    'rcv': 1,
                    'rnk': {
                        'brd': 0
                    },
                    'pri': []
                },
                'pav': {} # Dict of lower rank nodes
            }

    def __dictToSerial(self, dic):
        if not isinstance(dic, dict) :
            return dic
        sr = ''
        for i in dic.keys():
            try:
                if int(dic[i]['r']) < self.nodeRnk :
                    continue
            except (TypeError, KeyError):
                pass
            try:
                if int(i) < 10 :
                    sr += '0' + i
                else :
                    sr += i
            except ValueError :
                sr += i
            sr += str(self.__dictToSerial(dic[i]))
        return sr

    def __macAddressGetter (self) :
        with open('/sys/class/net/wpan{}/address'.format(self.nodeNum), 'r') as f :
            self.macAdrs = f.readline()
            self.macAdrs = b''.join(
                unhexlify(x) for x in 
                    self.macAdrs[:-1].split(':')) # This should be ':' since MAC address is delimited by ':' only

    def _rootConnTwdCntrllr (self):
        pass

    def processRcpTxn (self):
        _refLenCachePav = str(self.cache['pav']).__len__()
        with socket(AF_PACKET, SOCK_RAW, ntohs(0x0003)) as self.sktHdlr :
            self.sktHdlr.bind(('wpan{}'.format(self.nodeNum), 0, PACKET_BROADCAST))
            self.sktHdlr.setblocking(0)
            self.__macAddressGetter()
            logging.debug('[MAC][ADRS] : {}'.format(self.macAdrs))
            
            self.topic = self.macAdrs[-1:]
            logging.debug('[TPC][SELF] : {}'.format(bytes(self.topic)))
            
            _sendBuffer = self.pktBffr + self.macAdrs + bytes('>rnk>', 'utf8')

            # Root node
            if not self.nodeNum and self.nodeRnk == 255 :
                self.nodeRnk = 1
                _sendBuffer += bytes(str(self.nodeRnk) + '>', 'utf8')
                self.cache['ctr']['rnk']['brd'] = 3
                self.rootCon = socket()
                self.rootCon.connect((SDN_CONTROLLER_ADDRESS, SDN_CONTROLLER_PORT))
            # Node Process Begins
            try: 
                while True :
                    logging.debug(self.cache)
                    
                    self.rcvdPkt = None
                    if self.cache['ctr']['rcv'] :
                        # Recieve packets
                        try:
                            self.rcvdPkt = self.sktHdlr.recvfrom(123)
                            logging.info('[RCVD][PKT] : {}'.format(self.rcvdPkt))
                        
                        except BlockingIOError:
                            pass
                        # If packets received
                        if self.rcvdPkt != None :
                            _tmp_hld = str(self.rcvdPkt[0]).split('>')[1:]
                            logging.debug('[PKT] : {}'.format(_tmp_hld))
                            
                            for i in range(0, ceil(_tmp_hld.__len__()/2), 2): # Process the received packets one by one
                                attr = _tmp_hld[i]
                                val = _tmp_hld[i+1]
                                logging.debug('[PKT] : {} {}'.format(attr, val)) # Debug takes only str as argument

                                if 'rnk' in attr :
                                    # Rank setter
                                    if int(val) < self.nodeRnk :
                                        self.nodeRnk = 2 * int(val)
                                        logging.info('[SETG][RNK] : my rank is {}'.format(self.nodeRnk))
                                        self.cache['pav'][str(self.rcvdPkt[1][-1][0])] = dict(r=val)
                                        self.cache['ctr']['rnk']['brd'] = 3 # We're going to introduce ttl-like concept
                                    # Receive down nodes' ranks                                   
                                    elif int(val) >= self.nodeRnk :
                                        logging.info('[RECV][RNK] : node {} rank {}'.format(self.rcvdPkt[1][-1][0], val))
                                        
                                        self.cache['pav'][str(self.rcvdPkt[1][-1][0])] = dict(r=val)
                                        logging.info('[CACHE][PAV] : {}'.format(self.cache['pav']))
                            
                                # Map down nodes ranks
                                if 'pav' in attr :
                                    logging.info('[RECV][PAV] : node {} lowerRank {}'.format(self.rcvdPkt[1][-1][0], val))
                                    try:
                                        if int(self.cache['pav'][str(self.rcvdPkt[1][-1][0])]['r']) <= self.nodeRnk :
                                            continue
                                    except (KeyError, TypeError):
                                        pass
                                    try:
                                        self.cache['pav'][str(self.rcvdPkt[1][-1][0])]['d'] = val + 'D'
                                    except KeyError:
                                        self.cache['pav'][str(self.rcvdPkt[1][-1][0])] = dict(d=(val+'D'))
                                    logging.debug('[CACHE][PAV] : {}'.format(self.cache['pav']))
                                    

                    # If broadcast is allowed, send
                    if self.cache['ctr']['rnk']['brd'] :
                        Tbytes = self.sktHdlr.send(_sendBuffer + bytes(str(self.nodeRnk) + '>', 'utf8'))
                        logging.info('[SENT][PKT] : Total sent {} bytes'.format(Tbytes))
                        
                        self.cache['ctr']['rnk']['brd'] -= 1

                    sleep(1)

                    # Down nodes up forwarder
                    self.univClk -= 1
                    if not self.univClk :
                        self.univClk = 300
                    logging.debug('self.cache[\'pav\'].__len__() {} _refLenCachePav {} univClk {}'.format(self.cache['pav'].__len__(), _refLenCachePav, self.univClk))

                    if str(self.cache['pav']).__len__() != _refLenCachePav and not self.univClk % 3 :
                        _refLenCachePav = str(self.cache['pav']).__len__()
                        logging.debug(self.cache['pav'])

                        try:
                            Tbytes = self.sktHdlr.send(self.pktBffr + self.macAdrs + b'>pav>' + bytes(self.__dictToSerial(self.cache['pav']), 'utf8') + b'>') # Don't remove '>' it causes Index error in line 74
                            logging.info('[SENT][PKT] : Total sent {} bytes'.format(Tbytes))

                            # Sending the network map towards controller
                            if not self.nodeNum :
                                self.rootCon.send(bytes(self.__dictToSerial(self.cache['pav']), 'utf8'))
                                logging.warning('[CNTR][PKT] : Total sent {} bytes'.format(Tbytes))
                        except OSError:
                            logging.debug(self.__dictToSerial(self.cache['pav']))

            finally:
                self.rootCon.close()

if __name__ == "__main__" :
    # Create logging
    logging.basicConfig(
            filename='/home/priyan/code/sdn-iot-ip-icn/log/wpan{}.log'.
                format(argv[1]),
            filemode='a',
            level=logging.WARNING,
            format=("%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d "
            "%(message)s"),
            datefmt='%d/%m/%Y %H:%M:%S'
        )

    # we've created a class because in future we may have two separate sockets to
    # deal with control and data packets separately
    node = priCmmnForwarder()
    node.processRcpTxn()