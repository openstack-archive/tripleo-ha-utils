stonith-config
==============

This role acts on an already deployed tripleo environment, setting up STONITH
(Shoot The Other Node In The Head) inside the Pacemaker configuration for all
the hosts that are part of the overcloud.

Requirements
------------

The TripleO environment must be prepared as described [here](https://github.com/openstack/tripleo-ha-utils/tree/master/README.md).

STONITH
-------

STONITH is the way a Pacemaker clusters use to be certain that a node is powered
off. STONITH is the only way to use a shared storage environment without
worrying about concurrent writes on disks. Inside TripleO environments STONITH
is a requisite also for activating features like Instance HA because, before
moving any machine, the system need to be sure that the "move from" machine is
off.
STONITH configuration relies on the **instackenv.json** file, used by TripleO
also to configure Ironic and all the provision stuff.
Basically this role enables STONITH on the Pacemaker cluster and takes all the
information from the mentioned file, creating a STONITH resource for each host
on the overcloud.
After running this playbook the cluster configuration will have this properties:

    $ sudo pcs property
    Cluster Properties:
     cluster-infrastructure: corosync
     cluster-name: tripleo_cluster
     ...
     ...
     **stonith-enabled: true**

And something like this, depending on how many nodes are there in the overcloud:

    sudo pcs stonith
     ipmilan-overcloud-compute-0    (stonith:fence_ipmilan):        Started overcloud-controller-1
     ipmilan-overcloud-controller-2 (stonith:fence_ipmilan):        Started overcloud-controller-0
     ipmilan-overcloud-controller-0 (stonith:fence_ipmilan):        Started overcloud-controller-0
     ipmilan-overcloud-controller-1 (stonith:fence_ipmilan):        Started overcloud-controller-1
     ipmilan-overcloud-compute-1    (stonith:fence_ipmilan):        Started overcloud-controller-1

Having all this in place is a requirement for a reliable HA solution and for
configuring special OpenStack features like [Instance HA](https://github.com/openstack/tripleo-ha-utils/tree/master/roles/instance-ha).

**Note**: by default this role configures STONITH for the controllers nodes,
but it is possible to configure all the nodes or to limitate it just for
computes, by setting the **stonith_devices** variable, which by default is set
to "controllers", but can also be "*all*" or "*computes*".

Limitations
-----------

The only kind of STONITH devices supported are **for the moment** IPMI.

Examples on how to invoke the playbook via ansible
--------------------------------------------------

This command line will install the STONITH devices for the controller nodes:

    ansible-playbook /home/stack/tripleo-ha-utils/playbooks/overcloud-stonith-config.yml

If a user wants to install the STONITH devices for all the nodes:

    ansible-playbook /home/stack/tripleo-ha-utils/playbooks/overcloud-stonith-config.yml -e stonith_devices="all"

To uninstall the STONITH devices for the controllers:

    ansible-playbook /home/stack/tripleo-ha-utils/playbooks/overcloud-stonith-config.yml -e stonith_action="uninstall"

To uninstall the STONITH devices just for the computes:

    ansible-playbook /home/stack/tripleo-ha-utils/playbooks/overcloud-stonith-config.yml -e stonith_action="uninstall" -e stonith_devices="computes"

The STONITH role supports also "none" as a valid value for *stonith_devices*
which can become useful when configuring instance HA in an environment already
configured with STONITH for both controllers and computes.

License
-------

GPL

Author Information
------------------

Raoul Scarazzini <rasca@redhat.com>
