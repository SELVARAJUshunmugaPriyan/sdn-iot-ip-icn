#!/usr/bin/python3
import socket
import time
import threading
import _thread
import logging
import node

SDN_CONTROLLER_ADDRESS  = '10.0.254.1' 
SDN_CONTROLLER_PORT     = 14323
MSGS_BEFORE_STOP_MAP    = 143
TRICKLE_TIME            = 143

class PavSdnCntrlr(threading.Thread, node.NodeUtilities) :
    def __init__(self, evntObj=None, networkMap=None) :
        threading.Thread.__init__(self)
        self.networkMap     = networkMap if networkMap else {}
        self.lock           = threading.Lock()
        self.evntObj        = evntObj
        self.counter        = 254
        self.lenMapPav_r    = str(self.networkMap).__len__()
        self.flags          = {
            'map' : {
                'rdy' : False
            }
        }

    def _deltaFinder(self):
        _rtBul = False
        _lenMapPav = str(self.networkMap).__len__()
        _delta = int((abs(_lenMapPav - self.lenMapPav_r) / self.lenMapPav_r ) * 100)
        if _delta > 10 :
            self.lenMapPav_r = _lenMapPav
            _rtBul = True
        logging.debug("[_deltaFinder] _lenMapPav {} _delta {} _rtBul {}".format(_lenMapPav, _delta, _rtBul))
        return _rtBul

    def _networkMapper (self, strng):
        networkMapUpd = {}
        downRouteFlag = False
        index = 0
        startNode = ''
        logging.debug("[_networkMapper] strng {}".format(strng))
        if not isinstance(strng, str):
            raise TypeError
        while index < strng.__len__():
            if strng[index] in '0123456789' :
                logging.debug("[_networkMapper] strng[index] {}".format(strng[index]))
                if strng[index+2] == 'r' :
                    logging.debug("[_networkMapper] index {} networkMapUpd {}".format(index, networkMapUpd))
                    
                    _rank = ''
                    try:
                        if strng[index+4] not in ('D', 'd', '0') :
                            _rank = strng[index+3:index+5]
                        else :
                            _rank = strng[index+3]
                    except IndexError:
                        _rank = strng[index+3] 
                    """ If rank is in two digits and this is why its helpful in keep ranks in power of 2's since it will not end with '0'"""
                    logging.debug("[_networkMapper] {} _rank {}".format(strng[index:index+5], _rank))
                    try:
                        networkMapUpd[strng[index:index+2]]['r'] = _rank
                        logging.debug("[_networkMapper] strng[index:index+2] {}".format(strng[index:index+2]))
                    except KeyError:
                        networkMapUpd[strng[index:index+2]] = dict(r=_rank, v='')
                        logging.debug("[_networkMapper] {}".format(strng[index:index+2]))
                    if downRouteFlag :
                        logging.debug("[_networkMapper] startNode {} strng[index+1] {}".format(startNode, strng[index:index+2]))
                        if startNode not in networkMapUpd[strng[index:index+2]]['v'] :
                            networkMapUpd[strng[index:index+2]]['v'] += ' ' + startNode
                index += 3
            elif strng[index] == 'd':
                downRouteFlag = True
                if not startNode or startNode == ' ':
                    startNode += strng[index-4:index-2]
                else :
                    startNode += ',' + strng[index-4:index-2]
                logging.debug("[_networkMapper] startNode {}".format(startNode))

            elif strng[index] == 'D':
                downRouteFlag = False
                if not startNode :
                    startNode = ' '
            index += 1
        logging.debug("[_networkMapper] networkMapUpd {}".format(networkMapUpd))
        return networkMapUpd

    # Redundant function can be improved after cleaning the network_map sent towards controller
    # till then this function must be used to periodically clean the network_map dictionary.
    def _routeManager(self, networkMapUpd):
        for i in networkMapUpd.keys() :
            try:
                self.networkMap[i]['r'] =  networkMapUpd[i]['r']
            except KeyError :
                self.networkMap[i] = dict(r=networkMapUpd[i]['r'])
            via = networkMapUpd[i]['v']
            via = [ [ y for y in x.split(',') if y ] for x in via.split(' ') if x ]
            logging.debug("[_routeManager] Before: i {} networkMapUpd[i][\'r\'] {} via {}".format(i, networkMapUpd[i]['r'], via))

            j = via.__len__()
            while j :
                j -= 1
                logging.debug("[_routeManager] via[j] {} via[j][0] {} networkMapUpd[via[j][0]] {}".format(via[j], via[j][0], networkMapUpd[via[j][0]]))

                if networkMapUpd[via[j][0]]['r'] != '2' or i in via[j] :
                    via.remove(via[j])
            try:
                gen = (x for x in via if x not in self.networkMap[i]['v'])
                for x in gen :
                    self.networkMap[i]['v'].append(x) 
            except KeyError :
                self.networkMap[i]['v'] = via
            logging.debug("[_routeManager] After: i {} networkMapUpd[i][\'r\'] {} via {}".format(i, networkMapUpd[i]['r'], via))
            
        # self.networkMap[i]['v'] = list of tuples after cleaning organised by number of hops. This is the function that can be improved to accommodate ML techniques

    def _manage(self, conn):
        with conn: # this thread will be running forever so it can finally
                # close the socket not inother threads
            while True:
                with self.lock:
                    try:
                        _rcvData = str(conn.recv(1024))
                        if 'con_req' in _rcvData :
                            logging.warning("[_manage][RECV][CON] Receieved message {}".format(_rcvData))
                        if 'net_map' in _rcvData :
                            self.flags['map']['rdy'] = True
                            _rcvData = _rcvData[10:-1] # -1 is a dirty hack
                            if _rcvData and 'r' in _rcvData:
                                self._routeManager(self._networkMapper(_rcvData))
                                logging.warning("[_manage][RECV][MAP] Receieved message {}".format(self.networkMap))
                    except BlockingIOError:
                        pass
        return

    def _monitor(self, conn):
        # Monitor progress of network mapping
        # If it slows below 10 % for 10 consecutive values, we instruct stop the network mapping down the network
        # **** We have to think about periodic updates later
        _valBfrStop = MSGS_BEFORE_STOP_MAP
        _countNoted = 0
        while True:
            self.evntObj.wait(10)
            if self.flags['map']['rdy'] :
                self.flags['map']['rdy'] = False
                if self._deltaFinder() : # > 10% True
                    _valBfrStop = MSGS_BEFORE_STOP_MAP
                    _countNoted = self.counter - TRICKLE_TIME
                else :
                    _valBfrStop -= 1
            if not _valBfrStop  or ( self.counter <  _countNoted and self.counter > _countNoted - 3) :
                _valBfrStop = MSGS_BEFORE_STOP_MAP
                with self.lock:
                    _totalBytes = conn.send(b"net_map_stop")
                logging.info("[_monitor][SNT][CTL] Total sent {} bytes".format(_totalBytes))
        return

    def run(self):
        
        # Starting the internal counter
        threading.Thread(target=self.internalCounter, args=()).start() # threading.
        with socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0) as sck :
            sck.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sck.bind((SDN_CONTROLLER_ADDRESS, SDN_CONTROLLER_PORT))
            logging.info("socket binded to port {}".format(SDN_CONTROLLER_PORT))
            sck.listen(5)
            logging.info("socket is listening")
            try:
                while True:
                    client, addr = sck.accept()
                    client.setblocking(0)
                    logging.info('Connected to : {}:{}'.format(addr[0], addr[1]))
                    threading.Thread(target=self._manage, args=(client,)).start() # threading.
                    threading.Thread(target=self._monitor, args=(client,)).start() # threading.
            finally:
                _thread.exit() # _thread.
        return
    
if __name__ == "__main__" :
    # Creating a common clock
    _evntObj = threading.Event() # threading. * Cannot 'with'
    
    # Create logging
    logging.basicConfig(
            filename='/home/priyan/code/sdn-iot-ip-icn/log/controller.log',
            filemode='a',
            level=logging.INFO,
            format=("%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d "
            "%(message)s"),
            datefmt='%d/%m/%Y %H:%M:%S'
        )
    
    sdnCtrlThrd = PavSdnCntrlr(evntObj=_evntObj)
    #icnCtlr.ServerProcess()

    try:
        sdnCtrlThrd.start()
        logging.warning('SDN process started')

        while True:
            _evntObj.clear()
            time.sleep(1)
            _evntObj.set()

    finally:
        sdnCtrlThrd.join()