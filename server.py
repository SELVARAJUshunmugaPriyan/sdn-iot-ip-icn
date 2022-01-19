#!/usr/bin/python3
import socket
from _thread import *
import threading
  
print_lock = threading.Lock()

def threaded(c):
    c.setblocking(0)
    #print_lock.release()
    try:
        while True:
            try:
                data = c.recv(1024)
                print(data)           
            except BlockingIOError:
                pass
    finally:
        c.close()
  
def Main():
    host = ""
    port = 12345
    with socket.socket() as s :
        s.bind((host, port))
        print("socket binded to port", port)
        s.listen(5)
        print("socket is listening")
        while True:
            c, addr = s.accept()
            #print_lock.acquire()
            print('Connected to :', addr[0], ':', addr[1])
            start_new_thread(threaded, (c,))
    
if __name__ == '__main__':
    Main()