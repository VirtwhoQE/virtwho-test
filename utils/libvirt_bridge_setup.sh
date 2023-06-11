#!/usr/bin/env bash

# If you want to delete the bridge and recovery the original network:
# nmcli c del $br_name
# nmcli c del $DEV_CON
# nmcli c add type ethernet autoconnect yes con-name $DEV_CON ifname $DEV

usage() {
   echo "Usage: $0 -b BRIDGE_NAME"
   exit 1
}

while getopts "b:" opt; do
   case "$opt" in
      b)  br_name="$OPTARG" ;;
      ?)  usage ;;
  esac
done

if [ -z "$br_name" ]; then
   usage
fi

DEV=$(ip route get 8.8.8.8 | awk 'NR==2 {print $1}' RS='dev')
DEV_CON=$(nmcli device show $DEV | grep 'GENERAL.CONNECTION' | awk -F':' '{print $2}' | awk '$1=$1')
IP=$(nmcli device show $DEV | grep 'IP4.ADDRESS' | awk '{print $2}')
GW=$(nmcli device show $DEV | grep 'IP4.GATEWAY' | awk '{print $2}')
DNS1=$(nmcli device show $DEV | grep 'IP4.DNS\[1\]' | awk '{print $2}')
DNS2=$(nmcli device show $DEV | grep 'IP4.DNS\[2\]' | awk '{print $2}')
DNS3=$(nmcli device show $DEV | grep 'IP4.DNS\[3\]' | awk '{print $2}')
NIC=$(ethtool -i $DEV | grep 'driver' | awk -F':' '{print $2}')

if [[ $DEV != $br_name ]]; then
    nmcli c del "$DEV_CON"
    nmcli c add type bridge autoconnect yes con-name $br_name ifname $br_name
    nmcli c add type bridge-slave autoconnect yes con-name "$DEV_CON" ifname $DEV master $br_name
    nmcli c modify $br_name bridge.stp no
    nmcli c modify $br_name ipv6.method disabled
    nmcli c modify $br_name ipv4.ignore-auto-dns yes
    nmcli c modify $br_name ipv4.ignore-auto-routes yes
    nmcli c modify $br_name ipv4.method manual ipv4.addresses $IP ipv4.gateway $GW
    nmcli c modify $br_name ipv4.dns $DNS1,$DNS2,$DNS3
    modprobe -r $NIC
    modprobe $NIC
    nmcli c down $br_name
    nmcli c up "$DEV_CON"
    nmcli c up $br_name
else
    echo "The bridge $br_name is already exist!"
fi
