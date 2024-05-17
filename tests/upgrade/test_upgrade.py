"""Test cases Global fields

:casecomponent: virt-who
:testtype: nonfunctional
:subtype1: scalability
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""

from virtwho import RHEL_COMPOSE, HYPERVISOR
from virtwho.base import hypervisors_list, local_files_compare
from virtwho.configure import hypervisor_create, VirtwhoSysConfig


class TestUpgrade:
    def test_pre_upgrade(
        self,
        virtwho,
        sm_guest,
        hypervisor_data,
        ssh_host,
        globalconf,
    ):
        """Pre-upgrade test cases for virt-who

        :title: virt-who: upgrade : pre-upgrade test cases for virt-who
        :id: 97e5f32d-7d56-4be1-97b3-c368519cd448
        :caseimportance: High
        :tags: upgrade
        :customerscenario: false
        :upstream: no
        :steps:
            1. Create the virt-who config files for the multi hypervisors list
            2. Run the virt-who service

        :expectedresults:
            1. Succeed to run the virt-who, no error messages in the rhsm.log
        """
        # Clean all the settings in /etc/virt-who.conf and /etc/sysconfig/virt-who
        globalconf.clean()
        if "RHEL-8" in RHEL_COMPOSE:
            sysconfig = VirtwhoSysConfig(HYPERVISOR)
            sysconfig.clean()

        # Clean all the settings in /etc/virt-who.conf and /etc/sysconfig/virt-who
        cmd = "rm -rf /etc/virt-who.d/*"
        ssh_host.runcmd(cmd)

        # register guest
        sm_guest.register()

        for mode in hypervisors_list():
            hypervisor_create(mode)
        # Configure global options by /etc/virt-who.conf and /etc/sysconfig/virtwho
        globalconf.update("global", "interval", "3600")
        globalconf.update("global", "reporter_id", "upgrade-test")
        globalconf.update("global", "debug", "True")
        globalconf.update("global", "oneshot", "False")
        globalconf.update("global", "log_per_config", "False")
        globalconf.update("global", "log_dir", "/var/log/rhsm")
        globalconf.update("global", "log_file", "rhsm.log")

        globalconf.update("defaults", "owner", "Default_Organization")
        globalconf.update("defaults", "hypervisor_id", "hostname")

        if "RHEL-8" in RHEL_COMPOSE:
            globalconf.update("system_environment", "https_proxy", "https://xxx:3128")
            globalconf.update("system_environment", "no_proxy", "*")

        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

        ssh_host.get_file("/etc/virt-who.conf", "/tmp/virt-who.conf.pre")
        ssh_host.get_file("/etc/sysconfig/virt-who", "/tmp/virt-who.pre")
        for mode in hypervisors_list():
            ssh_host.get_file(f"/etc/virt-who.d/{mode}.conf", f"/tmp/{mode}.conf.pre")

    def test_post_upgrade(self, virtwho, ssh_host):
        """Post-upgrade test cases for virt-who

        :title: virt-who: upgrade : post-upgrade test cases for virt-who
        :id: 40db5c14-1c86-4371-b9f7-89b00612cb96
        :caseimportance: High
        :tags: upgrade
        :customerscenario: false
        :upstream: no
        :steps:
            1. Create the virt-who config files for the multi hypervisors list
            2. Run the virt-who service

        :expectedresults:
            1. Succeed to run the virt-who, no error messages in the rhsm.log
        """
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

        # Check all the configurations in /etc/virt-who.conf
        # and /etc/sysconfig/virt-who still exist

        ssh_host.get_file("/etc/virt-who.conf", "/tmp/virt-who.conf.post")
        ssh_host.get_file("/etc/sysconfig/virt-who", "/tmp/virt-who.post")

        assert local_files_compare(
            "/tmp/virt-who.conf.pre", "/tmp/virt-who.conf.post"
        ) and local_files_compare("/tmp/virt-who.pre", "/tmp/virt-who.post")

        # Check the /etc/virt-who.d/virtwho.conf file still exists
        for mode in hypervisors_list():
            ssh_host.get_file(f"/etc/virt-who.d/{mode}.conf", f"/tmp/{mode}.conf.post")
            assert local_files_compare(
                f"/tmp/{mode}.conf.pre", f"/tmp/{mode}.conf.post"
            )
