#!/usr/bin/python3
from socket     import *
from time       import sleep
import logging
import _thread
import threading
  
print_lock = threading.Lock()

class PavSdnCntrlr() :
    def __init__(self) :
        pass

    def networkMapper (strng):
        dic = {}
        downRouteFlag = False
        i = 0
        startNode = ''
        if not isinstance(strng, str):
            raise TypeError
        while i < strng.__len__():
            if strng[i] == '0' :
                if strng[i+2] == 'r' :
                    logging.debug("[NMPPR][FUNC] {} dic {}".format(i, dic))
                    try:
                        dic[strng[i+1]]['r'] = strng[i+3]
                    except KeyError:
                        dic[strng[i+1]] = dict(r=strng[i+3], v='')
                    if downRouteFlag :
                        dic[strng[i+1]]['v'] += startNode
                i += 3
            elif strng[i] == 'd':
                downRouteFlag = True
                startNode += strng[i-3] + ','
                logging.debug("[NMPPR][FUNC] startNode {}".format(startNode))
            elif strng[i] == 'D':
                downRouteFlag = False
                startNode = ' '
            i += 1
        return dic


def __networkMapper (self, strng):
    dic = {}
    downRouteFlag = False
    i = 0
    startNode = ''
    if not isinstance(strng, str):
        raise TypeError
    while i < strng.__len__():
        if strng[i] == '0' :
            if strng[i+2] == 'r' :
                logging.debug("[NMPPR][FUNC] {} dic {}".format(i, dic))
                try:
                    dic[strng[i+1]]['r'] = strng[i+3]
                except KeyError:
                    dic[strng[i+1]] = dict(r=strng[i+3], v='')
                if downRouteFlag :
                    dic[strng[i+1]]['v'] += startNode
            i += 3
        elif strng[i] == 'd':
            downRouteFlag = True
            startNode += strng[i-3] + ','
            logging.debug("[NMPPR][FUNC] startNode {}".format(startNode))
        elif strng[i] == 'D':
            downRouteFlag = False
            startNode = ' '
        i += 1
    return dic

def threaded(c):
    c.setblocking(0)
    #print_lock.release()
    try:
        while True:
            try:
                data = c.recv(1024)
                if data :
                    logging.info(data)           
            except BlockingIOError:
                pass
    finally:
        c.close()
  
def Main():
    host = ''
    port = 5001
    with socket() as s :
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind((host, port))
        logging.info("socket binded to port", port)
        s.listen(5)
        logging.info("socket is listening")
        while True:
            c, addr = s.accept()
            #print_lock.acquire()
            logging.info('Connected to :', addr[0], ':', addr[1])
            _thread.start_new_thread(threaded, (c,))
    
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
    Main()