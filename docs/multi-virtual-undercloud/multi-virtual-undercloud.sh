#!/bin/bash

set -eux

DISTRO=$1
CLONEFROM=/images/$DISTRO\.qcow2
VMNAME=$2
VMIMG=/vms/$VMNAME\.qcow2
VMIMGCOPY=/vms/ORIG-$VMNAME\.qcow2
VMETH0IP=$3
VMETH0NM=$4
VMETH0GW=$5
VMSSHKEY=$6
VMDISKADD=50G
UCVLAN=$7
UCEXTVLAN=$8
WORKDIR=/tmp/virt-undercloud-$(date +%s)

mkdir -p $WORKDIR
pushd $WORKDIR

# Destroy the machine if it is running
ISRUNNING=$(virsh list | grep $VMNAME || true)
[ "x$ISRUNNING" != "x" ] && virsh destroy $VMNAME

# Undefine the vm if it is defined
ISDEFINED=$(virsh list --all | grep $VMNAME || true)
[ "x$ISDEFINED" != "x" ] && virsh undefine $VMNAME

# Copy qcow2 base image
cp -v $CLONEFROM $VMIMG

echo "$(date) - Adding $VMDISKADD to $VMIMG: "
qemu-img resize $VMIMG +$VMDISKADD

echo "$(date) - Resizing filesystem of $VMIMG: "
cp -v $VMIMG $VMIMGCOPY
virt-resize --expand /dev/sda1 $VMIMGCOPY $VMIMG
rm -fv $VMIMGCOPY

echo "$(date) - Checking status of $VMIMG: "
qemu-img info $VMIMG
virt-filesystems --long -h --all -a $VMIMG

cat > ifcfg-eth0 <<EOF
NAME=eth0
DEVICE=eth0
ONBOOT=yes
BOOTPROTO=static
IPADDR=$VMETH0IP
NETMASK=$VMETH0NM
GATEWAY=$VMETH0GW
PEERDNS=yes
DNS1=8.8.8.8
TYPE=Ethernet
EOF

cat > ifcfg-eth1 <<EOF
NAME=eth1
DEVICE=eth1
ONBOOT=yes
BOOTPROTO=none
TYPE=Ethernet
EOF

cat $VMSSHKEY >> ./authorized_keys

case "$DISTRO" in
"centos-7") virt-customize -a $VMIMG \
             --root-password password:redhat \
             --install openssh-server \
             --run-command "xfs_growfs /" \
             --run-command "echo 'GRUB_CMDLINE_LINUX=\"console=tty0 crashkernel=auto no_timer_check net.ifnames=0 console=ttyS0,115200n8\"' >> /etc/default/grub" \
             --run-command "grubby --update-kernel=ALL --args=net.ifnames=0" \
             --run-command "systemctl enable sshd" \
             --mkdir /root/.ssh \
             --copy-in ifcfg-eth0:/etc/sysconfig/network-scripts/ \
             --copy-in ifcfg-eth1:/etc/sysconfig/network-scripts/ \
             --copy-in ./authorized_keys:/root/.ssh/ \
             --selinux-relabel
            ;;
"rhel-7") virt-customize -a $VMIMG \
           --root-password password:redhat \
           --run-command "curl -o rhos-release-latest.noarch.rpm http://rhos-release.virt.bos.redhat.com/repos/rhos-release/rhos-release-latest.noarch.rpm" \
           --run-command "rpm -Uvh rhos-release-latest.noarch.rpm" \
           --run-command "rhos-release rhel-7.3" \
           --install openssh-server \
           --run-command "systemctl enable sshd" \
           --run-command "rpm -e rhos-release" \
           --run-command "sed -i -e '/\[rhelosp-rhel-7.3-server-opt\]/,/^\[/s/enabled=0/enabled=1/' /etc/yum.repos.d/rhos-release-rhel-7.3.repo" \
           --mkdir /root/.ssh \
           --copy-in ifcfg-eth0:/etc/sysconfig/network-scripts/ \
           --copy-in ifcfg-eth1:/etc/sysconfig/network-scripts/ \
           --copy-in ./authorized_keys:/root/.ssh/ \
           --selinux-relabel
          ;;
esac

# Deploy the vm
virt-install \
 --import \
 --name $VMNAME \
 --ram 16192 \
 --disk path=$VMIMG \
 --vcpus 8 \
 --os-type linux \
 --os-variant generic \
 --network bridge=br0 \
 --network bridge=br$UCVLAN \
 --network bridge=br$UCEXTVLAN \
 --graphics none \
 --noautoconsole

rm -rf $WORKDIR
popd
