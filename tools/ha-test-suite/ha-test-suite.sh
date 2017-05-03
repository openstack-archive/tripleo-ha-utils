#!/bin/bash

# Raoul Scarazzini (rasca@redhat.com)
# This script provides a testing suite for TripleO/Director OpenStack HA (so with Pacemaker) environments

# Define main workdir
WORKDIR=$(dirname $0)

# Source function library.
. $WORKDIR/include/functions

# Fixed parameters
# How much time wait in seconds for a resource to change status (i.e. from started to stopped)
RESOURCE_CHANGE_STATUS_TIMEOUT=600
# How much time wait in seconds before starting recovery
DEFAULT_RECOVERY_WAIT_TIME=10

# Command line parameters
if [ $# -gt 0 ]
 then
  while :; do
   case $1 in
    -h|-\?|--help)
        usage
        exit
        ;;
    -u|--undercloud)
        undercloud=true
        shift
        ;;
    -t|--test)
        test_sequence="$2"
        shift
        ;;
    -r|--recover)
        recovery_sequence="$2"
        shift
        ;;
    --)
        shift
        break
        ;;
    -?*)
        usage
        exit 1
        ;;
    *)
        break
   esac

   shift
  done
 else
  usage
  exit 1
fi

# Populating overcloud elements if not on undercloud
if [ "$undercloud" != true ]
 then
  echo -n "$(date) - Populationg overcloud elements..."
  OVERCLOUD_CORE_RESOURCES="galera redis rabbitmq"
  OVERCLOUD_RESOURCES=$(sudo pcs resource show | egrep '^ (C|[a-Z])' | sed 's/.* \[\(.*\)\]/\1/g' | sed 's/ \(.*\)(.*):.*/\1/g' | sort)
  OVERCLOUD_SYSTEMD_RESOURCES=$(sudo pcs config show | egrep "Resource:.*systemd"|grep -v "haproxy"|awk '{print $2}')
  echo "OK"
fi

if [ -f "$test_sequence" ]
 then
  echo "$(date) - Test: $(grep '^#.*Test:' $test_sequence | sed 's/^#.*Test: //')"
  . $test_sequence
 else
  echo "No test file passed or unable to read test file."
fi

if [ -f "$recovery_sequence" ]
 then
  echo "$(date) - Waiting $DEFAULT_RECOVERY_WAIT_TIME seconds to recover environment"
  sleep $DEFAULT_RECOVERY_WAIT_TIME

  echo "$(date) - Recovery: $(grep '^#.*Recovery:' $recovery_sequence | sed 's/^#.*Recovery: //')"
  . $recovery_sequence
 else
  echo "No recovery file passed or unable to read recovery file."
fi

echo "$(date) - End"
