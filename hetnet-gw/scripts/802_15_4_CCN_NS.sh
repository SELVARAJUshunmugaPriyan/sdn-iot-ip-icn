#!/bin/bash

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: REQUIRED Run as root user"
    exit
fi

if [ -z "$1" ]; then
    echo "ERROR: REQUIRED No value entered for number of nodes in star topology"
    exit
fi

if [ -z "$2" ]; then
    echo "WARNING: OPTIONAL No value entered for loss percentage (default: 0)"
    lossPercentage=0
else
    lossPercentage=$2
fi

rmmod mac802154_hwsim
rmmod mac802154
rmmod ieee802154_6lowpan
rmmod ieee802154
modprobe mac802154_hwsim

for i in `seq 0 $1`
    do wpan-hwsim add
done

#sudo python3 /home/priyan/github-repo-offline/sdn-iot-ip-icn/hetnet-gw/scripts/hetnet-gw.py &>>/dev/null &

# BUILD TOPOLOGY
for i in `seq 1 $1`; do
    # CONFIGURE NETWORK NAMESPACE
    ip netns add wpan$i

    eval "wpan-hwsim edge add "$i' 0'
    eval "wpan-hwsim edge add 0 "$i

    # CONFIGURE NETWORK INTERFACE
    iwpan phy phy$i set netns name wpan$i
    ip netns exec wpan$i ip link set dev wpan$i down
    ip netns exec wpan$i ip link set dev wpan$i address 00:12:37:00:00:00:00:$i
    ip netns exec wpan$i iwpan dev wpan$i set pan_id 0xbeef
    ip netns exec wpan$i ip link set dev wpan$i up

    ip netns exec wpan$i sudo python3 /home/priyan/code/githubRepoOffline/sdn-iot-ip-icn/hetnet-gw/scripts/802_15_4_CCN.py $i $lossPercentage &>>/dev/null &

done

sleep 10000