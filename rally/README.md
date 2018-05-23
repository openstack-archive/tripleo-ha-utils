Rally tests
===========

This directory contains all the files available to use Rally for testing the
behavior of the TripleO environment.
For example you can test if instance HA is behaving correctly inside the
overcloud environment in which it was configured.

Requirements
------------

A working and accessible TripleO environment, as described [here](https://github.com/openstack/tripleo-ha-utils/tree/master/README.md).
so an *hosts* file containing the whole environment inventory and, if needed, a
*ssh.config.ansible* with all the information to access nodes.

How to use Rally to test Instance HA
------------------------------------

If you want to launch a Rally test session to check how Instance HA is behaving
into the overcloud you can rely on a command like this one:

    ansible-playbook -i hosts \
     -e public_physical_network="public" \
     -e floating_ip_cidr="192.168.99.0/24" \
     -e public_net_pool_start="192.168.99.211" \
     -e public_net_pool_end="192.168.99.216" \
     -e public_net_gateway="192.168.99.254" \
     tripleo-ha-utils/rally/instance-ha.yml

this command can be launched from the *undercloud* machine or from a jump host
(which must have all the required file locally).
The requested parameters refers to the network settings in which the instances
will be spawned into.

This will execute the tests contained in the template yaml:

* *InstanceHA.recover_instance_fip_and_volume*: spawn an instance, stop the
  compute it's running on, check it migrates, check node recovers;
* *InstanceHA.recover_stopped_instance_fip*: spawn an instance, put it in
  stopped status, stop the compute it's running on, check it migrates, check
  node recovers;
* *InstanceHA.recover_instance_two_cycles*: do as in the first step, but two
  times;

License
-------

GPL

Author Information
------------------

Raoul Scarazzini <rasca@redhat.com>
