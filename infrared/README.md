Infrared Intance-ha Plugin Playbook
====================================

This Plugin deploys Instance-Ha on OpenStack using InfraRed

The Tasks in infrared_instance-ha_plugin_main.yml, along with the
plugin.spec at tripleo-quickstart-utils/plugin.spec provide support
for running this repo's roles and playbooks as an Infrared plugin.

[InfraRed](http://infrared.readthedocs.io/en/stable/) is a plugin based system
 that aims to provide an easy-to-use CLI for Ansible based projects and 
 OpenStack deployment.

The plugin provides infrared plugin integration for 
two OpenStack High-Availability features:  

 [instance-ha](https://github.com/redhat-openstack/tripleo-quickstart-utils/tree/master/roles/instance-ha)

 [stonith-config](https://github.com/redhat-openstack/tripleo-quickstart-utils/tree/master/roles/stonith-config)

Usage: 
=====

**Installation and deployment:**

[Setup InfraRed](http://infrared.readthedocs.io/en/stable/bootstrap.html)

ir plugin add https://github.com/redhat-openstack/tripleo-quickstart-utils

export ANSIBLE_ROLES_PATH='plugins/tripleo-quickstart-utils/roles'

ir instance-ha-deploy -v --release 12 --stonith_devices all

*notice: a fail & warning will be issued if the plugin's specific ANSIBLE_ROLES_PATH is not defined *


**Plugin help:**

ir instance-ha-deploy -h


**Plugin Uninstall:**

ir plugin remove instance-ha-deploy




Author Information
------------------

Pini Komarov pkomarov@redhat.com