"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho import logger
from virtwho.settings import config
from virtwho.register import Satellite


@pytest.mark.usefixtures('globalconf_clean')
@pytest.mark.usefixtures('hypervisor_create')
class TestSmoke:
    def test_host_guest_association(
            self, virtwho, satellite, hypervisor_data, register_data,
            sm_guest, ssh_guest
    ):
        """Just a demo

        :title: virt-who: rhsm: test vdc sku attach
        :id:
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        guest_uuid = hypervisor_data['guest_uuid']
        guest_hostname = hypervisor_data['guest_hostname']
        hypervisor_hostname = hypervisor_data['hypervisor_hostname']
        default_org = register_data['default_org']
        # assert the association in mapping
        result = virtwho.run_cli()
        mappings = result['mappings']
        associated_hypervisor_in_mapping = mappings[default_org][guest_uuid][
            'guest_hypervisor']
        assert (result['send'] == 1
                and result['error'] == 0
                and associated_hypervisor_in_mapping == hypervisor_hostname)
        # assert the association in satellite web
        sm_guest.register()
        assert satellite.associate(hypervisor_hostname, guest_hostname) is not False

    def test_rhsm_options(self, virtwho, hypervisor, sm_host, debug_true):
        """Just a demo

        :title: virt-who: rhsm: test vdc sku unattach
        :id: 
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        hypervisor.destroy()
        hypervisor.create(rhsm=False)
        sm_host.register()
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0)

        sm_host.unregister()
        result = virtwho.run_service()
        assert (result['send'] == 0
                and result['error'] != 0)

        hypervisor.destroy()
        hypervisor.create(rhsm=True)
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0)

    def test_rhsm_proxy(self, virtwho, hypervisor, data):
        """Just a demo

        :title: virt-who: rhsm: test vdc sku unattach
        :id:
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        proxy = data['proxy']
        logger.info(f'---{proxy}---')
        connection_log = proxy['connection_log']
        proxy_log = proxy['proxy_log']
        hypervisor.update('rhsm_proxy_hostname', proxy['server'])
        hypervisor.update('rhsm_proxy_port', proxy['port'])
        result = virtwho.run_cli()
        assert (result['send'] == 1
                and result['error'] == 0
                and connection_log in result['log']
                and proxy_log in result['log'])

        errors = data['proxy']['error']
        hypervisor.update('rhsm_proxy_hostname', proxy['bad_server'])
        hypervisor.update('rhsm_proxy_port', proxy['bad_port'])
        result = virtwho.run_cli()
        assert (result['send'] == 0
                and result['error'] != 0
                and any(error in result['log'] for error in errors))

    def test_hypervisor_id(self):
        """Just a demo

        :title: virt-who: rhsm: test vdc sku unattach
        :id:
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        pass

    def test_vdc_sku(self):
        """Just a demo

        :title: virt-who: rhsm: test vdc sku unattach
        :id:
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        pass

    def test_temporary_sku(self):
        """Just a demo

        :title: virt-who: rhsm: test vdc sku unattach
        :id:
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        pass
