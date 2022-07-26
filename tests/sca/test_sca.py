"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho.settings import config
from virtwho import REGISTER, HYPERVISOR
from virtwho.register import Satellite, RHSM

if REGISTER == 'satellite':
    register = Satellite(
        server=config.satellite.server,
        org=config.satellite.default_org,
        activation_key=config.satellite.activation_key
    )
else:
    register = RHSM()


@pytest.fixture(scope='class')
def sca_enable():
    """Enable SCA mode before run test cases"""
    register.sca(sca='enable')


@pytest.fixture(scope='class')
def sca_disable():
    """Disable SCA mode after finished all test cases"""
    yield
    register.sca(sca='disable')


@pytest.mark.usefixtures('globalconf_clean')
@pytest.mark.usefixtures('hypervisor_create')
@pytest.mark.usefixtures('debug_true')
@pytest.mark.usefixtures('sca_enable')
@pytest.mark.usefixtures('sca_disable')
class TestSCA:
    def test_hypervisor_facts(self, virtwho, hypervisor, hypervisor_data,
                              register_data):
        """Test the hypervisor facts in mapping

        :title: virt-who: sca: test hypervisor facts
        :id: d0ca112a-6965-4334-8b41-410bb4c74e0c
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Run virt-who to get the mapping
            2. Check the hypervisor facts
        :expectedresults:
            1. virt-who can get and send maping successfully
            2. the hypervisor facts of type, version, socket, dmi and cluster
                are expected.
        """
        register_org = register_data['default_org']
        hypervisor_hostname = hypervisor_data['hypervisor_hostname']
        result = virtwho.run_cli()
        assert (result['send'] == 1
                and result['error'] == 0)

        facts = result['mappings'][register_org][hypervisor_hostname]
        assert (facts['type'] == hypervisor_data['type']
                and facts['version'] == hypervisor_data['version']
                and facts['socket'] == hypervisor_data['cpu']
                and facts['dmi'] == hypervisor_data['hypervisor_uuid'])
        if HYPERVISOR in ['esx', 'rhevm', 'ahv']:
            assert facts['cluster'] == hypervisor_data['cluster']

    def test_host_to_guest_association(self, virtwho, sm_guest, ssh_guest,
                                       register_data, hypervisor_data,
                                       register_guest):
        """Test the host-to-guest association in mapping log and register server
        Web UI.

        :title: virt-who: sca: test host-to-guest association
        :id: 044a7c1b-92cb-43a0-a790-f81279e09a8b
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. run virt-who against Satellite/RHSM
            2. assert the association in mapping
            3. assert the association in Satellite/RHSM WebUI
        :expectedresults:
            1. the host and guest are associated in the both mapping
            and register server WebUI
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
        if REGISTER == 'satellite':
            assert register.associate(hypervisor_hostname, guest_hostname)
        else:
            assert register.associate(hypervisor_hostname, guest_uuid)

    def test_guest_entitlement_status(self, ssh_guest, register_guest,
                                      hypervisor_data):
        """Test the guest entitlement status.

        :title: virt-who: sca: test guest entitlement status
        :id: 7192ed31-a6fc-4cef-a7f3-7d19bdc2581f
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. register guest
            2. check the #subscription-manager status
            3. try to auto-attach subscription for guest
        :expectedresults:
            1. get the output with 'Content Access Mode is set to Simple Content
                Access' by #subscription-manager status
            2. get the 'This host's organization is in Simple Content Access
                mode. Auto-attach is disabled'
        """
        ret, output = ssh_guest.runcmd('subscription-manager status')
        assert ('Content Access Mode is set to Simple Content Access' in output)

        guest_hostname = hypervisor_data['guest_hostname']
        if 'satellite' in REGISTER:
            msg = "This host's organization is in Simple Content Access mode." \
                  " Auto-attach is disabled"
            result = register.attach(host=guest_hostname)
            assert msg in result
        else:
            # pending on bz2108415
            pass

    def test_hypervisor_entitlement_status(self, virtwho, hypervisor_data):
        """Test the hypervisor entitlement status.

        :title: virt-who: sca: test hypervisor entilement status
        :id: 15a23e94-934f-462e-b190-2942b33d6418
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. run virt-who to report mappings
            2. try to auto-attach subscription for hypervisor
        :expectedresults:
            get the 'This host's organization is in Simple Content Access
                mode. Auto-attach is disabled'
        """
        hypervisor_hostname = hypervisor_data['hypervisor_hostname']
        if 'satellite' in REGISTER:
            msg = "This host's organization is in Simple Content Access mode." \
                  " Auto-attach is disabled"
            result = register.attach(host=hypervisor_hostname)
            assert msg in result
        else:
            # pending on bz2108415
            pass
