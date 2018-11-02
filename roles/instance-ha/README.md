instance-ha
===========

This role aims to automate all the steps needed to configure instance HA on a
deployed TripleO overcloud environment.

Requirements
------------

The TripleO environment must be prepared as described [here](https://github.com/openstack/tripleo-ha-utils/tree/master/README.md).

**NOTE**: Instance-HA depends on STONITH. This means that all the steps
performed by this role make sense only if on the overcloud STONITH has been
configured. There is a dedicated role that automates the STONITH
configuration, named [stonith-config](https://github.com/openstack/tripleo-ha-utils/tree/master/roles/stonith-config).

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

How Instance HA works
---------------------

There are three key resource agents you need to consider. Here's the list:

- *fence_compute* (named **fence-nova** inside the cluster): which takes care
  of marking a compute node with the attribute "evacuate" set to yes;
- *NovaEvacuate* (named **nova-evacuate** inside the cluster): which takes care
  of the effective evacuation of the instances and runs on one of the
  controllers;
- *nova-compute-wait* (named **nova-compute-checkevacuate** inside the
  cluster): which waits for eventual evacuation before starting nova compute
  services and runs on each compute nodes;

Looking at the role you will notice that other systemd resources will be added
into the cluster on the compute nodes, especially in older release like mitaka
(*neutron-openvswitch-agent*, *libvirtd*, *openstack-ceilometer-compute* and
*nova-compute*), but the keys for the correct instance HA comprehension are the
aforementioned three resources.

Evacuation
----------

The principle under which Instance HA works is *evacuation*. This means that
when a host becomes unavailablea for whatever reason, instances on it are
evacuated to another available host.
Instance HA works both on shared storage and local storage environments, which
means that evacuated instances will maintain the same network setup (static ip,
floating ip and so on) and characteristics inside the new host, even if they
will be spawned from scratch.

What happens when a compute node is lost
----------------------------------------

Once configured, how does the system behaves when evacuation is needed? The
following sequence describes the actions taken by the cluster and the OpenStack
components:

1. A compute node (say overcloud-compute-1) which is running instances goes
   down for some reason (power outage, kernel panic, manual intervention);
2. The cluster starts the action sequence to fence this host, since it needs
   to be sure that the host is *really* down before driving any other operation
   (otherwise there is potential for data corruption or multiple identical VMs
   running at the same time in the infrastructure). Setup is configured to have
   two levels of fencing for the compute hosts:

    * **IPMI**: which will occur first and will take care of physically
      resetting the host and hence assuring that the machine is really powered
      off;
    * **fence-nova**: which will occur afterwards and will take care of marking
      with a cluster per-node attribute "evacuate=yes";

    So the host gets reset and on the cluster a new node-property like the
    following will appear:

        [root@overcloud-controller-0 ~]# attrd_updater -n evacuate -A
        name="evacuate" host="overcloud-compute-1.localdomain" value="yes"

3. At this point the resource **nova-evacuate** which constantly monitors the
   attributes of the cluster in search of the evacuate tag will find out that
   the *overcloud-compute-1* host needs evacuation, and by internally using
   *nova-compute commands*, will start the evactuation of the instances towards
   another host;
4. In the meantime, while compute-1 is booting up again,
   **nova-compute-checkevacuate** will wait (with a default timeout of 120
   seconds) for the evacuation to complete before starting the chain via the
   *NovaCompute* resource that will enable the fenced host to become available
   again for running instances;

What to look for when something is not working
----------------------------------------------

Here there are some tips to follow once you need to debug why instance HA is
not working:

1. Check credentials: many resources require access data the the overcloud
   coming form the overcloudrc file, so it's not so difficult to do copy
   errors;
2. Check connectivity: stonith is essential for cluster and if for some reason
   the cluster is not able to fence the compute nodes, the whole instance HA
   environment will not work;
3. Check errors: inside the controller's cluster log
   (*/var/log/cluster/corosync.log*) some errors may catch the eye.

Examples on how to invoke the playbook via ansible
--------------------------------------------------

This command line will install the whole instance-ha solution, with controller
stonith, compute stonith and all the instance ha steps in:

    ansible-playbook /home/stack/tripleo-ha-utils/playbooks/overcloud-instance-ha.yml -e release="rhos-10"

By default the playbook will install the instance-ha solution with the shared
storage configuration, but it is possible to make the installation in a no
shared storage environment, passing the **instance_ha_shared_storage** variable
as **false**:

    ansible-playbook /home/stack/tripleo-ha-utils/playbooks/overcloud-instance-ha.yml -e release="rhos-10" -e instance_ha_shared_storage=false

If a user configured the overcloud with a specific domain it is possible to
override the default "localdomain" value by passing the **overcloud_domain**
variable to the playbook:

    ansible-playbook /home/stack/tripleo-ha-utils/playbooks/overcloud-instance-ha.yml -e release="rhos-10" -e overcloud_domain="mydomain"

If a user already installed STONITH for controllers and wants just to apply all
the instance HA steps with STONITH for the compute nodes can launch this:

    ansible-playbook /home/stack/tripleo-ha-utils/playbooks/overcloud-instance-ha.yml -e release="rhos-10" -e stonith_devices="computes"

To uninstall the whole instance HA solution:

    ansible-playbook /home/stack/tripleo-ha-utils/playbooks/overcloud-instance-ha.yml -e release="rhos-10" -e instance_ha_action="uninstall"

Or if you a user needs to omit STONITH for the controllers:

    ansible-playbook /home/stack/tripleo-ha-utils/playbooks/overcloud-instance-ha.yml -e release="rhos-10" -e stonith_devices="computes" -e instance_ha_action="uninstall"

Is it also possible to totally omit STONITH configuration by passing "none" as
the value of *stonith_devices*.

License
-------

GPL

Author Information
------------------

Raoul Scarazzini <rasca@redhat.com>
