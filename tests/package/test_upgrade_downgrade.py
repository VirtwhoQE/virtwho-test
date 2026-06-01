"""Test cases Global fields

:casecomponent: virt-who
:testtype: nonfunctional
:subtype1: scalability
:caseautomation: Automated
:subsystemteam: rhel-sst-csi-client-tools
:caselevel: Component

"""

import pytest
from virtwho import VIRTWHO_PKG
from virtwho.base import package_check, package_upgrade, package_downgrade
from virtwho.base import dnf_download_pkg, dnf_can_downgrade, random_string
from virtwho.base import system_reboot


def _skip_if_no_downgrade(ssh_host):
    """Skip the test if dnf cannot downgrade virt-who (only one version in repos)."""
    if not dnf_can_downgrade(ssh_host, "virt-who"):
        pytest.skip(
            "Only one version of virt-who available in repos — "
            "downgrade not possible (expected in compose-only mode)"
        )


@pytest.mark.usefixtures("function_globalconf_clean")
@pytest.mark.usefixtures("class_hypervisor")
@pytest.mark.usefixtures("class_virtwho_d_conf_clean")
@pytest.mark.usefixtures("function_host_register_for_local_mode")
class TestUpgradeDowngrade:
    @pytest.mark.tier1
    @pytest.mark.notLocal
    def test_downgrade_upgrade_by_dnf(self, ssh_host, virtwho, globalconf):
        """Test virt-who upgrade/downgrade by dnf using system repos.

        In gating mode the Brew build is newer than the compose version, so
        dnf downgrade goes to the compose version and dnf upgrade returns to
        the gating build.  In compose-only mode only one version exists in
        the repos, so the test is skipped.

        :title: virt-who: package: downgrade/upgrade by dnf
        :id: 318cb940-b68f-4ad8-8070-4ea60d05545e
        :caseimportance: High
        :tags: package,tier1
        :customerscenario: false
        :steps:
            1. configure virt-who configurations
            2. downgrade virt-who by dnf
            3. check all configurations still available
            4. upgrade virt-who by dnf
            5. check all configurations still available
            6. reboot virt-who host
            7. check all configurations still available
        :expectedresults:
            1. virt-who can be downgraded and upgraded successfully.
            2. all configurations are preserved across downgrade, upgrade,
               and host reboot.
        """
        _skip_if_no_downgrade(ssh_host)

        try:
            globalconf.update("global", "debug", "True")
            globalconf.update("system_environment", "http_proxy", "xxx")
            globalconf.update("system_environment", "no_proxy", "*")

            package_downgrade(ssh_host, "virt-who")
            result = virtwho.run_service()
            assert (
                package_check(ssh_host, "virt-who") is not False
                and package_check(ssh_host, "virt-who") != VIRTWHO_PKG
                and result["send"] == 1
                and result["error"] == 0
                and result["debug"] is True
            )

            package_upgrade(ssh_host, "virt-who")
            result = virtwho.run_service()
            assert (
                package_check(ssh_host, "virt-who") == VIRTWHO_PKG
                and result["send"] == 1
                and result["error"] == 0
                and result["debug"] is True
            )

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

    @pytest.mark.tier1
    def test_downgrade_upgrade_by_rpm(self, ssh_host, virtwho, globalconf):
        """Test virt-who upgrade/downgrade by rpm using dnf-downloaded RPMs.

        Downloads the current (gating) and compose RPMs via ``dnf download``,
        then exercises downgrade/upgrade via raw ``rpm`` commands.  Skipped in
        compose-only mode where only one version is available.

        :title: virt-who: package: downgrade/upgrade by rpm
        :id: b363a4f4-c4cb-46b0-a378-fdaf956dd345
        :caseimportance: High
        :tags: package,tier1
        :customerscenario: false
        :steps:
            1. configure virt-who configurations
            2. save current RPM via dnf download
            3. downgrade virt-who by dnf, then save compose RPM
            4. upgrade back via rpm -Uvh with saved RPM
            5. check configurations preserved
            6. downgrade via rpm --oldpackage with compose RPM
            7. check configurations preserved
        :expectedresults:
            1. virt-who can be downgraded and upgraded by rpm successfully.
            2. all configurations are preserved across downgrade and upgrade.
        """
        _skip_if_no_downgrade(ssh_host)

        gating_dir = "/tmp/vw-gating-" + random_string()
        compose_dir = "/tmp/vw-compose-" + random_string()
        try:
            globalconf.update("global", "debug", "True")
            globalconf.update("system_environment", "http_proxy", "xxx")
            globalconf.update("system_environment", "no_proxy", "*")

            gating_rpm = dnf_download_pkg(ssh_host, "virt-who", gating_dir)

            package_downgrade(ssh_host, "virt-who")
            compose_pkg = package_check(ssh_host, "virt-who")
            assert compose_pkg is not False and compose_pkg != VIRTWHO_PKG
            compose_rpm = dnf_download_pkg(ssh_host, "virt-who", compose_dir)

            package_upgrade(ssh_host, "virt-who", rpm=gating_rpm)
            result = virtwho.run_service()
            assert (
                package_check(ssh_host, "virt-who") == VIRTWHO_PKG
                and result["send"] == 1
                and result["error"] == 0
                and result["debug"] is True
            )

            package_downgrade(ssh_host, "virt-who", rpm=compose_rpm)
            result = virtwho.run_service()
            assert (
                package_check(ssh_host, "virt-who") == compose_pkg
                and result["send"] == 1
                and result["error"] == 0
                and result["debug"] is True
            )

        finally:
            if package_check(ssh_host, "virt-who") != VIRTWHO_PKG:
                package_upgrade(ssh_host, "virt-who")
            ssh_host.runcmd(f"rm -rf {gating_dir} {compose_dir}")

    @pytest.mark.tier1
    @pytest.mark.release(rhel8=False, rhel9=True, rhel10=True)
    def test_config_migration_after_upgrade(self, ssh_host, virtwho):
        """Test the global configurations in /etc/sysconfig/virt-who can be
            migrated to /etc/virt-who.conf after upgrade

        :title: virt-who: package: global options migration after upgrade
        :id: 3947857c-a9d2-4ae8-990e-91ab0a4c60ad
        :caseimportance: High
        :tags: package,tier1
        :customerscenario: false
        :steps:
            1. downgrade virt-who via dnf
            2. write legacy /etc/sysconfig/virt-who options
            3. upgrade virt-who via dnf (triggers migrateconfiguration.py)
            4. check migrated options in /etc/virt-who.conf
            5. run virt-who to verify migrated config works
        :expectedresults:
            1. virt-who can be downgraded and upgraded successfully.
            2. all configurations in /etc/sysconfig/virt-who are migrated
               to /etc/virt-who.conf after upgrade.
        """
        _skip_if_no_downgrade(ssh_host)

        sysconfig_file = "/etc/sysconfig/virt-who"
        virtwho_conf_file = "/etc/virt-who.conf"

        try:
            package_downgrade(ssh_host, "virt-who")

            ssh_host.runcmd(
                f"cat <<EOF > {sysconfig_file}\n"
                f"VIRTWHO_DEBUG = 1\n"
                f"VIRTWHO_ONE_SHOT = 0\n"
                f"VIRTWHO_INTERVAL = 120\n"
                f"http_proxy = proxy_server:proxy_port\n"
                f"no_proxy = *\n"
                f"EOF"
            )
            ssh_host.runcmd(
                "/usr/bin/python3 -c "
                "'from virtwho.migrate.migrateconfiguration import main; main()'"
            )

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

            package_upgrade(ssh_host, "virt-who")
            result = virtwho.run_service()
            assert (
                result["send"] == 1
                and result["error"] == 0
                and result["interval"] == 120
                and result["debug"] is True
            )
        finally:
            if package_check(ssh_host, "virt-who") != VIRTWHO_PKG:
                package_upgrade(ssh_host, "virt-who")
