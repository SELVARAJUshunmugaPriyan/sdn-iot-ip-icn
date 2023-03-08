tme2int = lambda line : int(line[17:19] + line[20:23])

latVal = 0
sntCnt = 0
rcvCnt = 1
latLst = []
pdrLst = []
tmgDct = {}

def getSntCnt(f1):
    f1.seek(0)
    global sntCnt
    for line in f1.readlines():
        if 'Sending' in line :
            sntCnt += 1
    return

def strSearcher(f1, strng):
    f1.seek(0)
    while True:
        line = f1.readline()
        if 'Sending' in line :
            if strng == line.split(' ')[-1][:-1] :
                # print(line, end='')
                return tme2int(line)
            # else :
            #     tmgDct[]

def tally(f2, f1):
    # print(f2, f1)
    global latVal, rcvCnt, sntCnt
    while True :
        line = f2.readline()
        if not line :
            getSntCnt(f1)
            latLst.append(latVal/rcvCnt)
            pdrLst.append(rcvCnt/sntCnt)
            print(latVal/rcvCnt, rcvCnt/sntCnt)
            return
        if 'Received' in line :
            # print(line, end='')
            strng = line.split(' ')[-1][:-1]
            tmeIn = strSearcher(f1, strng)
            tmeOut = tme2int(line)
            if abs(tmeOut - tmeIn) < 10000 :
                # print(tmeOut, tmeIn)
                latVal += abs(tmeOut - tmeIn)
                rcvCnt += 1

for i in range(1, 6):
    f1 = open(f'/home/priyan/code/githubRepoOffline/sdn-iot-ip-icn/hetnet-gw/logs/802_11_IP/WLAN_node_{i}.log', 'r')
    f2 = open(f'/home/priyan/code/githubRepoOffline/sdn-iot-ip-icn/hetnet-gw/logs/802_15_4_CCN/WPAN_node_{i}.log', 'r')
    tally(f2, f1)
    latVal = 0
    sntCnt = 0
    rcvCnt = 1
    f1.seek(0)
    f2.seek(0)
    tally(f1, f2)
    f1.close()
    f2.close()

print("\n\n\n", sum(latLst) / latLst.__len__())
print("\n\n\n", sum(pdrLst) / pdrLst.__len__())