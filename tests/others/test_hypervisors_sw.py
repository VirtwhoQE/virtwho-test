"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""

import pytest
from virtwho.configure import config, hypervisor_create
from virtwho.register import SubscriptionManager, RHSM
from virtwho.runner import VirtwhoRunner
from virtwho.base import hostname_get
from virtwho.ssh import SSHConnect
from utils.properties_update import virtwho_ini_update


@pytest.mark.usefixtures("class_globalconf_clean")
@pytest.mark.usefixtures("class_virtwho_d_conf_clean")
class TestHypervisorsSW:
    def test_report_hypervisor_for_sw(self):
        """
        Report hypervisors mapping and register guest to stage candlepin for
        the con-work with Subscription Watch team.
        """
        hypervisors = config.job.multi_hypervisors
        hosts = []
        virtwho = VirtwhoRunner(mode="", register_type="rhsm")
        sm_host = SubscriptionManager(
            host=config.virtwho.server,
            username=config.virtwho.username,
            password=config.virtwho.password,
            register_type="rhsm_sw",
        )
        rhsm = RHSM(rhsm="rhsm_sw")
        try:
            # remove all systems from stage account
            rhsm.host_delete()
            # register virt-who host to the stage
            sm_host.register()

            # start to report mapping and register guest
            if "ahv" in hypervisors:
                hypervisor_create(mode="ahv", register_type="rhsm_sw", rhsm=False)
                sm_guest = SubscriptionManager(
                    host=config.ahv.guest_ip_sw,
                    username=config.ahv.guest_username_sw,
                    password=config.ahv.guest_password_sw,
                    register_type="rhsm_sw",
                )
                sm_guest.register()

                ssh_guest = SSHConnect(
                    host=config.ahv.guest_ip_sw,
                    user=config.ahv.guest_username_sw,
                    pwd=config.ahv.guest_password_sw,
                )
                guest_hostname = hostname_get(ssh_guest)
                virtwho_ini_update("ahv", "guest_hostname_sw", guest_hostname)
                hosts.append(config.ahv.hostname)
                hosts.append(guest_hostname)

            if "kubevirt" in hypervisors:
                hypervisor_create(mode="kubevirt", register_type="rhsm_sw", rhsm=False)
                sm_guest = SubscriptionManager(
                    host=config.kubevirt.guest_ip_sw,
                    username=config.kubevirt.guest_username_sw,
                    password=config.kubevirt.guest_password_sw,
                    port=config.kubevirt.guest_port_sw,
                    register_type="rhsm_sw",
                )
                sm_guest.register()

                ssh_guest = SSHConnect(
                    host=config.kubevirt.guest_ip_sw,
                    user=config.kubevirt.guest_username_sw,
                    pwd=config.kubevirt.guest_password_sw,
                    port=config.kubevirt.guest_port_sw,
                )
                guest_hostname = hostname_get(ssh_guest)
                virtwho_ini_update("kubevirt", "guest_hostname_sw", guest_hostname)
                hosts.append(config.kubevirt.hostname)
                hosts.append(guest_hostname)

            result = virtwho.run_cli(config=None)
            assert (
                result["send"] != 0
                and result["error"] == 0
                and all(rhsm.info(name) for name in hosts)
            )

        finally:
            sm_host.unregister()
