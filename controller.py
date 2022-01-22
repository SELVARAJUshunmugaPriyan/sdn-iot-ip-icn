#!/usr/bin/python3
from socket     import *
from time       import sleep
from threading  import Lock, Thread, Event
from _thread    import exit
import logging

SDN_CONTROLLER_ADDRESS = '10.0.254.1' 
SDN_CONTROLLER_PORT = 14323

class PavSdnCntrlr(Thread) :
    def __init__(self, sleepEvent=None, networkMap=None) :
        self.networkMap = networkMap if networkMap else {}
        self.lock       = Lock()
        self.sleepEvent = sleepEvent
        self.counter    = 254

    def _deltaFinder(self):
        pass

    def _internalCounter(self):
        while True:
            if not self.counter :
                self.counter = 254
            else :
                self.counter -= 1
            self.sleepEvent.wait()
            logging.warning("[INTCTR][FUNC] self.counter {}".format(self.counter))
        return

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
                    logging.debug("[NMPPR][FUNC] {} networkMapUpd {}".format(index, networkMapUpd))

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
                logging.debug("[NMPPR][FUNC] startNode {}".format(startNode))

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
            logging.debug('Before: i {} networkMapUpd[i][\'r\'] {} via {}'.format(i, networkMapUpd[i]['r'], via))

            j = via.__len__()
            while j :
                j -= 1
                logging.debug("via[j] {} via[j][0] {} networkMapUpd[via[j][0]] {}".format(via[j], via[j][0], networkMapUpd[via[j][0]]))

                if networkMapUpd[via[j][0]]['r'] != '2' or i in via[j] :
                    via.remove(via[j])
            try:
                gen = (x for x in via if x not in self.networkMap[i]['v'])
                for x in gen :
                    self.networkMap[i]['v'].append(x) 
            except KeyError :
                self.networkMap[i]['v'] = via
            logging.debug('After: i {} networkMapUpd[i][\'r\'] {} via {}'.format(i, networkMapUpd[i]['r'], via))
            
        # self.networkMap[i]['v'] = list of tuples after cleaning organised by number of hops. This is the function that can be improved to accommodate ML techniques

    def _manage(self, conn):
        with conn: # this thread will be running forever so it can finally
                # close the socket not inother threads
            while True:
                with self.lock:
                    try:
                        _rcvData = str(conn.recv(1024))
                        if 'con_req' in _rcvData :
                            logging.warning(_rcvData)
                        else :
                            self._routeManager(self._networkMapper(_rcvData))
                            logging.warning(self.networkMap)
                    except BlockingIOError:
                        pass
        return

    def _monitor(self, conn):
        #_lenMapPav = str(self.networkMap).__len__()
        #while True:
        for i in range(10):
            self.sleepEvent.wait()
            logging.warning("[_monitor] self.counter {}".format(self.counter))
            # _delta = _lenMapPav / str(self.networkMap).__len__()
            # if _delta > 1.0 :
            #     _delta /= _delta
            # _delta *= 100            
            # if _delta > 10 :
            #     _lenMapPav.append(str(self.networkMap).__len__())
                # Monitor progress of network mapping
                # If it slows below 10 % for 60 s, we instruct stop the network mapping down the network
                # **** We have to think about periodic updates later
        return

    def run(self):
        
        # Starting the internal counter
        Thread(target=self._internalCounter, args=()).start() # threading.
        with socket(AF_INET, SOCK_STREAM, 0) as sck :
            sck.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            sck.bind((SDN_CONTROLLER_ADDRESS, SDN_CONTROLLER_PORT))
            logging.info("socket binded to port", SDN_CONTROLLER_PORT)
            sck.listen(5)
            logging.info("socket is listening")
            try:
                while True:
                    client, addr = sck.accept()
                    client.setblocking(0)
                    logging.info('Connected to :', addr[0], ':', addr[1])
                    Thread(target=self._manage, args=(client,)).start() # threading.
                    Thread(target=self._monitor, args=(client,)).start() # threading.
            finally:
                exit() # _thread.
        return
    
if __name__ == "__main__" :
    # Creating a common clock
    _sleepEvent = Event() # threading. * Cannot 'with'
    
    # Create logging
    logging.basicConfig(
            filename='/home/priyan/code/sdn-iot-ip-icn/log/controller.log',
            filemode='a',
            level=logging.INFO,
            format=("%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d "
            "%(message)s"),
            datefmt='%d/%m/%Y %H:%M:%S'
        )
    
    sdnCtrlThrd = PavSdnCntrlr(sleepEvent=_sleepEvent)
    #icnCtlr.ServerProcess()

    try:
        sdnCtrlThrd.start()
        logging.warning('SDN process started')

        #sleepEvent.set()
        sleep(1)

    finally:
        pass