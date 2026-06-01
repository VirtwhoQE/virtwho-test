"""Test cases Global fields

:casecomponent: virt-who
:testtype: nonfunctional
:subtype1: installability
:caseautomation: Automated
:subsystemteam: rhel-sst-csi-client-tools
:caselevel: Component
"""

import re

import pytest
from virtwho import VIRTWHO_PKG, RHEL_COMPOSE
from virtwho.base import package_check, package_install, package_uninstall
from virtwho.base import dnf_download_pkg, random_string


class TestInstallUninstall:
    @pytest.mark.tier1
    def test_install_uninstall_by_dnf(self, ssh_host):
        """Test virt-who install/uninstall by dnf

        :title: virt-who: package: install/uninstall by dnf
        :id: 7b32612a-11eb-437e-92c9-b7d501d2e8a0
        :caseimportance: High
        :tags: package,tier1
        :customerscenario: false
        :steps:
            1. uninstall virt-who by #dnf remove virt-who
            2. install virt-who by #dnf install virt-who
            3. check the /etc/virt-who.d/template.conf
        :expectedresults:
            1. virt-who can be removed and reinstalled from repos successfully.
            2.
        """
        package_uninstall(ssh_host, "virt-who")
        assert package_check(ssh_host, "virt-who") is False
        package_install(ssh_host, "virt-who")
        assert package_check(ssh_host, "virt-who") == VIRTWHO_PKG

        options = [
            "#[config name]",
            "#type=",
            "#server=",
            "#username=",
            "#password=",
            "#encrypted_password=",
            "#owner=",
            "#hypervisor_id=",
            "#rhsm_hostname=",
            "#rhsm_port=",
            "#rhsm_username=",
            "#rhsm_password=",
            "#rhsm_encrypted_password=",
            "#rhsm_prefix=/rhsm",
            "#kubeconfig=",
            "#kubeversion=",
            "#insecure=",
        ]
        line_num = 44
        if "RHEL-8" in RHEL_COMPOSE:
            line_num = 43
            options.remove("#insecure=")
        _, output = ssh_host.runcmd("cat /etc/virt-who.d/template.conf")
        for option in options:
            assert len(re.findall(option, output)) > 0
        lines = output.strip().split("\n")
        assert len(lines) == line_num

    @pytest.mark.tier1
    def test_install_uninstall_by_rpm(self, ssh_host):
        """Test virt-who install/uninstall by rpm

        :title: virt-who: package: install/uninstall by rpm
        :id: 14152159-22a7-4550-9281-1109c4440f34
        :caseimportance: High
        :tags: package,tier1
        :customerscenario: false
        :steps:
            1. uninstall virt-who by #rpm -e
            2. download virt-who RPM from system repos using dnf download
            3. install virt-who by #rpm -ivh
        :expectedresults:
            1. virt-who can be removed and reinstalled successfully.
        """
        try:
            file_path = "/tmp/packageInstallUninstall-" + random_string()
            rpm_path = dnf_download_pkg(ssh_host, "virt-who", file_path)

            package_uninstall(ssh_host, "virt-who", rpm=VIRTWHO_PKG)
            assert package_check(ssh_host, "virt-who") is False

            package_install(ssh_host, "virt-who", rpm=rpm_path)
            assert package_check(ssh_host, "virt-who") == VIRTWHO_PKG
        finally:
            if package_check(ssh_host, "virt-who") is False:
                package_install(ssh_host, "virt-who")
            ssh_host.runcmd(f"rm -rf {file_path}")
