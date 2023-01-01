#!/usr/bin/python3
import socket
import sys
import binascii
import time
import threading
import logging
import _thread
import select

SDN_CONTROLLER_ADDRESS = '10.0.254.1' 
SDN_CONTROLLER_PORT = 14323
TICK_TIME = 1
MAP_EVRY_CNTR = 7

class RootNode(threading.Thread):
    def __init__(self, evntObj, cachLck, cache):
        threading.Thread.__init__(self)
        self.rootCon = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0)         # Root node's connection towards controller
        self.rootCon.connect((SDN_CONTROLLER_ADDRESS, SDN_CONTROLLER_PORT))
        self.rootCon.setblocking(0)
        self.evntObj = evntObj
        self.rootLck = threading.Lock()
        self.cachLck = cachLck
        self.cache   = cache

    def run(self):
        with self.rootCon :
            while True :
                self.evntObj.wait(10)
                _rcvData = None
                try:
                    with self.rootLck:
                        _rcvData = str(self.rootCon.recv(1024))
                    logging.debug("[rootSend][ROOT] : _rcvData {}".format(_rcvData))
                    if _rcvData :
                        with self.cachLck :
                            self.cache['ctr']['sdn']['nm'] = True
                            self.cache['ctr']['sdn']['msg'] = _rcvData
                        # [NOTE] Not useful to process the SDN control packet in root thread. It should be processed
                        # by node thread
                        # if 'net_map_stop' in _rcvData :
                        #     with self.cachLck :
                        #         self.cache['ctr']['dwn_sdn_msg']['ctMng_on_off'] = 2 # 0 - default 1 - on 2 - off
                except BlockingIOError:
                    pass

    def rootSend(self, payload):
        with self.rootLck:
            _totalBytes = self.rootCon.send(bytes(payload, 'utf8'))
            logging.info("[rootSend][ROOT] : Total sent {} bytes".format(_totalBytes))
            return _totalBytes

class NodeUtilities:
    def macAddressGetter(self, nodeNum) :
        with open('/sys/class/net/wpan{}/address'.format(nodeNum), 'r') as f :
            strng = f.readline()
            strng = b''.join(binascii.unhexlify(x) for x in strng[:-1].split(':')) # This should be ':' since MAC address is delimited by ':' only
            return strng

    def internalCounter(self):
        while True:
            if not self.counter :
                self.counter = 254
            else :
                self.counter -= 1
            self.evntObj.wait(10)
            logging.debug("node.nodeUtilities: [_internalCounter] self.counter {}".format(self.counter))
        return   

    def emptySocket(self, sock):
    # Remove the data present on the socket
        _input = [sock]
        while True:
            _inputReady, o, e = select.select(_input,[],[], 0.0)
            if not _inputReady.__len__(): 
                break
            for _sck in _inputReady:
                try:
                    _sck.recv(123)
                except BlockingIOError:
                    pass
        return

class PriCtrlPlaneUnit(NodeUtilities, RootNode, threading.Thread): # order in arg list is improtant it affects the inheritence order
    # It works for only one pkt format 41c8 broadcast with long source address
    #_ctlPlnThrd   = PriCtrlPlaneUnit(evntObj=_event_obj, sockLck=_sockLck, macRwsk=l2_sock, cachLck=_cachLck, cache=_cache, rootNode=_rootNodeThrd)
    def __init__(self, evntObj, sockLck, macRwsk, cachLck, cache, macAdrs=None, pktBffr=b'\x41\xc8\x00\xff\xff\xff\xff', rcvdPkt=[], nodeType='ccn', rootNode=None) :
        # Call the Thread class's init function
        threading.Thread.__init__(self)
        self.evntObj = evntObj      # Node's common clock
        self.sockLck = sockLck      # Socket Lock allowing atomicity
        self.cachLck = cachLck      # Node cache lock allowing atomicity
        self.macRwsk = macRwsk      # Node's MAC RAW socket
        self.cache   = cache      # Node's cache
        with self.cachLck :
            _getVal = self.cache['nod']
        if not macAdrs :
            self.macAdrs = self.macAddressGetter(_getVal)      # Node's MAC address
        else :
            self.macAdrs = macAdrs
        self.pktBffr = pktBffr      # Node's packet buffer
        self.rcvdPkt = rcvdPkt      # Received packet buffer
        if nodeType == 'ccn' :
            self.topic = None       # Node's self topic
        self.rootNod = rootNode
        # Preconfigured values
        self.counter = 254          # System Clock
        threading.Thread(target=self.internalCounter, args=()).start()
        self.nodeRnk = 254          # Node's rank in the network
        self.topic = self.macAdrs[-1:]
        logging.debug('[priCtrlPlaneUnit][TPC][SELF] : {}'.format(bytes(self.topic)))

        # Reference variable for length of cache 'pav'
        with self.cachLck:
            self.lenCachePav = str(self.cache['pav']).__len__()
        logging.debug('[priCtrlPlaneUnit][MAC][ADRS] : {}'.format(self.macAdrs))
            
        return

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

    def _recvProcess(self, log=False, clearBuffer=False):
        # [NOTE] Create mode_setting if to simulate low node, do not use list... instead use one packet at a time
        self.rcvdPkt = []
        # Recieve packets
        with self.sockLck:
            try:
                while True:
                    self.rcvdPkt.append(self.macRwsk.recvfrom(123))
            except BlockingIOError:
                log and logging.info('[_recvProcess][RCVD][PKT] : {}'.format(self.rcvdPkt))
            clearBuffer and threading.Thread(target=NodeUtilities.emptySocket, args=(self, self.macRwsk)).start()
        return

    def _pktProcessngProcess(self):
        for _rcvdPkt in self.rcvdPkt :
            _valHolder = [ False, False ] # If we have only one value, IndexError in line 173 
            """ Recevied message validity flags 
                [0] -> Valid conn req flag
                [1] -> Hold SDN msg
            """
            _tmpHld = str(_rcvdPkt[0]).split('>')
            logging.debug('[_pktProcessngProcess][PKT] : {}'.format(_tmpHld))
            
            for index in range(1, _tmpHld.__len__() - 1, 2): # Processing each attribute at a time for now
                _attribute = _tmpHld[index]                      # only one pair of attribute value is transmitted
                _value = _tmpHld[index+1]
                logging.debug('[_pktProcessngProcess][PKT] : {} {}'.format(_attribute, _value)) # Debug takes only str as argument

                # Connection request in packet
                if 'con' in _attribute :
                    if int(_value[1:]) > self.nodeRnk :
                        logging.info('[_pktProcessngProcess][CON] : {}'.format(_tmpHld[0][-2:]))
                        _valHolder[0] = True
                        continue
                    
                # New SDN message
                if 'sdn' in _attribute and 'True' in _value:
                    _valHolder[1] = True
                    continue
    
                if _valHolder[0] and 'nod' in _attribute :
                    with self.cachLck :
                        _getVal = self.cache['nod']
                    if not _getVal :
                        self.rootNod.rootSend(payload='con_req:' + _value)
                    else :
                        self._broadcastConnectionRequest(payload=_value)
                    continue

                # [NOTE] We may want process SDN message in _cacheConfigUpdation. Rantional : It makes sense there since we are al
                # ready updating cache which holds all the node's configuration
                if _valHolder[1] and 'rnk' in _attribute : # if we don't have _valHolder 'rnk' in _attribute contd will execute
                    if int(_value) < self.nodeRnk :
                        with self.cachLck:
                            self.cache['ctr']['sdn']['nm']  = True
                            self.cache['ctr']['sdn']['msg'] = _tmpHld[index+3] # value is stored here
                        pass

                # Rank in packet
                if 'rnk' in _attribute :
                    with self.cachLck:
                    # Rank setter
                        if int(_value) < self.nodeRnk :
                            self.nodeRnk = 2 * int(_value)
                            logging.info('[_pktProcessngProcess][SETG][RNK] : my rank is {}'.format(self.nodeRnk))
                            self.cache['pav'][str(_rcvdPkt[1][-1][0])] = dict(r=_value)
                            self.cache['ctr']['rnk']['brd'] = 3 # We're going to introduce ttl-like concept
                        # Receive down nodes' ranks                                   
                        elif int(_value) >= self.nodeRnk :
                            logging.info('[_pktProcessngProcess][RECV][RNK] : node {} rank {}'.format(_rcvdPkt[1][-1][0], _value))
                            self.cache['pav'][str(_rcvdPkt[1][-1][0])] = dict(r=_value)
                            logging.info('[_pktProcessngProcess][CACHE][PAV] : {}'.format(self.cache['pav']))
                        continue
            
                # Network map in packet
                if 'pav' in _attribute :
                    logging.info('[_pktProcessngProcess][RECV][PAV] : node {} lowerRank {}'.format(_rcvdPkt[1][-1][0], _value))
                    with self.cachLck:
                        try:    
                            if int(self.cache['pav'][str(_rcvdPkt[1][-1][0])]['r']) <= self.nodeRnk :
                                    continue
                        except (KeyError, TypeError):
                            pass

                        try:
                            self.cache['pav'][str(_rcvdPkt[1][-1][0])]['d'] = _value + 'D'
                        except KeyError:
                            self.cache['pav'][str(_rcvdPkt[1][-1][0])] = dict(d=(_value+'D'))
                        logging.debug('[_pktProcessngProcess][CACHE][PAV] : {}'.format(self.cache['pav']))
                    continue

        return

    def _broadcastProcess(self, sendBuffer):
        with self.sockLck:
            _totalBytes = self.macRwsk.send(sendBuffer + bytes(str(self.nodeRnk) + '>', 'utf8'))
        logging.info('[_broadcastProcess][SENT][PKT] : Total sent {} bytes'.format(_totalBytes))
        with self.cachLck:
            self.cache['ctr']['rnk']['brd'] -= 1
        return

    def _broadcastNetMap(self):
        _cachPav = None
        with self.cachLck:
            _cachPav = self.cache['pav']
        logging.debug('[_broadcastNetMap] _cachPav.__len__() {} refLenCachePav {} counter {}'.format(_cachPav.__len__(), self.lenCachePav, self.counter))

        try:
            with self.sockLck:
                _totalBytes = self.macRwsk.send(self.pktBffr + self.macAdrs + b'>pav>' + bytes(self.__dictToSerial(_cachPav), 'utf8') + b'>')
            logging.debug(self.__dictToSerial(_cachPav))
            logging.info('[_broadcastNetMap][SENT][PKT] : Total sent {} bytes'.format(_totalBytes))

            # Sending the network map towards controller
            with self.cachLck :
                _getVal = self.cache['nod']
            if not _getVal :
                self.rootNod.rootSend('net_map:' + self.__dictToSerial(_cachPav))
        except OSError:
            logging.warning(self.__dictToSerial(_cachPav))
        return

    def _broadcastConnectionRequest(self, payload=''):
        # Connection request is only inter domain communications
        # If communication reuest approved the specified nodes only cache the specific data
        with self.cachLck :
            _getVal = self.cache['nod']
        payload += '<' + str(_getVal)
        with self.sockLck:
            _totalBytes = self.macRwsk.send(self.pktBffr + self.macAdrs + b'>con>r' + bytes(str(self.nodeRnk), 'utf8') + b'>nod>' + bytes(payload, 'utf8') + b'>')
        
        logging.warning('[_broadcastConnectionRequest] payload {}'.format(payload))

        logging.info('[_broadcastConnectionRequest][SENT][PKT] : Total sent {} bytes'.format(_totalBytes))

        return

    def _cachConfigUpdation(self):
        _getVal = []
        with self.cachLck:
            _getVal.append(self.cache['ctr']['sdn']['nm'])
            _getVal.append(self.cache['ctr']['sdn']['msg'])
            # [NOTE] Write logic to process the type of SDN message
            # Clear the retrieved SDN message
            self.cache['ctr']['sdn']['nm'] = False
            self.cache['ctr']['rnk']['brd'] = False
            self.cache['ctr']['rnk']['m_brd'] = False
            _getVal.append(True) # Clear_flag for the remaining data in the socket
        if _getVal[0] :
            logging.warning("[_cachConfigUpdation] : _rcvData {}".format(_getVal[1]))
            self._broadcastProcess(self.pktBffr + self.macAdrs + bytes('>sdn>True' + '>rnk>' + str(self.nodeRnk) + '>msg>' + _getVal[1] + '>' , 'utf8'))
        if _getVal[2] :
            with self.sockLck :
                threading.Thread(target=NodeUtilities.emptySocket, args=(self, self.macRwsk)).start()
        return

    # Change log to control logging in this function
    def run(self, log=False):
        _sendBuffer = self.pktBffr + self.macAdrs + bytes('>rnk>', 'utf8')
        # Root node
        with self.cachLck :
            _getVal = self.cache['nod']
        if not _getVal and self.nodeRnk == 254 :
            self.nodeRnk = 1
            _sendBuffer += bytes(str(self.nodeRnk) + '>', 'utf8')
            with self.cachLck:
                self.cache['ctr']['rnk']['brd'] = 3
        # Node Process Begins
        while True :
            # Main continuous process

            # Receive function
            _getVal = None
            with self.cachLck:
                logging.debug("[run] self.cache {}".format(self.cache))
                _getVal = self.cache['ctr']['rcv'] 
            if _getVal :
                self._recvProcess()
                #log and logging.warning('[run] Receiving...')
                # Received packet processing
                if self.rcvdPkt.__len__() :
                    self._pktProcessngProcess()

            # Wait for next tick
            self.evntObj.wait(10)

            # Broadcast rank
            _getVal = None
            with self.cachLck:
                _getVal = self.cache['ctr']['rnk']['brd'] and self.cache['ctr']['rnk']['m_brd']
            if _getVal :
                self._broadcastProcess(_sendBuffer)
                log and logging.warning('[run] Broadcasting Rank...')

            # Process new configuration
            # [COMPLETED] should set a flag if I need to process this time can either from root thread or pkt processing function
            _getVal = None
            with self.cachLck:
                _getVal = self.cache['ctr']['sdn']['nm']
            if _getVal :
                self._cachConfigUpdation()

            # Connection request Broadcast
            _getVal = None
            with self.cachLck:
                _getVal = self.cache['ctr']['con']['brd']
            if _getVal and self.nodeRnk != 254 :
                self._broadcastConnectionRequest()
                log and logging.warning('[run] Broadcasting Connection Request...')
            
            # Broadcast network map
            _getVal = []
            with self.cachLck:
                _getVal.append(self.cache['ctr']['rnk']['m_brd'])
                if _getVal[0] :
                    _getVal.append(str(self.cache['pav']).__len__())
            if _getVal[0] and ( _getVal[1] != self.lenCachePav or not self.counter % MAP_EVRY_CNTR ) :
                self.lenCachePav = _getVal[1]
                with self.cachLck: 
                    logging.debug('[run] Broadcasting Map: self.cache[\'pav\'] {}'.format(self.cache['pav']))
                self._broadcastNetMap()
                log and logging.warning('[run] Broadcasting Network Map...')
        return

class PriDataPlaneUnit(threading.Thread, NodeUtilities):
    def __init__(self, macAdrs=None, pktBffr=b'\x41\xc8\x00\xff\xff\xff\xff'):
        threading.Thread.__init__(self)
        with self.cachLck :
            _getVal = self.cache['nod']
        if not macAdrs :
            self.macAdrs = self.macAddressGetter(_getVal)      # Node's MAC address
        else :
            self.macAdrs = macAdrs
        self.pktBffr = pktBffr + macAdrs
        return

    # This class must contain generic topic and data sender and receiver
    # [NOTE] Connection_request always belongs in control plane
    # Random intra-domain communication handler

    def run(self):
        while True :
            with self.sockLck :
                pass
        return
        
if __name__ == "__main__" :
    _rootNodeThrd    = None
    
    # Creating a threading lock
    _sockLck         = threading.Lock()
    _cachLck         = threading.Lock()
    # Temporary cache storage with limited capability of python dict
    # [INFO] Keep key in 3 characters for fast processing
    _cache   = {
        'nod': None, # Node number
        # may be hold the counter value when its changed, if the change is recent process it
        'ctr': {
            'rcv': 1,
            'rnk': {
                'brd': 0,
                'm_brd' : True
            },
            'con': {
                'req': None,
                'brd': None, 
            },
            'pri': [],
            'sdn': {
                'nm' : False, # New message
                'msg': ''     # Actual message
            },
        },
        'pav': {} # Dict of lower rank nodes
    }
    # Initialising an event object
    _event_obj = threading.Event()

    try:
        _cache['nod'] = int(sys.argv[1])
    except ValueError :
        raise Exception("Incorrect value for number of nodes")
    except IndexError :
        raise Exception("No value for number of nodes")

    # Create logging
    logging.basicConfig(
            filename='/home/priyan/code/sdn-iot-ip-icn/log/wpan{}.log'.
                format(_cache['nod']),
            filemode='a',
            level=logging.WARNING,
            format=("%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d "
            "%(message)s"),
            datefmt='%d/%m/%Y %H:%M:%S'
        )

    try:
        _cache['ctr']['con']['req'] = True if sys.argv[2] else None
        logging.warning("Connection request ON")
    except IndexError :
        pass
    try:
        _cache['ctr']['con']['brd'] if sys.argv[3] == 'a' else False
        logging.warning("AD HOC request ON")
    except IndexError :
        pass

    # Creating a common layer 2 socket between control and data plane
    l2_sock = socket.socket(family=socket.AF_PACKET, type=socket.SOCK_RAW, proto=socket.ntohs(0x0003))
    l2_sock.bind(('wpan{}'.format(_cache['nod']), 0, socket.PACKET_BROADCAST)) # _cache['nod'] is the node ID number
    l2_sock.setblocking(0)
    logging.warning('l2_socket established')

    _rootNodeThrd = RootNode(evntObj=_event_obj, cachLck=_cachLck, cache=_cache) if not _cache['nod'] else None
    _ctlPlnThrd   = PriCtrlPlaneUnit(evntObj=_event_obj, sockLck=_sockLck, macRwsk=l2_sock, cachLck=_cachLck, cache=_cache, rootNode=_rootNodeThrd)

    try:
        # we've created a class because in future we may have two separate sockets to
        # deal with control and data packets separately
        if _rootNodeThrd :
            _rootNodeThrd.start()
            logging.warning('Started Root Node...')
        _ctlPlnThrd.start()
        logging.warning('Started Control Plane...')
        #datPlnThrd = priDataPlaneUnit(l2_sock)
        #datPlnThrd.start()
        #logging.warning('started data plane')
        while True: # Without this hold up, the finally clause executes consecutively
            _event_obj.clear()
            time.sleep(TICK_TIME)
            _event_obj.set()
    finally:
        l2_sock.close()
        # Closing threads
        if _rootNodeThrd :
            _rootNodeThrd.join()
        _ctlPlnThrd.join()
        _thread.exit()