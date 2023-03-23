"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho.base import msg_search
from virtwho import REGISTER
from virtwho import HYPERVISOR
from virtwho import SECOND_HYPERVISOR_FILE
from virtwho import SECOND_HYPERVISOR_SECTION

from virtwho.base import encrypt_password
from virtwho.configure import hypervisor_create


@pytest.mark.usefixtures('function_virtwho_d_conf_clean')
@pytest.mark.usefixtures('class_debug_true')
@pytest.mark.usefixtures('class_globalconf_clean')
class TestRHSMPositive:
    @pytest.mark.tier1
    def test_no_rhsm_options(self, virtwho, function_hypervisor, sm_host,
                             rhsm_assertion):
        """Test the /etc/virt-who.d/x.conf without any rhsm option

        :title: virt-who: rhsm: test no rhsm options in config file (positive)
        :id: 09167890-bbd0-470a-a342-66bbe29f91f9
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Configure virt-who file without rhsm options
            2. Register virt-who host and run virt-who
            3. Unregister virt-who host and run virt-who
        :expectedresults:
            1. Virt-who can report without rhsm options when virt-who host
                registered.
            2. Virt-who cannot report without rhsm options when virt-who host
                unregistered.
        """
        function_hypervisor.create(rhsm=False)
        sm_host.register()
        result = virtwho.run_cli()
        assert (result['send'] == 1
                and result['error'] == 0)

        sm_host.unregister()
        result = virtwho.run_cli()
        assert (result['send'] == 0
                and result['error'] != 0
                and msg_search(result['error_msg'],
                               rhsm_assertion['unregister_host']))

    @pytest.mark.tier1
    def test_rhsm_encrypted_password(self, virtwho, function_hypervisor,
                                     ssh_host, register_data):
        """Test the rhsm_encrypted_password= option in /etc/virt-who.d/x.conf

        :title: virt-who: rhsm: test rhsm_encrypted_password option (positive)
        :id: a748e63c-0c80-444d-8bc4-0f6cad783be6
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Delete the rhsm_password= option
            2. Encrypted rhsm_password to define the rhsm_encrypted_password=.
            3. Run virt-who service

        :expectedresults:
            1. Succeeded to run the virt-who with rhsm_encrypted_password
        """
        # rhsm_encrypted_password option is valid value
        function_hypervisor.delete('rhsm_password')
        encrypted_pwd = encrypt_password(ssh_host, register_data['password'])
        function_hypervisor.update('rhsm_encrypted_password', encrypted_pwd)
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)


@pytest.mark.usefixtures('class_unregister_host')
@pytest.mark.usefixtures('class_debug_true')
@pytest.mark.usefixtures('class_globalconf_clean')
@pytest.mark.usefixtures('function_virtwho_d_conf_clean')
class TestRHSMNegative:
    @pytest.mark.tier2
    @pytest.mark.notLocal
    def test_owner(self, virtwho, function_hypervisor, rhsm_assertion):
        """Test the owner= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm: test owner option (negative)
        :id: ae0abf52-ab25-4544-a0f7-5ba13bcfaf3e
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Unregister virt-who host
            2. Run virt-who with owner=[invalid value]
            3. Run virt-who with owner=null
            4. Run virt-who without owner=
            5. Run virt-who without owner= together with anogher good config
            6. Run virt-who with owner=null together with anogher good config
        :expectedresults:
            1. Invalid: virt-who starts but fails to report with error
            2. Null: virt-who starts but fails to report with error
            3. Disable: virt-who fails to start with error
            4. Disable with another good config: virt-who starts but only
                reports the good config, and prints error for the bad one
            5. Null with another good config: virt-who starts but only
                reports the good config, and prints error for the bad one
        """
        owner = rhsm_assertion['owner']

        # invalid
        invalid = owner['invalid']
        for key, value in invalid.items():
            function_hypervisor.update('owner', key)
            result = virtwho.run_service()
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
    def test_rhsm_hostname(self, virtwho, function_hypervisor,
                           rhsm_assertion, function_rhsmconf_recovery):
        """Test the rhsm_hostname= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm: test rhsm_hostname option (negative)
        :id: 055f5ea2-e4f2-4342-9fb8-aa0e4b765394
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Unregister virt-who host
            2. Recover /etc/rhsm/rhsm.conf to default
            3. Run virt-who with rhsm_hostname=[invalid value]
            4. Run virt-who with rhsm_hostname=null
            5. Run virt-who without rhsm_hostname=
        :expectedresults:
            1. Invalid: virt-who starts but fails to report with error
            2. Null: virt-who starts but fails to report with error
            3. Disable: virt-who starts but fails to report with error
        """
        rhsm_hostname = rhsm_assertion['rhsm_hostname']

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
    def test_rhsm_port(self, virtwho, function_hypervisor,
                       rhsm_assertion, function_rhsmconf_recovery):
        """Test the rhsm_port= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm: test rhsm_port option (negative)
        :id: a1149344-b6c0-485c-96fc-9da4705e6b15
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Unregister virt-who host
            2. Recover /etc/rhsm/rhsm.conf to default
            3. Run virt-who with rhsm_port=[invalid value]
            4. Run virt-who with rhsm_port=null
            5. Run virt-who without rhsm_port=
        :expectedresults:
            1. Invalid: virt-who starts but fails to report with error
            2. Null: virt-who reports successfully
                (use the port=443 in rhsm.conf)
            3. Disable: virt-who reports successfully
                (use the port=443 in rhsm.conf)
        """
        rhsm_port = rhsm_assertion['rhsm_port']

        # invalid value
        invalid = rhsm_port['invalid']
        for key, value in invalid.items():
            function_hypervisor.update('rhsm_port', key)

            result = virtwho.run_service(wait=180)
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
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)

    @pytest.mark.tier2
    @pytest.mark.notLocal
    def test_rhsm_prefix(self, virtwho, function_hypervisor,
                         rhsm_assertion, function_rhsmconf_recovery):
        """Test the rhsm_prefix= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm: test rhsm_prefix option (negative)
        :id: 5c91dca3-835a-4d5a-936e-e93d3a13d1f6
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Unregister virt-who host
            2. Recover /etc/rhsm/rhsm.conf to default
            3. Run virt-who with rhsm_prefix=[invalid value]
            4. Run virt-who with rhsm_prefix=null
            5. Run virt-who without rhsm_prefix=
        :expectedresults:
            1. Invalid: virt-who starts but fails to report with error
            2. Null: virt-who reports successfully
                (use the prefix=/subscription in rhsm.conf)
            3. Disable: virt-who reports successfully
                (use the prefix=/subscription in rhsm.conf)
        """
        rhsm_prefix = rhsm_assertion['rhsm_prefix']

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
    def test_rhsm_username(self, virtwho, function_hypervisor, rhsm_assertion):
        """Test the rhsm_username= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm: test rhsm_username option (negative)
        :id: c6db8133-678f-41e0-8ce9-649afe6a6615
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Unregister virt-who host
            2. Recover /etc/rhsm/rhsm.conf to default
            3. Run virt-who with rhsm_username=[invalid value]
            4. Run virt-who with rhsm_username=null
            5. Run virt-who with rhsm_username=non-ascii
            6. Run virt-who without rhsm_username=
        :expectedresults:
            1. Invalid: virt-who starts but fails to report with error
            2. Null: virt-who starts but fails to report with error
            3. Non-ASCII: virt-who starts but fails to report with decode error
            4. Disable: virt-who starts but fails to report with decode error
        """
        rhsm_username = rhsm_assertion['rhsm_username']

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
    def test_rhsm_password(self, virtwho, function_hypervisor, rhsm_assertion):
        """Test the rhsm_password= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm: test rhsm_password option (negative)
        :id: 0a9496e2-8634-4725-983f-d56a2133e3d4
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Unregister virt-who host
            2. Recover /etc/rhsm/rhsm.conf to default
            3. Run virt-who with rhsm_password=[invalid value]
            4. Run virt-who with rhsm_password=null
            5. Run virt-who with rhsm_password=non-ascii
            6. Run virt-who without rhsm_password=
        :expectedresults:
            1. Invalid: virt-who starts but fails to report with error
            2. Null: virt-who starts but fails to report with error
            3. Non-ASCII: virt-who starts but fails to report with decode error
            4. Disable: virt-who starts but fails to report with decode error
        """
        rhsm_password = rhsm_assertion['rhsm_password']

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

    @pytest.mark.tier2
    def test_rhsm_encrypted_password(self, virtwho, function_hypervisor,
                                     ssh_host, rhsm_assertion):
        """Test the rhsm_encrypted_password= option in /etc/virt-who.d/x.conf

        :title: virt-who: rhsm: test rhsm_encrypted_password option (negative)
        :id: daab24a6-21a9-49dc-a129-46c742a9ef84
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Delete the rhsm_password option
            2. Run virt-who with rhsm_password=[invalid value]
            3. Run virt-who with rhsm_password=null
            4. Run virt-who service

        :expectedresults:
            1. Invalid: virt-who starts but fails to report with error
            2. Null: virt-who starts but fails to report with error
        """
        # rhsm_encrypted_password option is bad value
        encrypted_password = rhsm_assertion['rhsm_encrypted_password']
        function_hypervisor.delete('rhsm_password')

        # invalid value
        invalid = encrypted_password['invalid']
        for key, value in invalid.items():
            function_hypervisor.update('rhsm_encrypted_password', key)
            result = virtwho.run_service()
            assert (result['error'] is not 0
                    and result['send'] == 0
                    and result['thread'] == 1
                    and msg_search(result['log'], value))
