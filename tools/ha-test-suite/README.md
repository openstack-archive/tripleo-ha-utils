# OpenStack TripleO HA Test Suite

This project is a modular and a customizable test suite to be applied in an
Overcloud OpenStack environment deployed via TripleO upstream or Red Hat
OpenStack Director (OSPd).

## Usage

The script needs at least a test file (-t) which must contain the sequence of
the operations to be done.  A recovery file (-r), with the sequence of the
operations needed to recovery the environment can also be passed. So a typical
invocation will be something like this:

```console
[heat-admin@overcloud-controller-0 overcloud-ha-test-suite]$ ./overcloud-ha-test-suite.sh -t test/test_keystone-constraint-removal -r recovery/recovery_keystone-constraint-removal
Fri May 20 15:27:19 UTC 2016 - Populationg overcloud elements...OK
Fri May 20 15:27:22 UTC 2016 - Test: Stop keystone resource (by stopping httpd), check no other resource  is stopped
Fri May 20 15:27:22 UTC 2016 * Step 1: disable keystone resource via httpd stop
Fri May 20 15:27:22 UTC 2016 - Performing action disable on resource httpd ..OK
Fri May 20 15:27:26 UTC 2016 - List of cluster's failed actions:
Cluster is OK.
Fri May 20 15:27:29 UTC 2016 * Step 2: check resource status
Fri May 20 15:27:29 UTC 2016 - Cycling for 10 minutes polling every minute the status of the resources
Fri May 20 15:28:29 UTC 2016 - Polling...
delay -> OK
galera -> OK
...
...
openstack-sahara-engine -> OK
rabbitmq -> OK
redis -> OK
Fri May 20 15:41:00 UTC 2016 - List of cluster's failed actions:
Cluster is OK.
Fri May 20 15:41:03 UTC 2016 - Waiting 10 seconds to recover environment
Fri May 20 15:41:13 UTC 2016 - Recovery: Enable keystone via httpd and check for failed actions
Fri May 20 15:41:13 UTC 2016 * Step 1: enable keystone resource via httpd
Fri May 20 15:41:13 UTC 2016 - Performing action enable on resource httpd-clone OK
Fri May 20 15:41:15 UTC 2016 - List of cluster's failed actions:
Cluster is OK.
Fri May 20 15:41:17 UTC 2016 - End
```

The exit status will depend on the result of the operations. If a disable
operation fails, if failed actions will appear, if recovery does not ends with
success exit status will not be 0.

## Test and recoveries

Test and recovery are bash script portions that are
included inside the main script. Some functions and variables are available to
help on recurring operations.  These functions are listed here:

- **check_failed_actions**: will print failed actions and return error in case
  some of them are present;
- **check_resources_process_status**: will check for the process status of the
  resources on the system (not in the cluster), i.e. will check if there is a
  process for mysql daemon;
- **wait_resource_status**: will wail until a default timeout
  ($RESOURCE_CHANGE_STATUS_TIMEOUT) for a resource to reach a status;
- **check_resource_status**: will check a resource status, i.e. if you want to
  check if httpd resource is started;
- **wait_cluster_start**: will wait the until a timeout
  ($RESOURCE_CHANGE_STATUS_TIMEOUT) to be started, specifically will wait for
  all resources to be in state "Started";
- **play_on_resources**: will set the status of a resource;

The variables are:

- **OVERCLOUD_CORE_RESOURCES**: which are galera and rabbitmq
- **OVERCLOUD_RESOURCES**: which are *all* the resources
- **OVERCLOUD_SYSTEMD_RESOURCES**: which are the resources managed via systemd
  by pacemaker;

And can be used in combination to wrote test and recovery files.

### Test file contents

A typical test file, say test/test_keystone-constraint-removal, will contain
something like this:

```bash
# Test: Stop keystone resource (by stopping httpd), check no other resource is stopped

echo "$(date) * Step 1: disable keystone resource via httpd stop"
play_on_resources "disable" "httpd"

echo "$(date) - List of cluster's failed actions:"
check_failed_actions

echo "$(date) * Step 2: check resource status"
# Define resource list without httpd
OVERCLOUD_RESOURCES_NO_KEYSTONE="$(echo $OVERCLOUD_RESOURCES | sed 's/httpd/ /g')"
# Define number of minutes to look for status
MINUTES=10
# Cycling for $MINUTES minutes polling every minute the status of the resources
echo "$(date) - Cycling for 10 minutes polling every minute the status of the resources"
i=0
while [ $i -lt $MINUTES ]
 do
  # Wait a minute
  sleep 60
  echo "$(date) - Polling..."
  for resource in $OVERCLOUD_RESOURCES_NO_KEYSTONE
   do
    echo -n "$resource -> "
    check_resource_status "$resource" "Started"
    [ $? -eq 0 ] && echo "OK" || (FAILURES=1; echo "Error!")
   done
  let "i++"
 done

echo "$(date) - List of cluster's failed actions:"
check_failed_actions
```

Code is commented and should be self explaining, but in short:
- the first commented line, after "# Test: " is read as test title;
- using play_on_resources it disables httpd resource;
- it checks for failed actions;
- it defines a list of variable named OVERCLOUD_RESOURCES_NO_KEYSTONE containing
  all the variable but httpd;
- it cycles for 10 minutes, polling every minute the status of all the
  resources;

If any of these steps for some reason fails, then the overall test will be
considered failed and the exit status will not be 0.

### Recovery file contents

A typical recovery file, say recovery/recovery_keystone-constraint-removal,
will contain something like this:

```bash
# Recovery: Enable keystone via httpd and check for failed actions

echo "$(date) * Step 1: enable keystone resource via httpd"
play_on_resources "enable" "httpd-clone"

echo "$(date) - List of cluster's failed actions:" check_failed_actions
```

Again:
- the first commented line, after "# Recovery: " is read as recovery title;
- using play_on_resources it enables httpd resource;
- it checks for failed actions;
