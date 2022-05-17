#!/bin/bash

ip_mptcp=false
ip_mptcp_flags="subflow signal"

while getopts "p:" OPTION; do
  case "$OPTION" in
    p)
      if [ "$OPTARG" == "ip_mptcp" ]; then 
        shift 2
        ip_mptcp=true
      else
        echo "Unknown path manager!"
        exit 1
      fi
      ;;
    *)
      echo "Unknown option!"
      exit 1
  esac
done

table_count=0
while (( "$#" )); do
  table_count=$((table_count+1))
  interface=$1
  ipv4_gateway=$2

  ipv4=$(ifconfig $interface | awk '$1=="inet"{ print $2; }')
  netmask=$(ifconfig $interface | awk '$1=="inet"{ print $4; }')
  
  IFS=. read -r i1 i2 i3 i4 <<< "$ipv4"
  IFS=. read -r m1 m2 m3 m4 <<< "$netmask"

  subnet=$((i1 & m1)).$((i2 & m2)).$((i3 & m3)).$((i4 & m4))
  netmask=$(ip -o -4 addr list $interface | awk '{print $4}' | cut -d/ -f2)

  ip rule add from $ipv4 table $table_count

  ip route add $subnet/$netmask dev $interface scope link table $table_count

  ip route add default via $ipv4_gateway dev $interface table $table_count

  if $ip_mptcp ; then
    ip mptcp limits set subflows 8 add_addr_accepted 8 # Max values
    ip mptcp endpoint add $ipv4 dev $interface $ip_mptcp_flags
  fi

  shift 2
done
