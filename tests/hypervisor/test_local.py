"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""
import pytest
import time

from hypervisor import logger


@pytest.mark.usefixtures("function_virtwho_d_conf_clean")
@pytest.mark.usefixtures("class_debug_true")
@pytest.mark.usefixtures("class_globalconf_clean")
class TestLocalPositive:
    @pytest.mark.tier1
    def test_threads_number_after_reconfig_libvirt(self, virtwho, ssh_host):
        """
        :title: virt-who: local: test threads number after reconfig libvirt config file
        :id: 4d2552ce-af14-4e4f-84ab-64764db64fe2
        :caseimportance: High
        :tags: hypervisor,local,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Run virt-who service to check the thread number
            2. Update libvirt config, and restart libvirtd service
            3. Check virt-who thread_num is changed or not
            4. Recovery libvirt config

        :expectedresults:
            1. Succeeded to start virt-who service and the thread_num is 1
            2. Succeed to start the libvirtd service
            3. the thread_num is still 1
        """

        # run virt-who service to check the thread number
        result = virtwho.run_service()
        thread_berfore = result['thread']
        assert thread_berfore == 1
        logger.info(f"Succeeded to start virt-who service and the thread_num is {thread_berfore}")

        # update libvirt config, and restart libvirtd service
        libvirt_conf = "/etc/libvirt/libvirtd.conf"
        try:
            operate_option("enable", "listen_tls", libvirt_conf, ssh_host)
            operate_option("enable", "listen_tcp", libvirt_conf, ssh_host)
            operate_option("enable", "auth_tcp", libvirt_conf, ssh_host)
            operate_option("enable", "tcp_port", libvirt_conf, ssh_host)

            run_service(ssh_host, "libvirtd", "restart")
            _, output = run_service(ssh_host, "libvirtd", "status")
            assert "is running" in output or "Active: active (running)" in output

            # check virt-who thread_num is changed or not
            thread_after = virtwho.thread_number()
            assert thread_berfore == thread_after

        finally:
            # recovery libvirt config
            operate_option("disable", "listen_tls", libvirt_conf, ssh_host)
            operate_option("disable", "listen_tcp", libvirt_conf, ssh_host)
            operate_option("disable", "auth_tcp", libvirt_conf, ssh_host)
            operate_option("disable", "tcp_port", libvirt_conf, ssh_host)

            run_service(ssh_host, "libvirtd", "restart")
            _, output = run_service(ssh_host, "libvirtd", "status")
            assert "is running" in output or "Active: active (running)" in output


def operate_option(action, option, file, ssh_host):
    """
    Disable/Enable the option for the specific file
    :param action: Disable or Enable
    :param option: the name of the option
    :param file: the name of the file
    :param ssh_host: the ssh host for running the command
    :return: Succeed to run the command, return True; Else, return False
    """
    cmd = ""
    if action == "enable":
        cmd = f'sed -i "s|^#{option}|{option}|g" {file}'
    elif action == "disable":
        cmd = f'sed -i "s|^{option}|#{option}|g" {file}'
    ret, output = ssh_host.runcmd(cmd)
    if ret == 0:
        logger.info(f"Succeeded to {action} option {option}")
        return True
    else:
        logger.error(f"Failed to {action} option {option}")
        return False


def run_service(ssh_host, name, action):
    """
    Run the service command, such as service virt-who start
    :param ssh_host: the ssh host for running the command
    :param name: the name of the service
    :param action: Start, Stop, Status
    :return: Succeed to run the command, return True; Else, return False
    """
    cmd = f"service {name} {action}"
    ret, output = ssh_host.runcmd(cmd, True)
    time.sleep(10)
    return ret, output
