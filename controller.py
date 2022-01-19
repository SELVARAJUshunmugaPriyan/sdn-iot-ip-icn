#!/usr/bin/python3
from socket     import *
from time       import sleep
import logging
import _thread

SDN_CONTROLLER_ADDRESS = '10.0.254.1' 
SDN_CONTROLLER_PORT = 14323

class PavSdnCntrlr() :
    def __init__(self, networkMap=None) :
        self.networkMap = networkMap if networkMap else {}

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

    def _threaded(self, conn):
        conn.setblocking(0)
        try:
            while True:
                try:
                    self._routeManager(self._networkMapper(str(conn.recv(1024))))
                    logging.info(self.networkMap)          
                except BlockingIOError:
                    pass
        finally:
            conn.close()
  
    def ServerProcess(self):
        with socket() as sck :
            sck.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            sck.bind((SDN_CONTROLLER_ADDRESS, SDN_CONTROLLER_PORT))
            logging.info("socket binded to port", SDN_CONTROLLER_PORT)
            sck.listen(5)
            logging.info("socket is listening")
            while True:
                client, addr = sck.accept()
                logging.info('Connected to :', addr[0], ':', addr[1])
                _thread.start_new_thread(self._threaded, (client,))
    
if __name__ == "__main__" :
    # Create logging
    logging.basicConfig(
            filename='/home/priyan/code/sdn-iot-ip-icn/log/controller.log',
            filemode='a',
            level=logging.INFO,
            format=("%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d "
            "%(message)s"),
            datefmt='%d/%m/%Y %H:%M:%S'
        )
    icnCtlr = PavSdnCntrlr()
    icnCtlr.ServerProcess()
