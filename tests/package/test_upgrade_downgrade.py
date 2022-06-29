"""Test cases Global fields

:casecomponent: virt-who
:testtype: nonfunctional
:caseautomation: Automated
"""
import pytest
from virtwho import VIRTWHO_PKG, RHEL_COMPOSE
from virtwho.base import package_check, package_upgrade, package_downgrade
from virtwho.base import wget_download, rhel_compose_repo, random_string
from virtwho.testing import virtwho_pacakge_url


@pytest.mark.usefixtures('globalconf_clean')
@pytest.mark.usefixtures('hypervisor_create')
class TestUpgradeDowngrade:
    @pytest.mark.tier1
    def test_upgrade_downgrade_by_yum(self, ssh_host, virtwho, globalconf):
        """Test virt-who upgrade/downgrade by yum

        :title: virt-who: package: upgrade/downgrade by yum
        :id: 318cb940-b68f-4ad8-8070-4ea60d05545e
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. configure virt-who configurations
            2. downgrade virt-who by yum
            3. check all configurations still available
            4. upgrade virt-who by yum
            5. check all configurations still available
        :expectedresults:
            1. virt-who can be downgrade and upgrade successfully.
            2. all configurations will not be changed after downgrade and upgrade.
        """
        try:
            globalconf.update('global', 'debug', 'True')
            globalconf.update('system_environment', 'http_proxy', 'xxx')
            globalconf.update('system_environment', 'no_proxy', '*')
            # create old compose repo
            old_compose = 'latest-RHEL-9.0'
            if 'RHEL-8' in RHEL_COMPOSE:
                old_compose = 'latest-RHEL-8.5'
            rhel_compose_repo(
                ssh_host, old_compose, '/etc/yum.repos.d/oldCompose.repo'
            )
            # downgrade virt-who to check the configurations not change.
            package_downgrade(ssh_host, 'virt-who')
            result = virtwho.run_service()
            assert (
                package_check(ssh_host, 'virt-who') is not False and
                package_check(ssh_host, 'virt-who') != VIRTWHO_PKG and
                result['send'] == 1 and
                result['error'] == 0 and
                result['debug'] is True
            )
            # upgrade virt-who to check the configurations not change.
            package_upgrade(ssh_host, 'virt-who')
            result = virtwho.run_service()
            assert (
                package_check(ssh_host, 'virt-who') == VIRTWHO_PKG and
                result['send'] == 1 and
                result['error'] == 0 and
                result['debug'] is True
            )
        finally:
            if package_check(ssh_host, 'virt-who') != VIRTWHO_PKG:
                package_upgrade(ssh_host, 'virt-who')

    @pytest.mark.tier1
    def test_upgrade_downgrade_by_rpm(self, ssh_host, virtwho, globalconf):
        """Test virt-who upgrade/downgrade by rpm

        :title: virt-who: package: upgrade/downgrade by rpm
        :id: b363a4f4-c4cb-46b0-a378-fdaf956dd345
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. configure virt-who configurations
            2. downgrade virt-who by rpm
            3. check all configurations still available
            4. upgrade virt-who by rpm
            5. check all configurations still available
        :expectedresults:
            1. virt-who can be downgrade and upgrade successfully.
            2. all configurations will not be changed after downgrade and upgrade.
        """
        try:
            globalconf.update('global', 'debug', 'True')
            globalconf.update('system_environment', 'http_proxy', 'xxx')
            globalconf.update('system_environment', 'no_proxy', '*')
            # download the old and current virt-who package
            old_virtwho_pkg = 'virt-who-1.31.21-1.el9.noarch'
            if 'RHEL-8' in RHEL_COMPOSE:
                old_virtwho_pkg = 'virt-who-1.30.10-1.el8.noarch'
            pkg_url = virtwho_pacakge_url(VIRTWHO_PKG)
            old_pkg_url = virtwho_pacakge_url(old_virtwho_pkg)
            file_path = '/root/' + random_string()
            wget_download(ssh_host, pkg_url, file_path)
            wget_download(ssh_host, old_pkg_url, file_path)
            # downgrade virt-who to check the configurations not change.
            package_downgrade(ssh_host, 'virt-who',
                              rpm=f'{file_path}/{old_virtwho_pkg}.rpm')
            result = virtwho.run_service()
            assert (
                package_check(ssh_host, 'virt-who') is not False and
                package_check(ssh_host, 'virt-who') != VIRTWHO_PKG and
                result['send'] == 1 and
                result['error'] == 0 and
                result['debug'] is True
            )
            # upgrade virt-who to check the configurations not change.
            package_upgrade(ssh_host, 'virt-who',
                            rpm=f'{file_path}/{VIRTWHO_PKG}.rpm')
            result = virtwho.run_service()
            assert (
                package_check(ssh_host, 'virt-who') == VIRTWHO_PKG and
                result['send'] == 1 and
                result['error'] == 0 and
                result['debug'] is True
            )
        finally:
            if package_check(ssh_host, 'virt-who') != VIRTWHO_PKG:
                package_upgrade(ssh_host, 'virt-who')
