tme2int = lambda line : int(line[17:19] + line[20:23])

latVal = 0
sntCnt = 0
rcvCnt = 0
latLst = []
pdrLst = []
tmgDct = {}

def strSearcher(f1, strng):
    global tmgDct, sntCnt
    while True:
        try:
            _retVal = tmgDct[strng]
            tmgDct.__delitem__(strng)
            return _retVal
        except KeyError:
            line = f1.readline()
            _cmprStr = bytes(line.split(' ')[-1][:-1], encoding='utf-8')
            if 'Sending' in line :
                sntCnt += 1
                if strng == _cmprStr :
                    return tme2int(line)
                else :
                    tmgDct[_cmprStr] = tme2int(line)

def tally(f2, f1):
    global latVal, rcvCnt, sntCnt, tmgDct
    while True :
        line = f2.readline()
        if not line :
            latLst.append(latVal/rcvCnt)
            pdrLst.append(rcvCnt/sntCnt)
            print(latVal/rcvCnt, rcvCnt/sntCnt, tmgDct)
            return
        if 'Received' in line :
            _tmeIn = strSearcher(f1, bytes(line.split(' ')[-1][:-1], encoding='utf-8'))
            _tmeOt = tme2int(line)
            latVal += abs(_tmeOt - _tmeIn)
            rcvCnt += 1

for i in range(1, 6):
    f1 = open(f'/home/priyan/code/githubRepoOffline/sdn-iot-ip-icn/hetnet-gw/logs/802_11_IP/WLAN_node_{i}.log', 'r')
    f2 = open(f'/home/priyan/code/githubRepoOffline/sdn-iot-ip-icn/hetnet-gw/logs/802_15_4_CCN/WPAN_node_{i}.log', 'r')
    tally(f2, f1)
    # Resetting variables
    latVal = 0
    sntCnt = 0
    rcvCnt = 0
    tmgDct = {}
    f1.seek(0)
    f2.seek(0)
    tally(f1, f2)
    f1.close()
    f2.close()

print("\n\n\n", sum(latLst) / latLst.__len__())
print("\n\n\n", sum(pdrLst) / pdrLst.__len__())