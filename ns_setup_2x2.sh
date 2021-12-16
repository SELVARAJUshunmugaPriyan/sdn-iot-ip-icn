#!/bin/bash

rmmod mac802154_hwsim
rmmod mac802154
rmmod ieee802154_6lowpan
rmmod ieee802154
modprobe mac802154_hwsim

for i in `seq 0 4`
do
	wpan-hwsim add
done

# BUILD TOPOLOGY
for i in `seq 0 4`
do
	if [ "$i" == 0 ]
	then
			eval "wpan-hwsim edge add "$i' '`expr $i + 1`
	        eval "wpan-hwsim edge add " `expr $i + 1`' '$i
	else
		if [ "$i" == 1 ]
		then
			eval "wpan-hwsim edge add "$i' '`expr $i + 1`
	        eval "wpan-hwsim edge add " `expr $i + 1`' '$i
	        eval "wpan-hwsim edge add "$i' '`expr $i + 2`
	        eval "wpan-hwsim edge add " `expr $i + 2`' '$i
	        eval "wpan-hwsim edge add "$i' '`expr $i + 3`
	        eval "wpan-hwsim edge add " `expr $i + 3`' '$i
		fi
		if [ "$i" == 2 ]
		then
			eval "wpan-hwsim edge add "$i' '`expr $i + 1`
	        eval "wpan-hwsim edge add " `expr $i + 1`' '$i
	        eval "wpan-hwsim edge add "$i' '`expr $i + 2`
	        eval "wpan-hwsim edge add " `expr $i + 2`' '$i
		fi
		if [ "$i" == 3 ]
		then
			eval "wpan-hwsim edge add "$i' '`expr $i + 1`
	        eval "wpan-hwsim edge add " `expr $i + 1`' '$i
		fi
	fi

	# CONFIGURE NETWORK NAMESPACE 
	ip netns add wpan$i
	iwpan phy phy$i set netns name wpan$i
	# CONFIGURE NETWORK INTERFACE
	#ip netns exec wpan$i ip link set wpan$i down
	ip netns exec wpan$i ip link set dev wpan$i down
	ip netns exec wpan$i ip link set dev wpan$i address 00:12:37:00:00:00:00:$i
	ip netns exec wpan$i iwpan dev wpan$i set pan_id 0xbeef
	ip netns exec wpan$i ip link set dev wpan$i up
	#ip netns exec wpan$i ip link add link wpan$i name lowpan$i type lowpan
	#ip netns exec wpan$i ip link set wpan$i up
	#ip netns exec wpan$i ip link set lowpan$i up 
	ip netns exec wpan$i /home/priyan/code/sdn-iot-ip-icn/Init_icn_wpan_indv_nds.py $i &>>/home/priyan/code/sdn-iot-ip-icn/log/wpan$i.log &
done
