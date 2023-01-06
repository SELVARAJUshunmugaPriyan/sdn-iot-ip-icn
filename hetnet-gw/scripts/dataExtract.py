tme2int = lambda line : int(line[17:19] + line[20:23])
meanLat = 0
meanDrpCnt = 0
cont = 1

def strSearcher(f1, strng):
    _drpCnt = 0
    while True:
        line = f1.readline()
        if 'Sending' in line :
            _drpCnt += 1
            if strng == line.split(' ')[-1][:-1] :
                print(line, end='')
                global meanDrpCnt
                meanDrpCnt += _drpCnt
                return tme2int(line)

def tally(f2, f1):
    try:
        while True :
            line = f2.readline()
            if not line :
                break
            if 'Received' in line :
                print(line, end='')
                strng = line.split(' ')[-1][:-1]
                tmeIn = strSearcher(f1, strng)
                tmeOut = tme2int(line)
                if abs(tmeOut - tmeIn) < 10000 :
                    meanLat += abs(tmeOut - tmeIn)
                    cont += 1
    except KeyboardInterrupt:
        print(meanLat/cont, cont/meanDrpCnt)
        f1.close()
        f2.close()

for i in range(1, 6):
    f1 = open(f'/home/priyan/code/githubRepoOffline/sdn-iot-ip-icn/hetnet-gw/logs/802_11_IP/WLAN_node_{i}.log', 'r')
    f2 = open(f'/home/priyan/code/githubRepoOffline/sdn-iot-ip-icn/hetnet-gw/logs/802_15_4_CCN/WPAN_node_{i}.log', 'r')