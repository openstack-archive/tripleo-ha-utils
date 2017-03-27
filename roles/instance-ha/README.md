instance-ha
===========

This role aims to automate all the steps needed to configure instance HA on a
deployed (via tripleo-quickstart) overcloud environment. For more information
about Instance HA, see the [IHA Documentation](https://access.redhat.com/documentation/en-us/red_hat_openstack_platform/9/html-single/high_availability_for_compute_instances/)

Requirements
------------

This role must be used with a deployed TripleO environment, so you'll need a
working directory of tripleo-quickstart or in any case these files available:

- **hosts**: which will contain all the hosts used in the deployment;
- **ssh.config.ansible**: which will have all the ssh data to connect to the
  undercloud and all the overcloud nodes;

**NOTE**: Instance-HA depends on STONITH. This means that all the steps
performed by this role make sense only if on the overcloud STONITH has been
configured. There is a dedicated role that automates the STONITH
configuration, named [stonith-config](https://github.com/redhat-openstack/tripleo-quickstart-utils/tree/master/roles/stonith-config).

Instance HA
-----------

Instance HA is a feature that gives a certain degree of high-availability to the
instances spawned by an OpenStack deployment. Namely, if a compute node on which
an instance is running breaks for whatever reason, this configuration will spawn
the instances that were running on the broken node onto a functioning one.
This role automates are all the necessary steps needed to configure Pacemaker
cluster to support this functionality. A typical cluster configuration on a
clean stock **newton** (or **osp10**) deployment is something like this:

    Online: [ overcloud-controller-0 overcloud-controller-1 overcloud-controller-2 ]

    Full list of resources:

     ip-192.168.24.10       (ocf::heartbeat:IPaddr2):       Started overcloud-controller-0
     ip-172.18.0.11 (ocf::heartbeat:IPaddr2):       Started overcloud-controller-0
     ip-172.20.0.19 (ocf::heartbeat:IPaddr2):       Started overcloud-controller-1
     ip-172.17.0.11 (ocf::heartbeat:IPaddr2):       Started overcloud-controller-1
     ip-172.19.0.12 (ocf::heartbeat:IPaddr2):       Started overcloud-controller-0
     Clone Set: haproxy-clone [haproxy]
         Started: [ overcloud-controller-0 overcloud-controller-1 overcloud-controller-2 ]
     Master/Slave Set: galera-master [galera]
         Masters: [ overcloud-controller-0 overcloud-controller-1 overcloud-controller-2 ]
     ip-172.17.0.18 (ocf::heartbeat:IPaddr2):       Started overcloud-controller-1
     Clone Set: rabbitmq-clone [rabbitmq]
         Started: [ overcloud-controller-0 overcloud-controller-1 overcloud-controller-2 ]
     Master/Slave Set: redis-master [redis]
         Masters: [ overcloud-controller-0 ]
         Slaves: [ overcloud-controller-1 overcloud-controller-2 ]
     openstack-cinder-volume        (systemd:openstack-cinder-volume):      Started overcloud-controller-0

As you can see we have 3 controllers, six IP resources, four *core* resources
(*haproxy*, *galera*, *rabbitmq* and *redis*) and one last resource which is
*openstack-cinder-volume* that needs to run as a single active/passive resource
inside the cluster.  This role configures all the additional resources needed
to have a working instance HA setup.  Once the playbook is executed, the
configuration will be something like this:

    Online: [ overcloud-controller-0 overcloud-controller-1 overcloud-controller-2 ]
    RemoteOnline: [ overcloud-compute-0 overcloud-compute-1 ]

    Full list of resources:

     ip-192.168.24.10       (ocf::heartbeat:IPaddr2):       Started overcloud-controller-0
     ip-172.18.0.11 (ocf::heartbeat:IPaddr2):       Started overcloud-controller-0
     ip-172.20.0.19 (ocf::heartbeat:IPaddr2):       Started overcloud-controller-1
     ip-172.17.0.11 (ocf::heartbeat:IPaddr2):       Started overcloud-controller-1
     ip-172.19.0.12 (ocf::heartbeat:IPaddr2):       Started overcloud-controller-0
     Clone Set: haproxy-clone [haproxy]
         Started: [ overcloud-controller-0 overcloud-controller-1 overcloud-controller-2 ]
         Stopped: [ overcloud-compute-0 overcloud-compute-1 ]
     Master/Slave Set: galera-master [galera]
         Masters: [ overcloud-controller-0 overcloud-controller-1 overcloud-controller-2 ]
         Stopped: [ overcloud-compute-0 overcloud-compute-1 ]
     ip-172.17.0.18 (ocf::heartbeat:IPaddr2):       Started overcloud-controller-1
     Clone Set: rabbitmq-clone [rabbitmq]
         Started: [ overcloud-controller-0 overcloud-controller-1 overcloud-controller-2 ]
         Stopped: [ overcloud-compute-0 overcloud-compute-1 ]
     Master/Slave Set: redis-master [redis]
         Masters: [ overcloud-controller-0 ]
         Slaves: [ overcloud-controller-1 overcloud-controller-2 ]
         Stopped: [ overcloud-compute-0 overcloud-compute-1 ]
     openstack-cinder-volume        (systemd:openstack-cinder-volume):      Started overcloud-controller-0
     ipmilan-overcloud-compute-0    (stonith:fence_ipmilan):        Started overcloud-controller-1
     ipmilan-overcloud-controller-2 (stonith:fence_ipmilan):        Started overcloud-controller-0
     ipmilan-overcloud-controller-0 (stonith:fence_ipmilan):        Started overcloud-controller-0
     ipmilan-overcloud-controller-1 (stonith:fence_ipmilan):        Started overcloud-controller-1
     ipmilan-overcloud-compute-1    (stonith:fence_ipmilan):        Started overcloud-controller-1
     nova-evacuate  (ocf::openstack:NovaEvacuate):  Started overcloud-controller-0
     Clone Set: nova-compute-checkevacuate-clone [nova-compute-checkevacuate]
         Started: [ overcloud-compute-0 overcloud-compute-1 ]
         Stopped: [ overcloud-controller-0 overcloud-controller-1 overcloud-controller-2 ]
     Clone Set: nova-compute-clone [nova-compute]
         Started: [ overcloud-compute-0 overcloud-compute-1 ]
         Stopped: [ overcloud-controller-0 overcloud-controller-1 overcloud-controller-2 ]
     fence-nova     (stonith:fence_compute):        Started overcloud-controller-0
     overcloud-compute-1    (ocf::pacemaker:remote):        Started overcloud-controller-0
     overcloud-compute-0    (ocf::pacemaker:remote):        Started overcloud-controller-1

Since there are a lot of differences from a stock deployment, understanding
the way Instance HA works can be quite hard, so additional information around
Instance HA is available at [this link](https://github.com/rscarazz/tripleo-director-instance-ha/blob/master/README.md).

Quickstart invocation
---------------------

Quickstart can be invoked like this:

    ./quickstart.sh \
       --retain-inventory \
       --playbook overcloud-instance-ha.yml \
       --working-dir /path/to/workdir \
       --config /path/to/config.yml \
       --release <RELEASE> \
       --tags all \
       <HOSTNAME or IP>

Basically this command:

- **Keeps** existing data on the repo (it's the most important one)
- Uses the *overcloud-instance-ha.yml* playbook
- Uses the same custom workdir where quickstart was first deployed
- Select the specific config file
- Specifies the release (mitaka, newton, or “master” for ocata)
- Performs all the tasks in the playbook overcloud-instance-ha.yml

**Important note**

You might need to export *ANSIBLE_SSH_ARGS* with the path of the
*ssh.config.ansible* file to make the command work, like this:

    export ANSIBLE_SSH_ARGS="-F /path/to/quickstart/workdir/ssh.config.ansible"

Using the playbook on an existing TripleO environment
-----------------------------------------------------

It is possible to execute the playbook on an environment not created via TriplO
quickstart, by cloning via git the tripleo-quickstart-utils repo:

    $ git clone https://gitlab.com/redhat-openstack/tripleo-quickstart-utils

then it's just a matter of declaring three environment variables, pointing to
three files:

    $ export ANSIBLE_CONFIG=/path/to/ansible.cfg
    $ export ANSIBLE_INVENTORY=/path/to/hosts
    $ export ANSIBLE_SSH_ARGS="-F /path/to/ssh.config.ansible"

Where:

**ansible.cfg** must contain at least these lines:

    [defaults]
    roles_path = /path/to/tripleo-quickstart-utils/roles

**hosts** file must be configured with two *controller* and *compute* sections
like these:

    undercloud ansible_host=undercloud ansible_user=stack ansible_private_key_file=/path/to/id_rsa_undercloud
    overcloud-novacompute-1 ansible_host=overcloud-novacompute-1 ansible_user=heat-admin ansible_private_key_file=/path/to/id_rsa_overcloud
    overcloud-novacompute-0 ansible_host=overcloud-novacompute-0 ansible_user=heat-admin ansible_private_key_file=/path/to/id_rsa_overcloud
    overcloud-controller-2 ansible_host=overcloud-controller-2 ansible_user=heat-admin ansible_private_key_file=/path/to/id_rsa_overcloud
    overcloud-controller-1 ansible_host=overcloud-controller-1 ansible_user=heat-admin ansible_private_key_file=/path/to/id_rsa_overcloud
    overcloud-controller-0 ansible_host=overcloud-controller-0 ansible_user=heat-admin ansible_private_key_file=/path/to/id_rsa_overcloud

    [compute]
    overcloud-novacompute-1
    overcloud-novacompute-0

    [undercloud]
    undercloud

    [overcloud]
    overcloud-novacompute-1
    overcloud-novacompute-0
    overcloud-controller-2
    overcloud-controller-1
    overcloud-controller-0

    [controller]
    overcloud-controller-2
    overcloud-controller-1
    overcloud-controller-0

**ssh.config.ansible** can *optionally* contain specific per-host connection
options, like these:

    ...
    ...
    Host overcloud-controller-0
        ProxyCommand ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ConnectTimeout=60 -F /path/to/ssh.config.ansible undercloud -W 192.168.24.16:22
        IdentityFile /path/to/id_rsa_overcloud
        User heat-admin
        StrictHostKeyChecking no
        UserKnownHostsFile=/dev/null
    ...
    ...

In this example to connect to overcloud-controller-0 ansible will use
undercloud ad a ProxyHost

With this setup in place is then possible to launch the playbook:

    $ ansible-playbook -vvvv /path/to/tripleo-quickstart-utils/playbooks/overcloud-instance-ha.yml -e release=newton

Example Playbook
----------------

The main playbook contains STONITH config role as first thing, since it is a
pre requisite, and the instance-ha role itself:

    ---
    - name:  Configure STONITH for all the hosts on the overcloud
      hosts: undercloud
      gather_facts: no
      roles:
        - stonith-config

    - name: Configure Instance HA
      hosts: undercloud
      gather_facts: no
      roles:
        - instance-ha

License
-------

GPL

Author Information
------------------

Raoul Scarazzini <rasca@redhat.com>
