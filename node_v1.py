#!/usr/bin/python3
import socket
import sys
import binascii
import time
import threading
import random
import logging

SDN_CONTROLLER_ADDRESS = '10.0.254.1' 
SDN_CONTROLLER_PORT = 14323
TICK_TIME = 1
MAX_TIME = 1000

lock = threading.Lock()

class nodeUtilities:
    def macAddressGetter(nodeNum) :
        with open('/sys/class/net/wpan{}/address'.format(nodeNum), 'r') as f :
            strng = f.readline()
            strng = b''.join(binascii.unhexlify(x) for x in strng[:-1].split(':')) # This should be ':' since MAC address is delimited by ':' only
            return strng
    
class priCtrlPlaneUnit(threading.Thread, nodeUtilities):
    # It works for only one pkt format 41c8 broadcast with long source address
    def __init__(self, evntObj, macRwsk, nodeNum, macAdrs=None, pktBffr=b'\x41\xc8\x00\xff\xff\xff\xff', rcvdPkt=None, nodeType='ccn', connReq=None, adhocMode=False, rootCon=None) :
        # Call the Thread class's init function
        threading.Thread.__init__(self)
        self.evntObj = evntObj      # Node's common clock
        self.macRwsk = macRwsk      # Node's MAC RAW socket
        self.nodeNum = nodeNum      # Node's ID number
        if not macAdrs :
            self.macAdrs = nodeUtilities.macAddressGetter(self.nodeNum)      # Node's MAC address
        else :
            self.macAdrs = macAdrs
        self.pktBffr = pktBffr      # Node's packet buffer
        self.rcvdPkt = rcvdPkt      # Received packet buffer
        if nodeType == 'ccn' :
            self.topic = None       # Node's self topic
        # Temporary cache storage with limited capability of python dict
        self.cache = {
                'ctr': {
                    'rcv': 1,
                    'rnk': {
                        'brd': 0
                        },
                    'con': {
                        'req': connReq,
                        'brd': adhocMode, 
                    },
                    'pri': []
                    },
                'pav': {} # Dict of lower rank nodes
                }   
        self.rootCon = rootCon         # Root node's connection towards controller
        # Preconfigured values
        self.univClk = 254          # System Clock
        self.nodeRnk = 254          # Node's rank in the network
        self.topic = self.macAdrs[-1:]
        logging.debug('[priCtrlPlaneUnit][TPC][SELF] : {}'.format(bytes(self.topic)))

        # Reference variable for length of cache 'pav'
        self.lenCachePav = str(self.cache['pav']).__len__()
        logging.debug('[priCtrlPlaneUnit][MAC][ADRS] : {}'.format(self.macAdrs))
            
        return

    def __rootSendCont(self, payload):
        _totalBytes = self.rootCon.send(bytes(payload, 'utf8'))
        logging.info('[_broadcastNetMap][CNTR][PKT] : Total sent {} bytes'.format(_totalBytes))
        return _totalBytes

    def __dictToSerial(self, dic):
        if not isinstance(dic, dict) :
            return dic
        strng = ''
        for key in dic.keys():
            try:
                if int(dic[key]['r']) < self.nodeRnk :
                    continue
            except (TypeError, KeyError):
                pass
            try:
                if int(key) < 10 :
                    strng += '0' + key
                else :
                    strng += key
            except ValueError :
                strng += key
            strng += str(self.__dictToSerial(dic[key]))
        return strng

    def _recvProcess(self):
        self.rcvdPkt = None
        if self.cache['ctr']['rcv'] :
            # Recieve packets
            try:
                with lock:
                    self.rcvdPkt = self.macRwsk.recvfrom(123)
                logging.info('[_recvProcess][RCVD][PKT] : {}'.format(self.rcvdPkt))
            
            except BlockingIOError:
                pass
        return

    def _pktProcessngProcess(self):
        _vldCon = False
        _tmpHld = str(self.rcvdPkt[0]).split('>')
        logging.debug('[_pktProcessngProcess][PKT] : {}'.format(_tmpHld))
        
        for index in range(1, _tmpHld.__len__() - 1, 2): # Processing each attribute at a time for now
            _attribute = _tmpHld[index]                      # only one pair of attribute value is transmitted
            _value = _tmpHld[index+1]
            logging.debug('[_pktProcessngProcess][PKT] : {} {}'.format(_attribute, _value)) # Debug takes only str as argument

            # Connection request in packet
            if 'con' in _attribute :
                if int(_value[1:]) > self.nodeRnk :
                    logging.info('[_pktProcessngProcess][CON] : {}'.format(_tmpHld[0][-2:]))
                    _vldCon = True
                    continue
                    
            if _vldCon and 'nod' in _attribute :
                if not self.nodeNum :
                    self.__rootSendCont(payload='con_req:' + _value)
                else :
                    self._broadcastConnectionRequest(payload=_value)
                continue

            # Rank in packet
            if 'rnk' in _attribute :
                # Rank setter
                if int(_value) < self.nodeRnk :
                    self.nodeRnk = 2 * int(_value)
                    logging.info('[_pktProcessngProcess][SETG][RNK] : my rank is {}'.format(self.nodeRnk))
                    self.cache['pav'][str(self.rcvdPkt[1][-1][0])] = dict(r=_value)
                    self.cache['ctr']['rnk']['brd'] = 3 # We're going to introduce ttl-like concept
                # Receive down nodes' ranks                                   
                elif int(_value) >= self.nodeRnk :
                    logging.info('[_pktProcessngProcess][RECV][RNK] : node {} rank {}'.format(self.rcvdPkt[1][-1][0], _value))
                    
                    self.cache['pav'][str(self.rcvdPkt[1][-1][0])] = dict(r=_value)
                    logging.info('[_pktProcessngProcess][CACHE][PAV] : {}'.format(self.cache['pav']))
                continue
        
            # Network map in packet
            if 'pav' in _attribute :
                logging.info('[_pktProcessngProcess][RECV][PAV] : node {} lowerRank {}'.format(self.rcvdPkt[1][-1][0], _value))
                try:
                    if int(self.cache['pav'][str(self.rcvdPkt[1][-1][0])]['r']) <= self.nodeRnk :
                        continue
                except (KeyError, TypeError):
                    pass
                try:
                    self.cache['pav'][str(self.rcvdPkt[1][-1][0])]['d'] = _value + 'D'
                except KeyError:
                    self.cache['pav'][str(self.rcvdPkt[1][-1][0])] = dict(d=(_value+'D'))
                logging.debug('[_pktProcessngProcess][CACHE][PAV] : {}'.format(self.cache['pav']))
                continue

        return

    def _broadcastProcess(self, sendBuffer):
        with lock:
            _totalBytes = self.macRwsk.send(sendBuffer + bytes(str(self.nodeRnk) + '>', 'utf8'))
        logging.info('[_broadcastProcess][SENT][PKT] : Total sent {} bytes'.format(_totalBytes))
        
        self.cache['ctr']['rnk']['brd'] -= 1
        return

    def _broadcastNetMap(self):
        logging.debug('[_broadcastNetMap] self.cache[\'pav\'].__len__() {} refLenCachePav {} univClk {}'.format(self.cache['pav'].__len__(), self.lenCachePav, self.univClk))

        try:
            with lock:
                _totalBytes = self.macRwsk.send(self.pktBffr + self.macAdrs + b'>pav>' + bytes(self.__dictToSerial(self.cache['pav']), 'utf8') + b'>')
            logging.info('[_broadcastNetMap][SENT][PKT] : Total sent {} bytes'.format(_totalBytes))

            # Sending the network map towards controller
            if not self.nodeNum :
                self.__rootSendCont('net_map:' + self.__dictToSerial(self.cache['pav']))
        except OSError:
            logging.debug(self.__dictToSerial(self.cache['pav']))
        return

    def _broadcastConnectionRequest(self, payload=''):
        # Connection request is only inter domain communications
        # If communication reuest approved the specified nodes only cache the specific data
        payload += '<' + str(self.nodeNum)
        with lock:
            _totalBytes = self.macRwsk.send(self.pktBffr + self.macAdrs + b'>con>r' + bytes(str(self.nodeRnk), 'utf8') + b'>nod>' + bytes(payload, 'utf8') + b'>')
        
        logging.warning('[_broadcastConnectionRequest] payload {}'.format(payload))

        logging.info('[_broadcastConnectionRequest][SENT][PKT] : Total sent {} bytes'.format(_totalBytes))

        return

    def run(self):
        _sendBuffer = self.pktBffr + self.macAdrs + bytes('>rnk>', 'utf8')
        # Root node
        if not self.nodeNum and self.nodeRnk == 254 :
            self.nodeRnk = 1
            _sendBuffer += bytes(str(self.nodeRnk) + '>', 'utf8')
            self.cache['ctr']['rnk']['brd'] = 3
        # Node Process Begins
        while True :
            # Main continuous process
            logging.debug(self.cache)
            self._recvProcess()
            # Receive Packets
            if self.rcvdPkt :
                self._pktProcessngProcess()
            # Rank Broadcast
            if self.cache['ctr']['rnk']['brd'] :
                self._broadcastProcess(_sendBuffer)
            # Connection request Broadcast
            if self.cache['ctr']['con']['brd'] and self.nodeRnk != 254 :
                self._broadcastConnectionRequest()
            self.evntObj.wait(timeout=1)
            self.univClk -= 1
            if not self.univClk :
                self.univClk = 254
            if str(self.cache['pav']).__len__() != self.lenCachePav and not self.univClk % 3 :
                self.lenCachePav = str(self.cache['pav']).__len__()
                logging.debug('[run] {}'.format(self.cache['pav']))

                self._broadcastNetMap()
        return

class priDataPlaneUnit(threading.Thread, nodeUtilities):
    def __init__(self, macAdrs=None, pktBffr=b'\x41\xc8\x00\xff\xff\xff\xff'):
        threading.Thread.__init__(self)
        if not macAdrs :
            self.macAdrs = nodeUtilities.macAddressGetter(self.nodeNum)      # Node's MAC address
        else :
            self.macAdrs = macAdrs
        self.pktBffr = pktBffr + macAdrs
        return

    # This class must contain generic topic and data sender and receiver
    # [NOTE] Connection_request always belongs in control plane
    # Random intra-domain communication handler

    def run(self):
        while True :
            with lock :
                pass
        return
        
if __name__ == "__main__" :
    _nodeNum = None
    _commNod = None
    _adhocMod = None
    rootCon = None
    # Initialising an event object
    _event_obj = threading.Event()

    try:
        _nodeNum = int(sys.argv[1])
    except ValueError :
        raise Exception("Incorrect value for number of nodes")
    except IndexError :
        raise Exception("No value for number of nodes")

    # Create logging
    logging.basicConfig(
            filename='/home/priyan/code/sdn-iot-ip-icn/log/wpan{}.log'.
                format(_nodeNum),
            filemode='a',
            level=logging.WARNING,
            format=("%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d "
            "%(message)s"),
            datefmt='%d/%m/%Y %H:%M:%S'
        )

    try:
        _commNod = True if sys.argv[2] else None
        logging.warning("Connection request ON")
    except IndexError :
        pass
    try:
        _adhocMod = True if sys.argv[3] == 'a' else False
        logging.warning("AD HOC request ON")
    except IndexError :
        pass

    # Creating a common layer 2 socket between control and data plane
    l2_sock = socket.socket(family=socket.AF_PACKET, type=socket.SOCK_RAW, proto=socket.ntohs(0x0003))
    l2_sock.bind(('wpan{}'.format(_nodeNum), 0, socket.PACKET_BROADCAST)) # _nodeNum is the node ID number
    l2_sock.setblocking(0)
    logging.warning('l2_socket established')

    if not _nodeNum :
        rootCon = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0)
        rootCon.settimeout(15)
        rootCon.connect((SDN_CONTROLLER_ADDRESS, SDN_CONTROLLER_PORT))

    ctlPlnThrd = priCtrlPlaneUnit(evntObj=_event_obj, macRwsk=l2_sock, nodeNum=_nodeNum, connReq=_commNod, adhocMode=_adhocMod, rootCon=rootCon)

    try:
        # we've created a class because in future we may have two separate sockets to
        # deal with control and data packets separately
        ctlPlnThrd.start()
        logging.warning('started control plane')
        #datPlnThrd = priDataPlaneUnit(l2_sock)
        #datPlnThrd.start()
        #logging.warning('started data plane')
        while True: # Without this hold up, the finally clause executes consecutively
            _event_obj.set()
            time.sleep(1)

    finally:
        l2_sock.close()
        # Closing rootCon socket
        if not rootCon :
            rootCon.close()
        ctlPlnThrd.join()