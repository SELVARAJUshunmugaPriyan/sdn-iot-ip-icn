#!/usr/bin/python3
import socket
import time
import threading
import _thread
import logging
import node

SDN_CONTROLLER_ADDRESS  = '10.0.254.1' 
SDN_CONTROLLER_PORT     = 14323
MSGS_BEFORE_STOP_MAP    = 5

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
        logging.warning("[_deltaFinder] _lenMapPav {} _delta {} _rtBul {}".format(_lenMapPav, _delta, _rtBul))
        return _rtBul

    def _networkMapper (self, strng):
        networkMapUpd = {}
        downRouteFlag = False
        index = 0
        startNode = ''
        if not isinstance(strng, str):
            raise TypeError
        while index < strng.__len__():
            if strng[index] == '0' :
                if strng[index+2] == 'r' :
                    logging.debug("[_networkMapper] index {} networkMapUpd {}".format(index, networkMapUpd))

                    rank = strng[index+3:index+5] if strng[index+4] not in ('D', 'd', '0') else strng[index+3] # If rank is in two digits and this is why its helpful in keep ranks in power of 2's since it will not end with '0'
                    try:
                        networkMapUpd[strng[index+1]]['r'] = rank
                    except KeyError:
                        networkMapUpd[strng[index+1]] = dict(r=rank, v='')
                    if downRouteFlag :
                        if startNode not in networkMapUpd[strng[index+1]]['v'] :
                            networkMapUpd[strng[index+1]]['v'] += ' ' + startNode
                index += 3
            elif strng[index] == 'd':
                downRouteFlag = True
                startNode += strng[index-3] + ','
                logging.debug("[_networkMapper] startNode {}".format(startNode))

            elif strng[index] == 'D':
                downRouteFlag = False
                startNode = ' '
            index += 1
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
                if self._deltaFinder() :
                    _valBfrStop = MSGS_BEFORE_STOP_MAP
                    _countNoted = self.counter
                else :
                    _valBfrStop -= 1
            if not _valBfrStop  or (_countNoted == (self.counter - 40)) :
                _valBfrStop = 1
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