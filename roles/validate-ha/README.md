validate-ha
===========

This role acts on an already deployed tripleo environment, testing HA related
functionalities of the installation.

Requirements
------------

The TripleO environment must be prepared as described [here](https://github.com/redhat-openstack/tripleo-quickstart-utils/tree/master/README.md).

This role tests also instances spawning and to make this working the
definition of the floating network must be passed.
It can be contained in a config file, like this:

    private_network_cidr: "192.168.1.0/24"
    public_physical_network: "floating"
    floating_ip_cidr: "10.0.0.0/24"
    public_net_pool_start: "10.0.0.191"
    public_net_pool_end: "10.0.0.198"
    public_net_gateway: "10.0.0.254"

Or passed directly to the ansible command line (see examples below).

HA tests
--------

HA tests are meant to check the behavior of the environment in front of
circumstances that involve service interruption, lost of a node and in general
actions that stress the OpenStack installation with unexpected failures.
Each test is associated to a global variable that, if true, makes the test
happen.
Tests are grouped and performed by default depending on the OpenStack release.
This is the list of the supported variables, with test description and name of
the release on which the test is performed:

- **test_ha_failed_actions**: Look for failed actions (**all**)
- **test_ha_master_slave**: Stop master slave resources (galera and redis), all
the resources should come down (**all**)
- **test_ha_keystone_constraint_removal**: Stop keystone resource (by stopping
httpd), check no other resource is stopped (**mitaka**)
- Next generation cluster checks (**newton**, **ocata**, **master**):
  - **test_ha_ng_a**: Stop every systemd resource, stop Galera and Rabbitmq,
Start every systemd resource
  - **test_ha_ng_b**: Stop Galera and Rabbitmq, stop every systemd resource,
Start every systemd resource
  - **test_ha_ng_c**: Stop Galera and Rabbitmq, wait 20 minutes to see if
something fails

It is also possible to omit (or add) tests not made for the specific release,
using the above vars, by passing to the command line variables like this:

    ...
    -e test_ha_failed_actions=false \
    -e test_ha_ng_a=true \
    ...

In this case we will not check for failed actions, a test that otherwise would
have been done in mitaka, and we will force the execution of the "ng_a" test
described earlier, which is originally executed just in newton versions or
above.

All tests are performed using the tool [ha-test-suite](https://github.com/redhat-openstack/tripleo-quickstart-utils/tree/master/tools/ha-test-suite).

Examples on how to invoke the playbook via ansible
--------------------------------------------------

Here's a way to invoke the tests from an *undercloud* machine prepared as
described [here](https://github.com/redhat-openstack/tripleo-quickstart-utils/tree/master/README.md).

    ansible-playbook /home/stack/tripleo-quickstart-utils/playbooks/overcloud-validate-ha.yml \
      -e release=ocata \
      -e local_working_dir=/home/stack \
      -e private_net_cidr="192.168.1.0/24" \
      -e public_physical_network="floating" \
      -e floating_ip_cidr="10.0.0.0/24" \
      -e public_net_pool_start="10.0.0.191" \
      -e public_net_pool_end="10.0.0.198" \
      -e public_net_gateway="10.0.0.254"

Note that the variables above can be declared inside a config.yml file that can
be passed to the ansible-playbook command like this:

    ansible-playbook -vvvv /home/stack/tripleo-quickstart-utils/playbooks/overcloud-validate-ha.yml -e @/home/stack/config.yml

The result will be the same.

License
-------

GPL

Author Information
------------------

Raoul Scarazzini <rasca@redhat.com>
