---
config:
  entry_point: ./infrared/infrared_instance-ha_plugin_main.yml
  plugin_type: install
subparsers:
    instance-ha-deploy:
        description: Collection of instance-ha configuration tasks
        include_groups: ["Ansible options", "Inventory", "Common options", "Answers file"]
        groups:

            - title: Instance HA
              options:
                  instance_ha_action:
                      type: Value
                      default: install
                      help: |
                        Can be 'install' or 'uninstall'

                  release:
                      type: Value
                      help: |
                         A rhos release - version_number.
                         Example: "rhos-10".
                      required: yes
                  stonith_devices:
                    type: Value
                    default: controllers
                    help: |
                     Can be all, controllers or computes

                  instance_ha_shared_storage:
                    type: Bool
                    help: |
                      Do we have a shared storage or not?
                    default: False


