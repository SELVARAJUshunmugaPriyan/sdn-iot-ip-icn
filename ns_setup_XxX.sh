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
	# CONFIGURE NETWORK NAMESPACE
	ip netns add wpan$i
	
	if [ $i == 0 ]
	then
		eval "wpan-hwsim edge add "$i' '`expr $i + 1`
	    eval "wpan-hwsim edge add "`expr $i + 1`' '$i
		# CONFIGURE VIRTUAL LINK TOWARDS SDN CONTROLLER
		ip link add tunnel_start type veth peer name tunnel_end
		ip link set tunnel_end netns wpan0
		ip link set dev tunnel_start up
		ip a add 10.0.254.1/24 dev tunnel_start
		ip netns exec wpan0 ip link set dev tunnel_end up
		ip netns exec wpan0 ip a add 10.0.254.2/24 dev tunnel_end
		# STARTING CONTROLLER
		/home/priyan/code/sdn-iot-ip-icn/controller.py &>>/home/priyan/code/sdn-iot-ip-icn/log/controller.log &
	else
		if [ `expr "$i" % $1` != 0 ]
		then
			# East
			eval "wpan-hwsim edge add "$i' '`expr $i + 1`
		    eval "wpan-hwsim edge add "`expr $i + 1`' '$i
		fi
		if [ `expr "$i" % $1` != 0 -a $i -lt `expr $n - $1 + 1` ]
		then
			# SouthEast
			eval "wpan-hwsim edge add "$i' '`expr $i + $1 + 1`
		    eval "wpan-hwsim edge add "`expr $i + $1 + 1`' '$i
		fi
		if [ $i -lt `expr $n - $1 + 1` ]
		then
			# South
			eval "wpan-hwsim edge add "$i' '`expr $i + $1`
		    eval "wpan-hwsim edge add "`expr $i + $1`' '$i
		fi
		if [ `expr "$i" % $1` != 1 -a $i -lt `expr $n - $1 + 1` ]
		then
			# SouthWest
			eval "wpan-hwsim edge add "$i' '`expr $i + $1 - 1`
		    eval "wpan-hwsim edge add "`expr $i + $1 - 1`' '$i
		fi
	fi

	# CONFIGURE NETWORK INTERFACE
	iwpan phy phy$i set netns name wpan$i
	#ip netns exec wpan$i ip link set wpan$i down
	ip netns exec wpan$i ip link set dev wpan$i down
	ip netns exec wpan$i ip link set dev wpan$i address 00:12:37:00:00:00:00:$i
	ip netns exec wpan$i iwpan dev wpan$i set pan_id 0xbeef
	ip netns exec wpan$i ip link set dev wpan$i up
	#ip netns exec wpan$i ip link add link wpan$i name lowpan$i type lowpan
	#ip netns exec wpan$i ip link set wpan$i up
	#ip netns exec wpan$i ip link set lowpan$i up 
	ip netns exec wpan$i /home/priyan/code/sdn-iot-ip-icn/node_v*.py $i &>>/home/priyan/code/sdn-iot-ip-icn/log/wpan$i.log &
done
