#/bin/bash
n=`echo $1'*'$1 | bc`

for i in `seq 0 $n`
do
    ip netns del wpan$i
done

rmmod mac802154_hwsim