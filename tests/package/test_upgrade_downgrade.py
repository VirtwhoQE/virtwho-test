"""Test cases Global fields

:casecomponent: virt-who
:testtype: nonfunctional
:subtype1: scalability
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component

"""

import pytest
from virtwho import VIRTWHO_PKG, RHEL_COMPOSE, RHEL_COMPOSE_PATH, RHEL_SUBVERSION
from virtwho.base import virtwho_package_url
from virtwho.base import package_check, package_upgrade, package_downgrade
from virtwho.base import wget_download, rhel_compose_repo, random_string
from virtwho.base import system_reboot


old_pkg = "virt-who-unspecified.noarch"
old_compose = "latest-RHEL-unspecified"
old_compose_path = (
    "http://download.devel.redhat.com/rhel-unspecified/rel-eng/RHEL-unspecified"
)

if "RHEL-10" in RHEL_COMPOSE:
    old_pkg = "virt-who-1.32.1-2.el10.noarch"
    old_compose = "latest-RHEL-10.0"
    old_compose_path = "http://download.devel.redhat.com/rhel-10/rel-eng/RHEL-10"
if "RHEL-9" in RHEL_COMPOSE:
    old_pkg = "virt-who-1.31.22-1.el9_0.noarch"
    old_compose = "latest-RHEL-9.0"
    old_compose_path = "http://download.devel.redhat.com/rhel-9/rel-eng/RHEL-9"
if "RHEL-8" in RHEL_COMPOSE:
    old_pkg = "virt-who-1.30.8-1.el8.noarch"
    old_compose = "latest-RHEL-8.5"
    old_compose_path = "http://download.devel.redhat.com/rhel-8/rel-eng/RHEL-8"


@pytest.mark.usefixtures("function_globalconf_clean")
@pytest.mark.usefixtures("class_hypervisor")
@pytest.mark.usefixtures("class_virtwho_d_conf_clean")
@pytest.mark.usefixtures("function_host_register_for_local_mode")
class TestUpgradeDowngrade:
    @pytest.mark.tier1
    @pytest.mark.notLocal
    def test_upgrade_downgrade_by_yum(self, ssh_host, virtwho, globalconf):
        """Test virt-who upgrade/downgrade by yum

        :title: virt-who: package: upgrade/downgrade by yum
        :id: 318cb940-b68f-4ad8-8070-4ea60d05545e
        :caseimportance: High
        :tags: package,tier1
        :customerscenario: false
        :steps:
            1. configure virt-who configurations
            2. downgrade virt-who by yum
            3. check all configurations still available
            4. upgrade virt-who by yum
            5. check all configurations still available
            6. reboot virt-who host
            7. check all configurations still available
        :expectedresults:
            1. virt-who can be downgrade and upgrade successfully.
            2. all configurations will not be changed after virt-who downgrade,
                upgrade and host reboot.
        """

        """ If it is the first release of RHEL (aka 9.0, 10.0, ...) there is no reason to try downgrade/upgdare
            Since no old package is available for downgrading.
        """
        if RHEL_SUBVERSION == 0:
            pytest.skip(
                f"The first release of a distribution ({RHEL_COMPOSE}) - no downgrade posible "
            )

        current_package_version = package_check(ssh_host, "virt-who")
        if current_package_version == old_pkg:
            pytest.skip(
                f"Newer version of virt-who has not been released for ({RHEL_COMPOSE}) yet - no downgrade posible"
            )

        old_repo_file = "/etc/yum.repos.d/oldCompose.repo"
        try:
            globalconf.update("global", "debug", "True")
            globalconf.update("system_environment", "http_proxy", "xxx")
            globalconf.update("system_environment", "no_proxy", "*")
            # create old compose repo
            rhel_compose_repo(
                ssh=ssh_host,
                repo_file=old_repo_file,
                compose_id=old_compose,
                compose_path=old_compose_path,
            )
            # downgrade virt-who to check the configurations not change.
            package_downgrade(ssh_host, "virt-who")
            result = virtwho.run_service()
            assert (
                package_check(ssh_host, "virt-who") is not False
                and package_check(ssh_host, "virt-who") != VIRTWHO_PKG
                and result["send"] == 1
                and result["error"] == 0
                and result["debug"] is True
            )
            # upgrade virt-who to check the configurations not change.
            package_upgrade(ssh_host, "virt-who")
            result = virtwho.run_service()
            assert (
                package_check(ssh_host, "virt-who") == VIRTWHO_PKG
                and result["send"] == 1
                and result["error"] == 0
                and result["debug"] is True
            )
            # reboot host to check the configuration no change
            system_reboot(ssh_host)
            result = virtwho.run_service()
            assert (
                package_check(ssh_host, "virt-who") == VIRTWHO_PKG
                and result["send"] == 1
                and result["error"] == 0
                and result["debug"] is True
            )

        finally:
            if package_check(ssh_host, "virt-who") != VIRTWHO_PKG:
                package_upgrade(ssh_host, "virt-who")
            ssh_host.runcmd(f"rm -f {old_repo_file}")

    @pytest.mark.tier1
    def test_upgrade_downgrade_by_rpm(self, ssh_host, virtwho, globalconf):
        """Test virt-who upgrade/downgrade by rpm

        :title: virt-who: package: upgrade/downgrade by rpm
        :id: b363a4f4-c4cb-46b0-a378-fdaf956dd345
        :caseimportance: High
        :tags: package,tier1
        :customerscenario: false
        :steps:
            1. configure virt-who configurations
            2. downgrade virt-who by rpm
            3. check all configurations still available
            4. upgrade virt-who by rpm
            5. check all configurations still available
        :expectedresults:
            1. virt-who can be downgrade and upgrade successfully.
            2. all configurations will not be changed after downgrade and
                upgrade.
        """
        if RHEL_SUBVERSION == 0:
            pytest.skip(
                f"The first release of a distribution ({RHEL_COMPOSE}) - no downgrade posible "
            )
        current_package_version = package_check(ssh_host, "virt-who")
        if current_package_version == old_pkg:
            pytest.skip(
                f"Newer version of virt-who has not been released for ({RHEL_COMPOSE}) yet - no downgrade posible"
            )
        try:
            globalconf.update("global", "debug", "True")
            globalconf.update("system_environment", "http_proxy", "xxx")
            globalconf.update("system_environment", "no_proxy", "*")
            # download the current virt-who package
            file_path = "/tmp/packageUpgradeDowngrade-" + random_string()
            pkg_url = virtwho_package_url(VIRTWHO_PKG, RHEL_COMPOSE, RHEL_COMPOSE_PATH)
            wget_download(ssh_host, pkg_url, file_path)
            # download the old virt-who package
            old_pkg_url = virtwho_package_url(old_pkg, old_compose, old_compose_path)
            wget_download(ssh_host, old_pkg_url, file_path)
            # downgrade virt-who to check the configurations not change.
            package_downgrade(ssh_host, "virt-who", rpm=f"{file_path}/{old_pkg}.rpm")
            result = virtwho.run_service()
            assert (
                package_check(ssh_host, "virt-who") == old_pkg
                and result["send"] == 1
                and result["error"] == 0
                and result["debug"] is True
            )
            # upgrade virt-who to check the configurations not change.
            package_upgrade(ssh_host, "virt-who", rpm=f"{file_path}/{VIRTWHO_PKG}.rpm")
            result = virtwho.run_service()
            assert (
                package_check(ssh_host, "virt-who") == VIRTWHO_PKG
                and result["send"] == 1
                and result["error"] == 0
                and result["debug"] is True
            )
        finally:
            if package_check(ssh_host, "virt-who") != VIRTWHO_PKG:
                package_upgrade(ssh_host, "virt-who")

    @pytest.mark.tier1
    @pytest.mark.release(rhel8=False, rhel9=True, rhel10=True)
    def test_global_options_migration_after_upgrade(self, ssh_host, virtwho):
        """Test the global configurations in /etc/sysconfig/virt-who can be
            migrated to /etc/virt-who.conf after upgrade

        :title: virt-who: package: global options migration after upgrade
        :id: 3947857c-a9d2-4ae8-990e-91ab0a4c60ad
        :caseimportance: High
        :tags: package,tier1
        :customerscenario: false
        :steps:
            1. configure virt-who configurations
            2. downgrade virt-who by rpm
            3. check all configurations still available
            4. upgrade virt-who by rpm
            5. check all configurations still available
        :expectedresults:
            1. virt-who can be downgrade and upgrade successfully.
            2. all configurations will not be changed after downgrade and
                upgrade.
        """
        if RHEL_SUBVERSION == 0:
            pytest.skip(
                f"The first release of a distribution ({RHEL_COMPOSE}) - no downgrade posible "
            )
        current_package_version = package_check(ssh_host, "virt-who")
        if current_package_version == old_pkg:
            pytest.skip(
                f"Newer version of virt-who has not been released for ({RHEL_COMPOSE}) yet - no downgrade posible"
            )

        sysconfig_file = "/etc/sysconfig/virt-who"
        virtwho_conf_file = "/etc/virt-who.conf"

        # create /etc/sysconfig/virt-who file and define options
        ssh_host.runcmd(
            f"cat <<EOF > {sysconfig_file}\n"
            f"VIRTWHO_DEBUG = 1\n"
            f"VIRTWHO_ONE_SHOT = 0\n"
            f"VIRTWHO_INTERVAL = 120\n"
            f"http_proxy = proxy_server:proxy_port\n"
            f"no_proxy = *\n"
            f"EOF"
        )
        # run migrateconfiguration.py script
        ssh_host.runcmd(
            "/usr/bin/python3 "
            "/usr/lib/python3.9/site-packages/virtwho/migrate/"
            "migrateconfiguration.py"
        )
        # check the configurations in /etc/sysconfig/virt-who are migrated to
        # /etc/virt-who.conf
        _, output = ssh_host.runcmd(f"cat {virtwho_conf_file}")
        msg1 = (
            "[global]\n"
            "#migrated\n"
            "interval=120\n"
            "#migrated\n"
            "debug=True\n"
            "#migrated\n"
            "oneshot=False"
        )
        msg2 = (
            "[system_environment]\n"
            "#migrated\n"
            "http_proxy=proxy_server:proxy_port\n"
            "#migrated\n"
            "no_proxy=*"
        )
        assert msg1 in output and msg2 in output
        # run virt-who to test the migrated options working well
        result = virtwho.run_service()
        assert (
            result["send"] == 1
            and result["error"] == 0
            and result["interval"] == 120
            and result["debug"] is True
        )
