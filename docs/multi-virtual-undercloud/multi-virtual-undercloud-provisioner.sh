#!/bin/bash

set -eux

VIRTHOST=$1
DISTRO=$2
VMNAME=$3
VMETH0IP=$4
VMETH0NM=$5
VMETH0GW=$6
VMSSHKEY=$7
UCVLAN=$8
UCEXTVLAN=$9

function wait_machine_status {
 UNDERCLOUD=$1
 STATUS=$2
 while true
  do
   nc $UNDERCLOUD 22 < /dev/null &> /dev/null
   NCSTATUS=$?
   if [ "$STATUS" == "up" ]
    then
     [ $NCSTATUS -eq 0 ] && break || (sleep 5; echo -n ".")
    else
     [ $NCSTATUS -ne 0 ] && break || (sleep 5; echo -n ".")
   fi
  done
}

# Copying public key on VIRTHOST
echo -n "$(date) - Copying $VMSSHKEY on $VIRTHOST: "
scp $VMSSHKEY root@$VIRTHOST:$VMNAME\_key.pub
echo "Done."

# Providing the machine
echo -n "$(date) - Starting provision of $VMNAME ($VMETH0IP) on $VIRTHOST: "
ssh root@$VIRTHOST /root/multi-virtual-undercloud.sh $DISTRO $VMNAME $VMETH0IP $VMETH0NM $VMETH0GW $VMNAME\_key.pub $UCVLAN $UCEXTVLAN
echo "Done."

set +e

# Wait for machine to come up
echo -n "$(date) - Waiting for $VMNAME to come up again after update: "
wait_machine_status $VMETH0IP "up"
echo "Done."
