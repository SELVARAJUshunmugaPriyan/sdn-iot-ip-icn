#/bin/bash
n=`echo $1'*'$1 | bc`

for i in `seq 0 $n`
do
    ip netns del wpan$i
done

if [ $2 = "y" ]
then
    read -p "Are you sure you want to delete all log files?(y/n)" j
    if [ $j = "y" ]
    then
        rm -rf /home/priyan/code/sdn-iot-ip-icn/log/*
    fi
fi

rmmod mac802154_hwsim