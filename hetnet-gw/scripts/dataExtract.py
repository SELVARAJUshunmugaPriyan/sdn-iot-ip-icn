tme2int = lambda line : int(line[17:19] + line[20:23])
latency = 0
# meanDrpCnt = 0
cont = 1
latnLst = []

def strSearcher(f1, strng):
    f1.seek(0)
    _drpCnt = 0
    global meanDrpCnt
    while True:
        line = f1.readline()
        if 'Sending' in line :
            _drpCnt += 1
            if strng == line.split(' ')[-1][:-1] :
                # print(line, end='')
                # meanDrpCnt += _drpCnt
                return tme2int(line)

def tally(f2, f1):
    # print(f2, f1)
    global latency, cont
    while True :
        line = f2.readline()
        if not line :
            latnLst.append(latency/cont)
            print(latency/cont) #, cont/meanDrpCnt)
            return
        if 'Received' in line :
            # print(line, end='')
            strng = line.split(' ')[-1][:-1]
            tmeIn = strSearcher(f1, strng)
            tmeOut = tme2int(line)
            if abs(tmeOut - tmeIn) < 10000 :
                # print(tmeOut, tmeIn)
                latency += abs(tmeOut - tmeIn)
                cont += 1

for i in range(1, 5):
    f1 = open(f'/home/priyan/code/githubRepoOffline/sdn-iot-ip-icn/hetnet-gw/logs/802_11_IP/WLAN_node_{i}.log', 'r')
    f2 = open(f'/home/priyan/code/githubRepoOffline/sdn-iot-ip-icn/hetnet-gw/logs/802_15_4_CCN/WPAN_node_{i}.log', 'r')
    tally(f2, f1)
    latency = 0
    # meanDrpCnt = 0
    cont = 1
    f1.seek(0)
    f2.seek(0)
    tally(f1, f2)
    f1.close()
    f2.close()

print("\n\n\n", sum(latnLst) / latnLst.__len__())