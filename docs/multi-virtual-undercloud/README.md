Multi Virtual Undercloud
========================

This document describes a way to deploy multiple virtual undercloud on the same
host. This is mainly for environments in which you want to manage multiple
baremetal overclouds without having one baremetal machine dedicated for each one
you deploy.

Requirements
------------

**Physical switches**

The switch(es) must support VLAN tagging and all the ports must be configured in
trunk, so that the dedicated network interface on the physical host (in the 
examples the secondary interface, eth1) is able to offer PXE and dhcp to all the
overcloud machines via undercloud virtual machine's bridged interface.

**Host hardware**

The main requirement to make this kind of setup working is to have a host 
powerful enough to run virtual machines with at least 16GB of RAM and 8 cpus.
The more power you have, the more undercloud machines you can spawn without
having impact on performances.

**Host Network topology**

Host is reachable via ssh from the machine launching quickstart and configured 
with two main network interfaces:

- **eth0**: bridged on **br0**, pointing to LAN (underclouds will own an IP to
  be reachable via ssh);
- **eth1**: connected to the dedicated switch that supports all the VLANs that
  will be used in the deployment;

Over eth1, for each undercloud virtual machine two VLAN interfaces are created, 
with associated bridges:

- **Control plane network bridge** (i.e. br2100) built over VLAN interface (i.e. 
  eth1.2100) that will be eth1 on the undercloud virtual machine, used by 
  TripleO as br-ctlplane;
- **External network bridge** (i.e. br2105) built over VLAN interface (i.e. 
  eth1.2105) that will be eth2 on the undercloud virtual machine, used by 
  TripleO as external network device;

![network-topology](./multi-virtual-undercloud_network-topology.png "Multi Virtual Undercloud - Network Topology")

Quickstart configuration
------------------------

Virtual undercloud machine is treated as a baremetal one and the Quickstart 
command relies on the baremetal undercloud role, and its playbook.
This means that any playbook similar to [baremetal-undercloud.yml](https://github.com/openstack/tripleo-quickstart-extras/blob/master/playbooks/baremetal-undercloud.yml "Baremetal undercloud playbook") should be okay.

The configuration file has two specific sections that needs attention:

- Additional interface for external network to route overcloud traffic:
  
  ```yaml
  undercloud_networks:
     external:
       address: 172.20.0.254
       netmask: 255.255.255.0
       device_type: ethernet
       device_name: eth2
  ```
  
  **NOTE:** in this configuration eth2 is acting also as a default router for 
  the external network.

- Baremetal provision script, which will be an helper for the
  [multi-virtual-undercloud.sh](./multi-virtual-undercloud.sh) script on the <VIRTHOST>:
  
  ```yaml
   baremetal_provisioning_script: "/path/to/multi-virtual-undercloud-provisioner.sh <VIRTHOST> <DISTRO> <UNDERCLOUD-NAME> <UNDERCLOUD IP> <UNDERCLOUD NETMASK> <UNDERCLOUD GATEWAY> <CTLPLANEV LAN> <EXTERNAL NETWORK VLAN>"
  ```
  
  The supported parameters, with the exception of VIRTHOST, are the same ones 
  that are passed to the script that lives (and runs) on the VIRTHOST,
  *multi-virtual-undercloud.sh*.
  This helper script launches the remote command on VIRTHOST host and ensures 
  that the machine gets reachable via ssh before proceeding.

The multi virtual undercloud script
-----------------------------------

The [multi-virtual-undercloud.sh](./multi-virtual-undercloud.sh) script is 
placed on the VIRTHOST and needs these parameters:

1. **DISTRO**: this must be the name (without extension) of one of the images 
   present inside the */images* dir on the VIRTHOST;
2. **VMNAME**: the name of the undercloud virtual machine (the name that will be
   used by libvirt);
3. **VMETH0IP**: IP of the virtual undercloud primary interface to wich
   quickstart (and users) will connect via ssh;
4. **VMETH0NM**: Netmask of the virtual undercloud primary interface;
5. **VMETH0GW**: Gateway of the virtual undercloud primary interface;
6. **VMSSHKEY**: Public key to be enabled on the virtual undercloud;
7. **UCVLAN**: VLAN of the overcloud's ctlplane network;
8. **UCEXTVLAN**: VLAN of the overcloud's external network;

The script's actions are basically:

1. Destroy and undefine any existing machine named as the one we want to create;
2. Prepare the image on which the virtual undercloud will be created by copying
   the available distro image and preparing it to be ready for the TripleO
   installation, it fix size, network interfaces, packages and ssh keys;
3. Create and launch the virtual undercloud machine;

**Note**: on the VIRTHOST there must exist an */images* directory containing 
images suitable for the deploy.
Having this directory structure:

```console
[root@VIRTHOST ~]# ls -l /images/
total 1898320
lrwxrwxrwx.  1 root root         34 14 feb 09.20 centos-7.qcow2 -> CentOS-7-x86_64-GenericCloud.qcow2
-rw-r--r--.  1 root root 1361182720 15 feb 10.57 CentOS-7-x86_64-GenericCloud.qcow2
lrwxrwxrwx.  1 root root         36 14 feb 09.20 rhel-7.qcow2 -> rhel-guest-image-7.3-33.x86_64.qcow2
-rw-r--r--.  1 root root  582695936 19 ott 18.44 rhel-guest-image-7.3-33.x86_64.qcow2
```

Helps on updating the images, since one can leave config files pointing to
*centos-7* and, in case of updates, make the symlink point a newer image.

Quickstart command
------------------

A typical invocation of the TripleO Quickstart command is something similar to
this:

```console
/path/to/tripleo-quickstart/quickstart.sh \
  --bootstrap \
  --ansible-debug \
  --no-clone \
  --playbook baremetal-undercloud.yml \
  --working-dir /path/to/workdir \
  --config /path/to/config.yml \
  --release $RELEASE \
  --tags "all" \
  $VIRTHOST
```

So nothing different from a normal quickstart deploy command line, the 
difference here is made by the config.yml as described above, with its provision 
script.

Conclusions
-----------

This approach can be considered useful in testing multi environments with
TripleO for three reasons:

* It is *fast*: it takes the same time to install the undercloud but less to 
  provide it, since you don’t have to wait the physical undercloud provision;
* It is *isolated*: using VLANs to separate the traffic keeps each environment 
  completely isolated from the others;
* It is *reliable*: you can have the undercloud on a shared storage and think 
  about putting the undercloud vm in HA, live migrating it with libvirt, 
  pacemaker, whatever...

There are no macroscopic cons, except for the initial configuration on the
VIRTHOST, that is made only one time, at the beginning.

License
-------

GPL

Author Information
------------------

Raoul Scarazzini <rasca@redhat.com>
