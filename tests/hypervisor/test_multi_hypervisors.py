"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""
import pytest

from virtwho import REGISTER, logger
from virtwho.base import hypervisors_list, msg_search
from virtwho.configure import hypervisor_create
from virtwho.configure import get_hypervisor_info


@pytest.mark.usefixtures("function_virtwho_d_conf_clean")
@pytest.mark.usefixtures("class_debug_true")
@pytest.mark.usefixtures("class_globalconf_clean")
class TestMultiHypervisors:
    @pytest.mark.fipsEnable
    def test_multi_hypervisors_report_together(
        self, virtwho, ssh_host, satellite, rhsm
    ):
        """Test virt-who can report multi hypervisors together

        :title: virt-who: multiHypervisors: test multi hypervisors report together
        :id: 9fb6694e-7535-4d9f-9ac0-75e6cbe3066d
        :caseimportance: High
        :tags: hypervisor,multiHypervisor
        :customerscenario: false
        :upstream: no
        :steps:
            1. Create the virt-who config files for each hypervisor
            2. Run the virt-who service
            3. Check the register server

        :expectedresults:
            2. Succeed to run the virt-who, no error messages in the rhsm.log
            3. All the hypervisors could be found in the register server
        """
        file_types = ["separated", "single"]
        single_file = "/etc/virt-who.d/virtwho_multi.conf"
        try:
            for typ in file_types:
                logger.info(
                    f"+++ Start the multi hypervisors testing in ({typ}) file(s) +++"
                )
                hypervisor_hostname_list = []
                guest_uuid_list = []
                config_file_list = []
                for mode in hypervisors_list():
                    hypervisor = hypervisor_create(mode)
                    hypervisor_config_file = hypervisor.remote_file

                    hostname = "hostname"
                    if mode == "esx":
                        hostname = "esx_hostname"
                    elif mode == "rhevm":
                        hostname = "vdsm_hostname"
                    hypervisor_hostname = get_hypervisor_info(mode, hostname)
                    guest_uuid = get_hypervisor_info(mode, "guest_uuid")

                    if REGISTER == "rhsm":
                        rhsm.host_delete(hypervisor_hostname)
                    else:
                        satellite.host_delete(hypervisor_hostname)

                    hypervisor_hostname_list.append(hypervisor_hostname)
                    guest_uuid_list.append(guest_uuid)
                    config_file_list.append(hypervisor_config_file)
                if typ == "single":
                    multi_files_combine(
                        ssh_host, config_file_list, single_file, delete=True
                    )
                ssh_host.runcmd("ls /etc/virt-who.d/")
                result = virtwho.run_service()
                mappings = result["mappings"]
                assert (
                    result["error"] == 0
                    and result["send"] == 1
                    and result["thread"] == 1
                )
                assert msg_search(
                    output=str(mappings), msgs=hypervisor_hostname_list, check="and"
                )
                assert msg_search(
                    output=str(mappings), msgs=guest_uuid_list, check="and"
                )
                for hypervisor in hypervisor_hostname_list:
                    if REGISTER == "rhsm":
                        assert rhsm.consumers(host_name=hypervisor)
                    else:
                        assert satellite.hosts_info_on_webui(host=hypervisor)
        finally:
            ssh_host.runcmd(f"rm -f {single_file}")


def multi_files_combine(ssh, multi_files, dest_file, delete=False):
    for file in multi_files:
        ssh.runcmd(f"cat {file} >> {dest_file}", log_print=False)
        if delete:
            ssh.runcmd(f"rm -f {file}")
    ssh.runcmd(f"cat {dest_file}")
