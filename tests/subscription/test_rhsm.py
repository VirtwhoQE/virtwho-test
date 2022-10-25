"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho.base import msg_search
from virtwho import REGISTER
from virtwho import RHEL_COMPOSE
from virtwho import HYPERVISOR
from virtwho import SECOND_HYPERVISOR_FILE
from virtwho import SECOND_HYPERVISOR_SECTION
from virtwho import logger


from virtwho.base import encrypt_password
from virtwho.base import get_host_domain_id
from virtwho.configure import hypervisor_create


@pytest.mark.usefixtures('function_virtwho_d_conf_clean')
@pytest.mark.usefixtures('class_debug_true')
@pytest.mark.usefixtures('class_globalconf_clean')
class TestRHSMPositive:
    @pytest.mark.tier1
    def test_no_rhsm_options(self, virtwho, function_hypervisor, sm_host):
        """Test the /etc/virt-who.d/x.conf without any rhsm option

        :title: virt-who: rhsm: test no rhsm options in config file
        :id:
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Configure virt-who file without rhsm options
            2. Register virt-who host and run virt-who
            3. Unregister virt-who host and run virt-who
        :expectedresults:
            1. Virt-who can report without rhsm options when virt-who host registered.
            2. Virt-who cannot report without rhsm options when virt-who host unregistered.
        """
        function_hypervisor.create(rhsm=False)
        sm_host.register()
        result = virtwho.run_cli()
        assert (result['send'] == 1
                and result['error'] == 0)

        sm_host.unregister()
        result = virtwho.run_cli()
        assert (result['send'] == 0
                and result['error'] != 0)


@pytest.mark.usefixtures('function_virtwho_d_conf_clean')
@pytest.mark.usefixtures('class_debug_true')
@pytest.mark.usefixtures('class_globalconf_clean')
class TestRHSMNegative:
    @pytest.mark.tier2
    @pytest.mark.notLocal
    def test_owner(self, virtwho, function_hypervisor, register_assertion):
        """Test the owner= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm: test owner option
        :id:
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Test
        :expectedresults:
            1.
        """
        owner = register_assertion['owner']

        # invalid
        invalid = owner['invalid']
        for key, value in invalid.items():
            function_hypervisor.update('owner', key)
            result = virtwho.run_service()
            logger.info(f"----{result['error_msg']}")
            assert (result['error'] is not 0
                    and result['send'] == 0
                    and result['thread'] == 1
                    and msg_search(result['error_msg'], value))

        # disable
        function_hypervisor.delete('owner')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 0
                and result['thread'] == 0
                and msg_search(result['error_msg'], owner['disable']))

        # disable but another config is ok
        hypervisor_create(HYPERVISOR, REGISTER, SECOND_HYPERVISOR_FILE, SECOND_HYPERVISOR_SECTION)
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and msg_search(result['error_msg'],
                               owner['disable_with_another_good']))

        # null but another config is ok
        function_hypervisor.update('owner', '')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and msg_search(result['error_msg'],
                               owner['null_with_another_good']))

    @pytest.mark.tier2
    @pytest.mark.notLocal
    def test_rhsm_hostname(self, virtwho, function_hypervisor, register_assertion):
        """Test the rhsm_hostname= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm: test rhsm_hostname option
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
        rhsm_hostname = register_assertion['rhsm_hostname']

        # invalid value
        invalid = rhsm_hostname['invalid']
        for key, value in invalid.items():
            function_hypervisor.update('rhsm_hostname', key)
            result = virtwho.run_service()
            assert (result['error'] is not 0
                    and result['send'] == 0
                    and result['thread'] == 1
                    and msg_search(result['error_msg'], value))

        # disable
        function_hypervisor.delete('rhsm_hostname')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 0
                and result['thread'] == 1
                and msg_search(result['error_msg'], rhsm_hostname['disable']))

    @pytest.mark.tier2
    @pytest.mark.notLocal
    def test_rhsm_port(self, virtwho, function_hypervisor, register_assertion):
        """Test the rhsm_port= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm: test rhsm_port option
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
        rhsm_port = register_assertion['rhsm_port']

        # invalid value
        invalid = rhsm_port['invalid']
        for key, value in invalid.items():
            function_hypervisor.update('rhsm_port', key)
            result = virtwho.run_service()
            assert (result['error'] is not 0
                    and result['send'] == 0
                    and result['thread'] == 1
                    and msg_search(result['error_msg'], value))

        # null
        function_hypervisor.update('rhsm_port', '')
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)

        # disable
        function_hypervisor.delete('rhsm_port')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 0
                and result['thread'] == 1)

    @pytest.mark.tier2
    @pytest.mark.notLocal
    def test_rhsm_prefix(self, virtwho, function_hypervisor, register_assertion):
        """Test the rhsm_prefix= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm: test rhsm_prefix option
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
        rhsm_prefix = register_assertion['rhsm_prefix']

        # invalid value
        invalid = rhsm_prefix['invalid']
        for key, value in invalid.items():
            function_hypervisor.update('rhsm_prefix', key)
            result = virtwho.run_service()
            assert (result['error'] is not 0
                    and result['send'] == 0
                    and result['thread'] == 1
                    and msg_search(result['error_msg'], value))

        # null
        function_hypervisor.update('rhsm_prefix', '')
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)

        # disable
        function_hypervisor.delete('rhsm_prefix')
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)

    @pytest.mark.tier2
    @pytest.mark.notLocal
    def test_rhsm_username(self, virtwho, function_hypervisor, register_assertion):
        """Test the rhsm_username= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm: test rhsm_username option
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
        rhsm_username = register_assertion['rhsm_username']

        # invalid value
        invalid = rhsm_username['invalid']
        for key, value in invalid.items():
            function_hypervisor.update('rhsm_username', key)
            result = virtwho.run_service()
            assert (result['error'] is not 0
                    and result['send'] == 0
                    and result['thread'] == 1
                    and msg_search(result['error_msg'], value))

        # disable
        function_hypervisor.delete('rhsm_username')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 0
                and result['thread'] == 1
                and msg_search(result['error_msg'], rhsm_username['disable']))

    @pytest.mark.tier2
    @pytest.mark.notLocal
    def test_rhsm_username(self, virtwho, function_hypervisor, register_assertion):
        """Test the rhsm_username= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm: test rhsm_username option
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
        rhsm_password = register_assertion['rhsm_password']

        # invalid value
        invalid = rhsm_password['invalid']
        for key, value in invalid.items():
            function_hypervisor.update('rhsm_password', key)
            result = virtwho.run_service()
            assert (result['error'] is not 0
                    and result['send'] == 0
                    and result['thread'] == 1
                    and msg_search(result['error_msg'], value))

        # disable
        function_hypervisor.delete('rhsm_password')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 0
                and result['thread'] == 1
                and msg_search(result['error_msg'], rhsm_password['disable']))