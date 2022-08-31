"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho import REGISTER
from virtwho import RHEL_COMPOSE
from virtwho import HYPERVISOR
from virtwho.configure import VirtwhoHypervisorConfig


@pytest.mark.usefixtures('function_virtwho_d_conf_clean')
@pytest.mark.usefixtures('debug_true')
@pytest.mark.usefixtures('globalconf_clean')
class TestEsx:
    @pytest.mark.tier2
    def test_type(self, virtwho, function_hypervisor):
        """Test the type= option in /etc/virt-who.d/test_esx.conf

        :title: virt-who: esx: test type option
        :id: 0f2fcf4f-ac60-4c3c-905a-fabe22536ab2
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Configure type option with invalid value.
            2. Disable the type option in the config file.
            3. Create another valid config file
            4. Update the type option with null value

        :expectedresults:
            1. Failed to run the virt-who service, find error messages
            2. Find error message: Error in libvirt backend
            3. Find error message, the good config works fine
            4. The good config works fine
        """
        # type option is invalid value
        validate_values = ['xxx', '红帽€467aa', '']
        for value in validate_values:
            function_hypervisor.update('type', value)
            result = virtwho.run_service()
            assert (result['error'] is not 0
                    and result['send'] == 0
                    and result['thread'] == 0)
            if 'RHEL-9' in RHEL_COMPOSE:
                assert f"Unsupported virtual type '{value}' is set" in result['error_msg']
            else:
                assert "virt-who can't be started" in result['error_msg']

        # type option is disable
        function_hypervisor.delete('type')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 0
                and result['thread'] == 1
                and 'Error in libvirt backend' in result['error_msg'])

        # type option is disable but another config is ok
        new_file = '/etc/virt-who.d/new_config.conf'
        section_name = 'virtwho-config'
        new_hypervisor = VirtwhoHypervisorConfig(HYPERVISOR, REGISTER, new_file, section_name)
        new_hypervisor.create()
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and 'Error in libvirt backend' in result['error_msg'])

        # type option is null but another config is ok
        function_hypervisor.update('type', '')
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['thread'] == 1)
        if 'RHEL-9' in RHEL_COMPOSE:
            assert result['error'] == 1
        else:
            assert result['error'] == 0

    @pytest.mark.tier2
    def test_server(self, virtwho, function_hypervisor):
        """Test the server= option in /etc/virt-who.d/test_esx.conf

        :title: virt-who: esx: test server option
        :id: 0f2fcf4f-ac60-4c3c-905a-fabe22536ab2
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Configure server option with invalid value.
            2. Disable the server option in the config file.
            3. Create another valid config file
            4. Update the server option with null value

        :expectedresults:
            1. Failed to run the virt-who service, find error messages
            2. Find error message: virt-who can't be started
            3. Find error message: 'Required option: "server" not set', the good config works fine
            4. Find error message: 'Option server needs to be set in config', the good config
            works fine
        """
        # server option is wrong/null value
        validate_values = ['xxxxxx', '红帽€467aa', '']
        for value in validate_values:
            function_hypervisor.update('server', value)
            result = virtwho.run_service()
            assert (result['error'] is not 0
                    and result['send'] == 0)
            if value == 'xxxxxx':
                assert result['thread'] == 1
                assert 'Name or service not known' in result['error_msg']
            elif value == '红帽€467aa':
                assert result['thread'] == 0
                assert 'Option server needs to be ASCII characters only' in result['error_msg']
            elif value == '':   # server option is null value
                assert result['thread'] == 0
                assert 'Option server needs to be set in config' in result['error_msg']

        # server option is disable
        function_hypervisor.delete('server')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 0
                and result['thread'] == 0
                and "virt-who can't be started" in result['error_msg'])

        # server option is disable but another config is ok
        new_file = '/etc/virt-who.d/new_config.conf'
        section_name = 'virtwho-config'
        new_hypervisor = VirtwhoHypervisorConfig(HYPERVISOR, REGISTER, new_file, section_name)
        new_hypervisor.create()
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and 'Required option: "server" not set' in result['error_msg'])

        # server option is null but another config is ok
        function_hypervisor.update('server', '')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and 'Option server needs to be set in config' in result['error_msg'])

    @pytest.mark.tier2
    def test_username(self, function_hypervisor, virtwho):
        """Test the username= option in /etc/virt-who.d/test_esx.conf

        :title: virt-who: esx: test username option
        :id: 98359dec-7e49-4037-8399-8224e054c5b4
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Configure username option with invalid value.
            2. Disable the username option in the config file.
            3. Create another valid config file
            4. Update the username option with null value

        :expectedresults:
            1. Failed to run the virt-who service, find error message: 'Unable to login to ESX'
            2. Find error message: 'Required option: "username" not set'
            3. Find error message: 'Required option: "username" not set', the good config
            works fine
            4. Find error message: 'Unable to login to ESX', the good config works fine
        """
        # username option is wrong value
        validate_values = ['xxxxxx', '红帽€467aa', '']
        for value in validate_values:
            function_hypervisor.update('username', value)
            result = virtwho.run_service()
            assert (result['error'] is not 0
                    and result['send'] == 0
                    and result['thread'] == 1
                    and 'Unable to login to ESX' in result['error_msg'])

        # username option is disable
        function_hypervisor.delete('username')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 0
                and result['thread'] == 0
                and 'Required option: "username" not set' in result['error_msg'])

        # username option is disable but another config is ok
        new_file = '/etc/virt-who.d/new_config.conf'
        section_name = 'virtwho-config'
        new_hypervisor = VirtwhoHypervisorConfig(HYPERVISOR, REGISTER, new_file, section_name)
        new_hypervisor.create()
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and 'Required option: "username" not set' in result['error_msg'])

        # username option is null but another config is ok
        function_hypervisor.update('username', '')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and 'Unable to login to ESX' in result['error_msg'])

    @pytest.mark.tier2
    def test_password(self, virtwho, function_hypervisor):
        """Test the password= option in /etc/virt-who.d/test_esx.conf

        :title: virt-who: esx: test password option
        :id: 19f7305b-0ac5-4ac8-8d39-d32168e5b634
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Configure password option with invalid value.
            2. Disable the password option in the config file.
            3. Create another valid config file
            4. Update the password option with null value

        :expectedresults:
            1. Failed to run the virt-who service, find error message: 'Unable to login to ESX'
            2. Find error message: 'Required option: "password" not set'
            3. Find error message: 'Required option: "password" not set', the good config
            works fine
            4. Find error message: 'Unable to login to ESX', the good config works fine
        """
        # password option is wrong value
        validate_values = ['xxxxxx', '红帽€467aa', '']
        for value in validate_values:
            function_hypervisor.update('password', value)
            result = virtwho.run_service()
            assert (result['error'] is not 0
                    and result['send'] == 0
                    and result['thread'] == 1
                    and 'Unable to login to ESX' in result['error_msg'])

        # password option is disable
        function_hypervisor.delete('password')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 0
                and result['thread'] == 0
                and 'Required option: "password" not set' in result['error_msg'])

        # password option is disable but another config is ok
        new_file = '/etc/virt-who.d/new_config.conf'
        section_name = 'virtwho-config'
        new_hypervisor = VirtwhoHypervisorConfig(HYPERVISOR, REGISTER, new_file, section_name)
        new_hypervisor.create()
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and 'Required option: "password" not set' in result['error_msg'])

        # password option is null but another config is ok
        function_hypervisor.update('password', '')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and 'Unable to login to ESX' in result['error_msg'])

    @pytest.mark.tier1
    def test_hypervisor_id(self, virtwho, function_hypervisor, hypervisor_data, globalconf, rhsm, satellite):
        """Test the hypervisor_id= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test hypervisor_id function
        :id: be5877d9-3a59-46aa-bd9a-6c1e3ed5f5ee
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. clean all virt-who global configurations
            2. run virt-who with hypervisor_id=uuid
            3. run virt-who with hypervisor_id=hostname
            4. run virt-who with hypervisor_id=hwuuid

        :expectedresults:

            hypervisor id shows uuid/hostname/hwuuid in mapping as the setting.
        """
        hypervisor_ids = ['hostname', 'uuid', 'hwuuid']
        for hypervisor_id in hypervisor_ids:
            function_hypervisor.update('hypervisor_id', hypervisor_id)
            result = virtwho.run_service()
            assert (result['error'] == 0
                    and result['send'] == 1
                    and result['thread'] == 1
                    and result['hypervisor_id'] == hypervisor_data[f'hypervisor_{hypervisor_id}'])
            if REGISTER == 'rhsm':
                assert rhsm.consumers(hypervisor_data['hypervisor_hostname'])
                rhsm.delete(hypervisor_data['hypervisor_hostname'])
            else:
                if hypervisor_id == 'hostname':
                    assert satellite.host_id(hypervisor_data['hypervisor_hostname'])
                    assert not satellite.host_id(hypervisor_data['hypervisor_uuid'])
                    assert not satellite.host_id(hypervisor_data['hypervisor_hwuuid'])
                elif hypervisor_id == 'uuid':
                    assert satellite.host_id(hypervisor_data['hypervisor_uuid'])
                    assert not satellite.host_id(hypervisor_data['hypervisor_hostname'])
                    assert not satellite.host_id(hypervisor_data['hypervisor_hwuuid'])
                else:
                    assert satellite.host_id(hypervisor_data['hypervisor_hwuuid'])
                    assert not satellite.host_id(hypervisor_data['hypervisor_hostname'])
                    assert not satellite.host_id(hypervisor_data['hypervisor_uuid'])
