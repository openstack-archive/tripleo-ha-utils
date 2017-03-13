stonith-config
==============

This role acts on an already deployed tripleo environment, setting up STONITH (Shoot The Other Node In The Head) inside the Pacemaker configuration for all the hosts that are part of the overcloud.

Requirements
------------

This role must be used with a deployed TripleO environment, so you'll need a working directory of tripleo-quickstart with these files:

- **hosts**: which will contain all the hosts used in the deployment;
- **ssh.config.ansible**: which will have all the ssh data to connect to the undercloud and all the overcloud nodes;
- **instackenv.json**: which must be present on the undercloud workdir. This should be created by the installer;

Quickstart invocation
---------------------

Quickstart can be invoked like this:

    ./quickstart.sh \
       --retain-inventory \
       --playbook overcloud-stonith-config.yml \
       --working-dir /path/to/workdir \
       --config /path/to/config.yml \
       --release <RELEASE> \
       --tags all \
       <HOSTNAME or IP>

Basically this command:

- **Keeps** existing data on the repo (it's the most important one)
- Uses the *overcloud-stonith-config.yml* playbook
- Uses the same custom workdir where quickstart was first deployed
- Select the specific config file
- Specifies the release (mitaka, newton, or “master” for ocata)
- Performs all the tasks in the playbook overcloud-stonith-config.yml

**Important note**

You might need to export *ANSIBLE_SSH_ARGS* with the path of the *ssh.config.ansible* file to make the command work, like this:

    export ANSIBLE_SSH_ARGS="-F /path/to/quickstart/workdir/ssh.config.ansible"

STONITH configuration
---------------------

STONITH configuration relies on the same **instackenv.json** file used by TripleO to configure Ironic and all the provision stuff.
Basically this role enable STONITH on the Pacemaker cluster and takes all the information from the mentioned file, creating a STONITH resource for each host on the overcloud.
After running this playbook th cluster configuration will have this property:

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

Having all this in place is a requirement for a reliable HA solution and for configuring special OpenStack features like [Instance HA](https://github.com/redhat-openstack/tripleo-quickstart-utils/tree/master/roles/instance-ha).

**Note**: by default this role configures STONITH for all the overcloud nodes, but it is possible to limitate it just for controllers, or just for computes, by setting the **stonith_devices** variable, which by default is set to "all", but can also be "*controllers*" or "*computes*".

Limitations
-----------

The only kind of STONITH devices supported are **for the moment** IPMI.

Example Playbook
----------------

The main playbook couldn't be simpler:

    ---
    - name:  Configure STONITH for all the hosts on the overcloud
      hosts: undercloud
      gather_facts: no
      roles:
        - stonith-config

But it could also be used at the end of a deployment, like the validate-ha role is used in [baremetal-undercloud-validate-ha.yml](https://github.com/redhat-openstack/tripleo-quickstart-utils/blob/master/playbooks/baremetal-undercloud-validate-ha.yml).

License
-------

GPL

Author Information
------------------

Raoul Scarazzini <rasca@redhat.com>
