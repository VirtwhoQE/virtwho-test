"""Test cases Global fields

:casecomponent: virt-who
:testtype: nonfunctional
:caseautomation: Automated
"""
import pytest
from virtwho import VIRTWHO_PKG
from virtwho.base import package_check, package_install, package_uninstall
from virtwho.base import wget_download
from virtwho.testing import virtwho_pacakge_url


class TestInstallUninstall:
    @pytest.mark.tier1
    def test_install_uninstall_by_yum(self, ssh_host):
        """Just a demo

        :title: virt-who: package: install/uninstall by yum
        :id: 4f784cd4-ad46-4457-a20f-7cf07ba44d9e
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. uninstall virt-who by #yum remove virt-who
            2. install virt-who by #yum install virt-who
        :expectedresults:
            1. virt-who can be remove and reinstall successfully.
        """
        package_uninstall(ssh_host, 'virt-who')
        assert package_check(ssh_host, 'virt-who') is False
        package_install(ssh_host, 'virt-who')
        assert package_check(ssh_host, 'virt-who') is True

    @pytest.mark.tier1
    def test_install_uninstall_by_rpm(self, ssh_host):
        """Just a demo

        :title: virt-who: package: install/uninstall by rpm
        :id: 4f784cd4-ad46-4457-a20f-7cf07ba44d9e
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. uninstall virt-who by #rpm -e
            2. install virt-who by #rpm -ivh
        :expectedresults:
            1. virt-who can be remove and reinstall successfully.
        """
        try:
            package_uninstall(ssh_host, 'virt-who', rpm=VIRTWHO_PKG)
            assert package_check(ssh_host, 'virt-who') is False

            pkg_url = virtwho_pacakge_url(arch='x86_64')
            file_path = '/root/'
            wget_download(ssh_host, url=pkg_url, file_path=file_path)
            package_install(ssh_host,
                            pkg_name='virt-who',
                            rpm=f'{file_path}/{VIRTWHO_PKG}.rpm')
            assert package_check(ssh_host, 'virt-who') is True
        finally:
            if package_check(ssh_host, 'virt-who') is False:
                package_install(ssh_host, 'virt-who')
