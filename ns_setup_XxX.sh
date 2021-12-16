#!/bin/bash

rmmod mac802154_hwsim
rmmod mac802154
rmmod ieee802154_6lowpan
rmmod ieee802154
modprobe mac802154_hwsim

n=`echo $1'*'$1 | bc`

for i in `seq 0 $n`
do
	wpan-hwsim add
done

# BUILD TOPOLOGY
for i in `seq 0 $n`
do
	if [ "$i" == 0 ]
	then
		eval "wpan-hwsim edge add "$i' '`expr $i + 1`
	        eval "wpan-hwsim edge add " `expr $i + 1`' '$i
	else
		if [ "$i" -gt `expr $1 + 1` -a `expr "$i" % $1` != 1 ]
		then
			eval "wpan-hwsim edge add "$i' '`expr $i - $1 + 1`
		        eval "wpan-hwsim edge add " `expr $i - $1 + 1`' '$i
		fi
		if [ "$i" -gt $1 -a `expr "$i" % $1` != 0 ]
		then
			eval "wpan-hwsim edge add "$i' '`expr $i - $1 - 1`
		        eval "wpan-hwsim edge add " `expr $i - $1 - 1`' '$i
		fi
		if [ `expr "$i" % $1` != 0 ]
		then
			eval "wpan-hwsim edge add "$i' '`expr $i + 1`
		        eval "wpan-hwsim edge add " `expr $i + 1`' '$i
		fi
		if [ "$i" -lt `expr $n - $1 + 1` ]
		then
			eval "wpan-hwsim edge add "$i' '`expr $i + $1`
		        eval "wpan-hwsim edge add " `expr $i + $1`' '$i
		fi
	fi
	ip netns add wpan$i
	iwpan phy phy$i set netns name wpan$i
	ip netns exec wpan$i iwpan dev wpan$i set pan_id 0xbeef
	#ip netns exec wpan$i ip link add link wpan$i name lowpan$i type lowpan
	ip netns exec wpan$i ip link set wpan$i up
	#ip netns exec wpan$i ip link set lowpan$i up 
	ip netns exec wpan$i /home/priyan/code/C/notes/sdn-iot-ip-cin/Init_icn_wpan_indv_nds.py $i &
done
