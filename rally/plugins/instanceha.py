from os import path
import socket
import time


from rally.common import logging
from rally.common import sshutils
from rally import exceptions
from rally_openstack import consts
from rally_openstack import scenario
from rally_openstack.scenarios.vm import utils as vm_utils
from rally_openstack.scenarios.cinder import utils as cinder_utils
from rally.task import atomic
from rally.task import types
from rally.task import validation
from rally.task import utils as task_utils
import six


LOG = logging.getLogger(__name__)


def failover(self, host, command, port=22, username="", password="",
             key_filename=None, pkey=None):
    """Trigger failover at host
    :param host:
    :param command:
    :return:
    """
    if key_filename:
        key_filename = path.expanduser(key_filename)
    LOG.info("Host: %s. Injecting Failover %s" % (host,
                                                  command))
    try:
        code, out, err = _run_command(self, server_ip=host, port=port,
                                      username=username,
                                      password=password,
                                      key_filename=key_filename,
                                      pkey=pkey, command=command
                                      )
        if code and code > 0:
            raise exceptions.ScriptError(
                "Error running command %(command)s. "
                "Error %(code)s: %(error)s" % {
                    "command": command, "code": code, "error": err})
    except exceptions.SSHTimeout:
        LOG.debug("SSH session of disruptor command timeouted, continue...")
        pass


def _run_command(self, server_ip, port, username, password, command,
                 pkey=None, key_filename=None):
    """Run command via SSH on server.
    Create SSH connection for server, wait for server to become available
    (there is a delay between server being set to ACTIVE and sshd being
    available). Then call run_command_over_ssh to actually execute the
    command.
    Note: Shadows vm.utils.VMScenario._run_command to support key_filename.
    :param server_ip: server ip address
    :param port: ssh port for SSH connection
    :param username: str. ssh username for server
    :param password: Password for SSH authentication
    :param command: Dictionary specifying command to execute.
        See `rally info find VMTasks.boot_runcommand_delete' parameter
        `command' docstring for explanation.
    :param key_filename: private key filename for SSH authentication
    :param pkey: key for SSH authentication
    :returns: tuple (exit_status, stdout, stderr)
    """
    if not key_filename:
        pkey = pkey or self.context["user"]["keypair"]["private"]
    ssh = sshutils.SSH(username, server_ip, port=port,
                       pkey=pkey, password=password,
                       key_filename=key_filename)
    self._wait_for_ssh(ssh)
    return _run_command_over_ssh(self, ssh, command)


@atomic.action_timer("vm.run_command_over_ssh")
def _run_command_over_ssh(self, ssh, command):
    """Run command inside an instance.
    This is a separate function so that only script execution is timed.
    :param ssh: A SSHClient instance.
    :param command: Dictionary specifying command to execute.
        See `rally info find VMTasks.boot_runcommand_delete' parameter
        `command' docstring for explanation.
    :returns: tuple (exit_status, stdout, stderr)
    """
    cmd, stdin = [], None

    interpreter = command.get("interpreter") or []
    if interpreter:
        if isinstance(interpreter, six.string_types):
            interpreter = [interpreter]
        elif type(interpreter) != list:
            raise ValueError("command 'interpreter' value must be str "
                             "or list type")
        cmd.extend(interpreter)

    remote_path = command.get("remote_path") or []
    if remote_path:
        if isinstance(remote_path, six.string_types):
            remote_path = [remote_path]
        elif type(remote_path) != list:
            raise ValueError("command 'remote_path' value must be str "
                             "or list type")
        cmd.extend(remote_path)
        if command.get("local_path"):
            ssh.put_file(os.path.expanduser(
                command["local_path"]), remote_path[-1],
                mode=self.USER_RWX_OTHERS_RX_ACCESS_MODE)

    if command.get("script_file"):
        stdin = open(os.path.expanduser(command["script_file"]), "rb")

    elif command.get("script_inline"):
        stdin = six.moves.StringIO(command["script_inline"])

    cmd.extend(command.get("command_args") or [])

    return ssh.execute(cmd, stdin=stdin, timeout=10)


def one_killing_iteration(self, server, fip, computes, disruptor_cmd,
                          stop_instance):
    """Find the host where instance is hosted, disrupt the host and
    verify status of the instance after the failover"""

    server_admin = self.admin_clients("nova").servers.get(server.id)
    host_name_pre = getattr(server_admin, "OS-EXT-SRV-ATTR:host")
    host_name_ext = host_name_pre.split('.')[0] + ".external"
    hypervisors = self.admin_clients("nova").hypervisors.list()
    hostnames = []
    for hypervisor in hypervisors:
        hostnames.append(getattr(hypervisor, "hypervisor_hostname"))
        if getattr(hypervisor, "hypervisor_hostname") == host_name_pre:
            hypervisor_id = getattr(hypervisor, "id")
    hypervisor = self.admin_clients("nova").hypervisors.get(hypervisor_id)
    hypervisor_ip = socket.gethostbyname(host_name_ext.strip())

    if not disruptor_cmd:
        disruptor_cmd = {
            "script_inline": "sudo sh -c \"echo b > /proc/sysrq-trigger\"",
            "interpreter": "/bin/sh"
            }

    # Trigger failover of compute node hosting the instance
    failover(self, host=hypervisor_ip,
             command=disruptor_cmd,
             port=computes.get("port", 22),
             username=computes.get("username"),
             password=computes.get("password"),
             key_filename=computes.get("key_filename"),
             pkey=computes.get("pkey")
             )
    # Wait for instance to be moved to different host
    hostnames.remove(host_name_pre)
    task_utils.wait_for(
            server_admin,
            status_attr="OS-EXT-SRV-ATTR:host",
            ready_statuses=hostnames,
            update_resource=task_utils.get_from_manager(),
            timeout=120,
            check_interval=5
         )

    # Check the instance is SHUTOFF in the case of stopped instance or
    # that the instance is pingable
    if stop_instance:
        task_utils.wait_for(
            server,
            ready_statuses=["SHUTOFF"],
            update_resource=task_utils.get_from_manager(),
            timeout=60,
            check_interval=2
        )
        #server_admin = self.admin_clients("nova").servers.get(server.id)
        #host_name_post = getattr(server_admin, "OS-EXT-SRV-ATTR:host")
        #if host_name_post in host_name_pre:
            #raise exceptions.InvalidHostException()
    else:
        try:
            if self.wait_for_ping:
               self._wait_for_ping(fip["ip"])
        except exceptions.TimeoutException:
            console_logs = self._get_server_console_output(server,
                                                               None)
            LOG.debug("VM console logs:\n%s", console_logs)
            raise


def recover_instance_ha(self, image, flavor, computes,
                        volume_args=None,
                        floating_network=None,
                        use_floating_ip=True,
                        force_delete=False,
                        stop_instance=False,
                        disruptor_cmd=None,
                        iterations=1,
                        wait_for_ping=True,
                        max_log_length=None,
                        **kwargs):
    """Boot a server, trigger failover of host and verify instance.

    :param image: glance image name to use for the vm
    :param flavor: VM flavor name
    :param computes: dictionary with credentials to the compute nodes
        consisting of username, password, port, key_filename, disruptor
        command and pkey.
        Examples::
            computes: {
              username: heat-admin,
              key_filename: /path/to/ssh/id_rsa.pub
              port: 22
            }
    :param volume_args: volume args for booting server from volume
    :param floating_network: external network name, for floating ip
    :param use_floating_ip: bool, floating or fixed IP for SSH connection
    :param force_delete: whether to use force_delete for servers
    :param stop_instance: whether to stop instance before disruptor command
    :param disruptor_cmd: command to be send to hosting compute node
    :param iterations: number of compute node killing iteration
    :param wait_for_ping: whether to check connectivity on server creation
    :param **kwargs: extra arguments for booting the server
    :param max_log_length: The number of tail nova console-log lines user
                           would like to retrieve
    :returns:
    """

    self.wait_for_ping = wait_for_ping

    if volume_args:
        volume = self.cinder.create_volume(volume_args["size"], imageRef=None)
        kwargs["block_device_mapping"] = {"vdrally": "%s:::1" % volume.id}

    server, fip = self._boot_server_with_fip(
        image, flavor, use_floating_ip=use_floating_ip,
        floating_network=floating_network,
        key_name=self.context["user"]["keypair"]["name"],
        **kwargs)

    task_utils.wait_for(
        server,
        ready_statuses=["ACTIVE"],
        update_resource=task_utils.get_from_manager(),
        timeout=120,
        check_interval=2
    )

    try:
        if self.wait_for_ping:
            self._wait_for_ping(fip["ip"])
    except exceptions.TimeoutException:
        console_logs = self._get_server_console_output(server,
                                                       max_log_length)
        LOG.debug("VM console logs:\n%s", console_logs)
        raise

    if stop_instance:
        self._stop_server(server)
        task_utils.wait_for(
            server,
            ready_statuses=["SHUTOFF"],
            update_resource=task_utils.get_from_manager(),
            timeout=120,
            check_interval=2
        )

    # Wait a little before killing the compute
    # If we do not wait, backing image will get corrupted which was reported as bug
    time.sleep(30)

    for iteration in range(1, iterations+1):
        one_killing_iteration(self, server, fip, computes,
                              disruptor_cmd, stop_instance)
        # Give cluster some time to recover original compute node
        LOG.info("Wait for compute nodes to come online after previous disruption")
        time.sleep(360)

    if stop_instance:
        # Start instance If It was stopped.
        self._start_server(server)

    task_utils.wait_for(
        server,
        ready_statuses=["ACTIVE"],
        update_resource=task_utils.get_from_manager(),
        timeout=120,
        check_interval=2
    )
    self._delete_server_with_fip(server, fip, force_delete=force_delete)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor",
                flavor_param="flavor", image_param="image")
@validation.add("valid_command", param_name="command", required=False)
@validation.add("number", param_name="port", minval=1, maxval=65535,
                nullable=True, integer_only=True)
@validation.add("external_network_exists", param_name="floating_network")
@validation.add("required_services",
                services=[consts.Service.NOVA, consts.Service.CINDER])
@validation.add("required_platform", platform="openstack",
                users=True, admin=True)
@scenario.configure(context={"cleanup@openstack": ["nova", "cinder"],
                             "keypair@openstack": {}, "allow_ssh@openstack": None},
                    name="InstanceHA.recover_instance_fip_and_volume",
                    platform="openstack")
class InstanceHARecoverFIPAndVolume(vm_utils.VMScenario, cinder_utils.CinderBasic):

    def __init__(self, *args, **kwargs):
        super(InstanceHARecoverFIPAndVolume, self).__init__(*args, **kwargs)

    def run(self, image, flavor, computes,
            volume_args=None,
            floating_network=None,
            use_floating_ip=True,
            force_delete=False,
            wait_for_ping=True,
            max_log_length=None,
            **kwargs):

        recover_instance_ha(self, image, flavor, computes,
                            volume_args=volume_args,
                            floating_network=floating_network,
                            use_floating_ip=use_floating_ip,
                            force_delete=force_delete,
                            wait_for_ping=wait_for_ping,
                            max_log_length=max_log_length,
                            **kwargs)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor",
                flavor_param="flavor", image_param="image")
@validation.add("valid_command", param_name="command", required=False)
@validation.add("number", param_name="port", minval=1, maxval=65535,
                nullable=True, integer_only=True)
@validation.add("external_network_exists", param_name="floating_network")
@validation.add("required_services",
                services=[consts.Service.NOVA, consts.Service.CINDER])
@validation.add("required_platform", platform="openstack",
                users=True, admin=True)
@scenario.configure(context={"cleanup@openstack": ["nova", "cinder"],
                             "keypair@openstack": {}, "allow_ssh@openstack": None},
                    name="InstanceHA.recover_instance_two_cycles",
                    platform="openstack")
class InstanceHARecoverTwoCycle(vm_utils.VMScenario, cinder_utils.CinderBasic):

    def __init__(self, *args, **kwargs):
        super(InstanceHARecoverTwoCycle, self).__init__(*args, **kwargs)

    def run(self, image, flavor, computes,
            volume_args=None,
            floating_network=None,
            use_floating_ip=True,
            force_delete=False,
            wait_for_ping=True,
            max_log_length=None,
            **kwargs):

        recover_instance_ha(self, image, flavor, computes,
                            volume_args=volume_args,
                            floating_network=floating_network,
                            use_floating_ip=use_floating_ip,
                            force_delete=force_delete,
                            iterations=2,
                            wait_for_ping=wait_for_ping,
                            max_log_length=max_log_length,
                            **kwargs)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor",
                flavor_param="flavor", image_param="image")
@validation.add("valid_command", param_name="command", required=False)
@validation.add("number", param_name="port", minval=1, maxval=65535,
                nullable=True, integer_only=True)
@validation.add("external_network_exists", param_name="floating_network")
@validation.add("required_services",
                services=[consts.Service.NOVA, consts.Service.CINDER])
@validation.add("required_platform", platform="openstack",
                users=True, admin=True)
@scenario.configure(context={"cleanup@openstack": ["nova", "cinder"],
                             "keypair@openstack": {}, "allow_ssh@openstack": None},
                    name="InstanceHA.recover_stopped_instance_fip",
                    platform="openstack")
class InstanceHARecoverStopped(vm_utils.VMScenario, cinder_utils.CinderBasic):

    def __init__(self, *args, **kwargs):
        super(InstanceHARecoverStopped, self).__init__(*args, **kwargs)

    def run(self, image, flavor, computes,
            volume_args=None,
            floating_network=None,
            use_floating_ip=True,
            force_delete=False,
            wait_for_ping=True,
            max_log_length=None,
            **kwargs):

        recover_instance_ha(self, image, flavor, computes,
                            volume_args=volume_args,
                            floating_network=floating_network,
                            use_floating_ip=use_floating_ip,
                            force_delete=force_delete,
                            stop_instance=True,
                            wait_for_ping=wait_for_ping,
                            max_log_length=max_log_length,
                            **kwargs)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor",
                flavor_param="flavor", image_param="image")
@validation.add("valid_command", param_name="command", required=False)
@validation.add("number", param_name="port", minval=1, maxval=65535,
                nullable=True, integer_only=True)
@validation.add("external_network_exists", param_name="floating_network")
@validation.add("required_services",
                services=[consts.Service.NOVA, consts.Service.CINDER])
@validation.add("required_platform", platform="openstack",
                users=True, admin=True)
@scenario.configure(context={"cleanup@openstack": ["nova", "cinder"],
                             "keypair@openstack": {}, "allow_ssh@openstack": None},
                    name="InstanceHA.recover_instance_nova_compute",
                    platform="openstack")
class InstanceHARecoverNovaCompute(vm_utils.VMScenario, cinder_utils.CinderBasic):

    def __init__(self, *args, **kwargs):
        super(InstanceHARecoverNovaCompute, self).__init__(*args, **kwargs)

    def run(self, image, flavor, computes,
            volume_args=None,
            floating_network=None,
            use_floating_ip=True,
            force_delete=False,
            wait_for_ping=True,
            max_log_length=None,
            **kwargs):

        disruptor_cmd = {
            "script_inline": "sudo kill -9 $(ps -ef | grep ^nova* | awk \'{print$2}\'); echo {}",
            "interpreter": "/bin/sh"
            }
        recover_instance_ha(self, image, flavor, computes,
                            volume_args=volume_args,
                            floating_network=floating_network,
                            use_floating_ip=use_floating_ip,
                            force_delete=force_delete,
                            disruptor_cmd=disruptor_cmd,
                            wait_for_ping=wait_for_ping,
                            max_log_length=max_log_length,
                            **kwargs)
