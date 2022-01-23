#!/bin/bash

if [ "$EUID" -ne 0 ]; then
	echo "ERROR: REQUIRED Run as root user"
	exit
fi

if [ -z "$1" ]; then
	echo "ERROR: REQUIRED No value for X in X x X grid network"
	exit
fi

rmmod mac802154_hwsim
rmmod mac802154
rmmod ieee802154_6lowpan
rmmod ieee802154
modprobe mac802154_hwsim

numberOfNodes=`echo $1'*'$1 | bc`

if [ -z "$2" ]; then
	echo "MISSING: OPTIONAL value for number of communicating nodes"
else
	if [ $2 -ge $numberOfNodes ]; then
		echo "Invalid number of communication nodes"
		exit
	fi
	# Generating a list of communicating nodes
	declare -a commNodesLst
	# Generating end-to-end communication use case
	commNodesLst+=(9)

	typeset i=$(($2-1))
	typeset RANDOM=$$
	typeset inarray=0
	
	while [ $i -gt 0 ]; do
		typeset randVal=$(($(($RANDOM%$numberOfNodes))+1))
		inarray=0

		for j in "${!commNodesLst[@]}"; do
			if [ "${commNodesLst[$j]}" = "$randVal" ]; then
				inarray=1
			fi
		done
		if [ $inarray -eq 1 ]; then
			continue
		fi

		commNodesLst+=($randVal)
		i=$((i-1))
	done
fi

if [ -z "$3" ]; then
	echo "MISSING: OPTIONAL SDN mode configuration defaulting to managed mode"
else
	if [ $3 = 'a' ]; then
		echo "ADHOC mode enabled"
	fi
	if [ $3 = 's' ]; then
		echo "SDN mode enabled"
	fi
fi

echo "Communication nodes are ${commNodesLst[@]}"

for i in `seq 0 $numberOfNodes`
	do	wpan-hwsim add
done

# BUILD TOPOLOGY
for i in `seq 0 $numberOfNodes`; do	
	# CONFIGURE NETWORK NAMESPACE
	ip netns add wpan$i
	
	if [ $i == 0 ]; then
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
		if [ `expr "$i" % $1` != 0 ]; then
			# East
			eval "wpan-hwsim edge add "$i' '`expr $i + 1`
		    eval "wpan-hwsim edge add "`expr $i + 1`' '$i
		fi
		if [ `expr "$i" % $1` != 0 -a $i -lt `expr $numberOfNodes - $1 + 1` ]; then
			# SouthEast
			eval "wpan-hwsim edge add "$i' '`expr $i + $1 + 1`
		    eval "wpan-hwsim edge add "`expr $i + $1 + 1`' '$i
		fi
		if [ $i -lt `expr $numberOfNodes - $1 + 1` ];then
			# South
			eval "wpan-hwsim edge add "$i' '`expr $i + $1`
		    eval "wpan-hwsim edge add "`expr $i + $1`' '$i
		fi
		if [ `expr "$i" % $1` != 1 -a $i -lt `expr $numberOfNodes - $1 + 1` ];then
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

	# STARTING THE NODE PYTHON PROCESS
	arg="$i"
	for j in "${!commNodesLst[@]}"; do
		if [ "${commNodesLst[$j]}" =  $i ]; then
			arg="$i CONN_REQ_ON $3"
		fi
	done
	ip netns exec wpan$i /home/priyan/code/sdn-iot-ip-icn/node.py $arg &>>/home/priyan/code/sdn-iot-ip-icn/log/wpan$i.log &
done
