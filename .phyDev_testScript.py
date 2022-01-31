#!/usr/bin/python3

"""
KNOWN ISSUES: It detects whether the attached links are accurate or any 
missing links, but does not identify the missed link.
"""

import sys

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def _checkPrevNodeOK(x, node, nodeLinkCount):
    if node == 1 and nodeLinkCount == 4 or node == 0 and nodeLinkCount == 1:
        print(f"{bcolors.OKGREEN}[NODE OK]{bcolors.ENDC}")
    return

if __name__ == "__main__" :
    try:
        _x = int(sys.argv[2])
        with open(sys.argv[1], 'r') as fl :
            _nodeLinkCount = 0
            _node          = None
            _dirFlag       = 0xFF
            for line in fl.readlines() :
                line = line[:-1] # Removing trailing newline
                if 'radio' in line :
                    #print(line[line.index('o')+1:-1], end='')
                    _token = line[line.index('o')+1:]
                    if ':' in _token:
                        # New node begins
                        _checkPrevNodeOK(_x, _node, _nodeLinkCount)

                        _nodeLinkCount = 0
                        _node          = int(line[line.index('o')+1:-1]) # Removing trailing ':'
                        _dirFlag       = 0xFF
                        print(line)
                        continue
                    
                    _token = int(_token)

                    # Test begins
                    # Set the flags based on the nodes
                    _xx_1 = ( _x - 1 ) * _x + 1
                    if not _node % _x and not _node:
                        if _node == _x :
                            _dirFlag = 0x70
                        elif _node == _x * _x :
                            _dirFlag = 0xC1                           
                        else :
                            _dirFlag = 0xF1
                    elif _node % _x == 1 :
                        if _node == 1 :
                            _dirFlag = 0x9C
                        elif _node == _xx_1 :
                            _dirFlag = 0x07
                        else :
                            _dirFlag = 0x1F
                    elif _node < _x and _node > 1 :
                        _dirFlag = 0x7C
                    elif _node % _x > 1 and _node > _xx_1 :
                        _dirFlag = 0xC7           
                    elif not _node :
                        _dirFlag = 0x40

                    #       NE  E   SE  S   SW  W   NW  N
                    #       0   1   2   3   4   5   6   7   

                    #flag and northEast
                    if _dirFlag and 0x80:
                        _dirFlag = _dirFlag & 0b01111111
                        pass
                    #flag and east
                    if _dirFlag and 0x40:
                        _dirFlag = _dirFlag & 0b10111111
                        pass
                    #flag and southEast
                    if _dirFlag and 0x20:
                        _dirFlag = _dirFlag & 0b10111111
                        pass
                    #flag and south
                    if _dirFlag and 0x10:
                        _dirFlag = _dirFlag & 0b10111111
                        pass
                    #flag and southWest
                    if _dirFlag and 0x8:
                        _dirFlag = _dirFlag & 0b10111111
                        pass
                    #flag and west
                    if _dirFlag and 0x4:
                        _dirFlag = _dirFlag & 0b10111111
                        pass
                    #flag and northWest
                    if _dirFlag and 0x2:
                        _dirFlag = _dirFlag & 0b10111111
                        pass
                    #flag and north
                    if _dirFlag and 0x1:
                        _dirFlag = _dirFlag & 0b10111111
                        pass

                    
                        # Set feedback flag and return missing direction


    except IndexError:
        raise Exception("No file provided!")
