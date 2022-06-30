"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest


@pytest.mark.usefixtures('globalconf_clean')
@pytest.mark.usefixtures('hypervisor_create')
class TestSmoke:
    def test_host_guest_association(self, virtwho, satellite, hypervisor_data,
                                    register_data, sm_guest, ssh_guest):
        """Test the host-to-guest association in mapping log and Satellite
        Web UI.

        :title: virt-who: satellite smoke: test host-to-guest association
        :id: e2d4b364-34bf-402c-bb28-93ec81e7b11d
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. run virt-who against Satellite
            2. assert the association in mapping
            3. assert the association in Satellite WebUI
        :expectedresults:
            1. the host and guest are associated in the both mapping
            and Satellite WebUI
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
        # assert the association in Satellite web
        sm_guest.register()
        assert satellite.associate(hypervisor_hostname, guest_hostname) is not False

    def test_rhsm_options(self, virtwho, hypervisor, sm_host, debug_true):
        """Test the rhsm_hostname/username/password/prefix/port

        :title: virt-who: satellite smoke: test rhsm options
        :id: 8f674edf-9abb-43e7-8c72-457a1e4b0b33
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. define all the rhsm options in /etc/rhsm/rhsm.conf
                1.1 register virt-who host to satellite, which will configure
                    the /etc/rhsm/rhsm.conf
                1.2 configure /etc/virt-who.d/hypervisor.conf without rhsm
                    options
                1.3 run virt-who service
            2. define all the rhsm options in /etc/virt-who.d/hypervisor.conf
                1.1 unregister virt-who host, and recover /etc/rhsm/rhsm.conf
                    to default
                1.2 configure /etc/virt-who.d/hypervisor.conf with all rhsm
                    options
                1.3 run virt-who service
        :expectedresults:
            1. virt-who can report successfully
            2. virt-who can report successfully
        """
        try:
            hypervisor.create(rhsm=False)
            sm_host.register()
            result = virtwho.run_cli()
            assert (result['send'] == 1
                    and result['error'] == 0)

            sm_host.unregister()
            result = virtwho.run_cli()
            assert (result['send'] == 0
                    and result['error'] != 0)
        finally:
            hypervisor.create(rhsm=True)
            result = virtwho.run_cli()
            assert (result['send'] == 1
                    and result['error'] == 0)

    def test_rhsm_proxy(self, virtwho, hypervisor, proxy_data, register_data):
        """Test the rhsm_proxy in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: satellite smoke: test rhsm proxy
        :id: 8f4d5516-3afe-4ceb-a492-ace4a5ac391d
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. run virt-who with good rhsm proxy
            2. run virt-who with bad rhsm proxy
            3. run virt-who with bad rhsm proxy and no_proxy
        :expectedresults:
            1. virt-who run well with good rhsm proxy
            2. virt-who fails to run with bad rhsm proxy
            3. virt-who run well with bad rhsm proxy and no_proxy
        """
        # run virt-who with good rhsm proxy
        connection_log = proxy_data['connection_log']
        proxy_log = proxy_data['proxy_log']
        hypervisor.update('rhsm_proxy_hostname', proxy_data['server'])
        hypervisor.update('rhsm_proxy_port', proxy_data['port'])
        result = virtwho.run_cli()
        assert (result['send'] == 1
                and result['error'] == 0
                and connection_log in result['log']
                and proxy_log in result['log'])
        # run virt-who with bad rhsm proxy
        errors = proxy_data['error']
        hypervisor.update('rhsm_proxy_hostname', proxy_data['bad_server'])
        hypervisor.update('rhsm_proxy_port', proxy_data['bad_port'])
        result = virtwho.run_cli()
        assert (result['send'] == 0
                and result['error'] != 0
                and any(error in result['log'] for error in errors))
        # run virt-who with bad rhsm proxy and no_proxy
        hypervisor.update('rhsm_no_proxy', register_data['server'])
        result = virtwho.run_cli()
        assert (result['send'] == 1
                and result['error'] == 0
                and connection_log not in result['log']
                and proxy_log not in result['log'])

        hypervisor.delete('rhsm_no_proxy')
        hypervisor.delete('rhsm_proxy_port')
        hypervisor.delete('rhsm_proxy_hostname')

    # def test_hypervisor_id(self, hypervisor):
    #     """Test hypervisor_id option in /etc/virt-who.d/hypervisor.conf
    #
    #     :title: virt-who: rhsm: test vdc sku unattach
    #     :id: 0ee0c7ab-78b9-48d3-b028-f004cb802b15
    #     :caseimportance: High
    #     :tags: tier1
    #     :customerscenario: false
    #     :upstream: no
    #     :steps:
    #         1.
    #     :expectedresults:
    #         1.
    #     """
    #     pass
    #
    # def test_vdc_sku(self):
    #     """Just a demo
    #
    #     :title: virt-who: rhsm: test vdc sku unattach
    #     :id: 998ae998-c003-4495-ac3a-4da075cfcdc5
    #     :caseimportance: High
    #     :tags: tier1
    #     :customerscenario: false
    #     :upstream: no
    #     :steps:
    #         1.
    #     :expectedresults:
    #         1.
    #     """
    #     pass
    #
    # def test_temporary_sku(self):
    #     """Just a demo
    #
    #     :title: virt-who: rhsm: test vdc sku unattach
    #     :id: c016e44b-6de4-4585-a282-94189639025f
    #     :caseimportance: High
    #     :tags: tier1
    #     :customerscenario: false
    #     :upstream: no
    #     :steps:
    #         1.
    #     :expectedresults:
    #         1.
    #     """
    #     pass
