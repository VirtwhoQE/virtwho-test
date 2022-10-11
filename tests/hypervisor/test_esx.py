"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest

from virtwho import REGISTER
from virtwho import RHEL_COMPOSE
from virtwho import HYPERVISOR
from virtwho import SECOND_HYPERVISOR_FILE
from virtwho import SECOND_HYPERVISOR_SECTION

from virtwho.base import encrypt_password
from virtwho.configure import hypervisor_create


@pytest.mark.usefixtures('function_virtwho_d_conf_clean')
@pytest.mark.usefixtures('debug_true')
@pytest.mark.usefixtures('globalconf_clean')
class TestEsxPositive:
    @pytest.mark.tier1
    def test_encrypted_password(self, virtwho, function_hypervisor,
                                hypervisor_data, ssh_host):
        """Test the encrypted_password= option in /etc/virt-who.d/test_esx.conf

        :title: virt-who: esx: test encrypted_password option
        :id: f07205a4-8f18-4c6b-8a2c-285664b59ed3
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Delete the password option, encrypted password for the hypervisor.
            2. Configure encrypted_password option with valid value, run the virt-who service.

        :expectedresults:
            2. Succeeded to run the virt-who, no error messages in the log info
        """
        # encrypted_password option is valid value
        function_hypervisor.delete('password')
        encrypted_pwd = encrypt_password(ssh_host, hypervisor_data['hypervisor_password'])
        function_hypervisor.update('encrypted_password', encrypted_pwd)
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)

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

    @pytest.mark.tier1
    def test_filter_hosts(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the filter_hosts= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test filter_hosts option
        :id: fd3e4f83-af37-4947-aa45-297ec47ccade
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Set hypervisor_id=hostname.
            2. Configure filter_hosts={hostname}, run the virt-who service.
            3. Configure filter_hosts={host_uuid}, run the virt-who service.
            4. Configure filter_hosts={host_hwuuid}, run the virt-who service.
        :expectedresults:
            2. Succeeded to run the virt-who, can find hostname in the log message
            3. Succeeded to run the virt-who, can find host_uuid in the log message
            4. Succeeded to run the virt-who, can find host_hwuuid in the log message
        """
        hypervisor_ids = ['hostname', 'uuid', 'hwuuid']
        for hypervisor_id in hypervisor_ids:
            function_hypervisor.update('hypervisor_id', hypervisor_id)
            hypervisor_id_data = hypervisor_data[f'hypervisor_{hypervisor_id}']

            function_hypervisor.update('filter_hosts', hypervisor_id_data)
            result = virtwho.run_service()
            assert (result['error'] == 0
                    and result['send'] == 1
                    and result['thread'] == 1
                    and hypervisor_id_data in str(result['mappings']))

    @pytest.mark.tier1
    def test_exclude_hosts(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the exclude_hosts= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test exclude_hosts option
        :id: ca2f2c5e-cb2a-4dea-9d8e-010058e31947
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Set hypervisor_id=hostname.
            2. Configure exclude_hosts={hostname}, run the virt-who service.
            3. Configure exclude_hosts={host_uuid}, run the virt-who service.
            4. Configure exclude_hosts={host_hwuuid}, run the virt-who service.
        :expectedresults:
            2. Succeeded to run the virt-who, cannot find hostname in the log message
            3. Succeeded to run the virt-who, cannot find host_uuid in the log message
            4. Succeeded to run the virt-who, cannot find host_hwuuid in the log message
        """
        hypervisor_ids = ['hostname', 'uuid', 'hwuuid']
        for hypervisor_id in hypervisor_ids:
            function_hypervisor.update('hypervisor_id', hypervisor_id)
            hypervisor_id_data = hypervisor_data[f'hypervisor_{hypervisor_id}']

            function_hypervisor.update('exclude_hosts', hypervisor_id_data)
            result = virtwho.run_service()
            assert (result['error'] == 0
                    and result['send'] == 1
                    and result['thread'] == 1
                    and hypervisor_id_data not in str(result['mappings']))

    @pytest.mark.tier1
    def test_simplified_vim(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the simplified_vim option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test simplified_vim option
        :id: 4e0a0ab3-8426-4121-8bbd-2e39794043d8
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. run virt-who with simplified_vim=true
            2. run virt-who with simplified_vim=false

        :expectedresults:
            1. Succeed to run the virt-who
            2. Succeed to run the virt-who
        """
        function_hypervisor.update('simplified_vim', 'true')
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)

        function_hypervisor.update('simplified_vim', 'false')
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)


@pytest.mark.usefixtures('function_virtwho_d_conf_clean')
@pytest.mark.usefixtures('debug_true')
@pytest.mark.usefixtures('globalconf_clean')
class TestEsxNegative:
    @pytest.mark.tier2
    def test_type(self, virtwho, function_hypervisor, esx_assertion):
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
        assertion = esx_assertion['type']
        assertion_invalid_list = list(assertion['invalid'].keys())
        for value in assertion_invalid_list:
            function_hypervisor.update('type', value)
            result = virtwho.run_service()
            assert (result['error'] is not 0
                    and result['send'] == 0
                    and result['thread'] == 0)
            if 'RHEL-9' in RHEL_COMPOSE:
                assert assertion['invalid'][f'{value}'] in result['error_msg']
            else:
                assert assertion['non_rhel9'] in result['error_msg']

        # type option is disable
        function_hypervisor.delete('type')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 0
                and result['thread'] == 1
                and assertion['disable'] in result['error_msg'])

        # type option is disable but another config is ok
        hypervisor_create(HYPERVISOR, REGISTER, SECOND_HYPERVISOR_FILE, SECOND_HYPERVISOR_SECTION)
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and assertion['disable_multi_configs'] in result['error_msg'])

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
    def test_server(self, virtwho, function_hypervisor, esx_assertion):
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
        # server option is invalid value
        assertion = esx_assertion['server']
        assertion_invalid_list = list(assertion['invalid'].keys())
        for value in assertion_invalid_list:
            function_hypervisor.update('server', value)
            result = virtwho.run_service()
            assert (result['error'] is not 0
                    and result['send'] == 0
                    and assertion['invalid'][f'{value}'] in result['error_msg'])

        # server option is disable
        function_hypervisor.delete('server')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 0
                and result['thread'] == 0
                and assertion['disable'] in result['error_msg'])

        # server option is disable but another config is ok
        hypervisor_create(HYPERVISOR, REGISTER, SECOND_HYPERVISOR_FILE, SECOND_HYPERVISOR_SECTION)
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and assertion['disable_multi_configs'] in result['error_msg'])

        # server option is null but another config is ok
        function_hypervisor.update('server', '')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and assertion['null_multi_configs'] in result['error_msg'])

    @pytest.mark.tier2
    def test_username(self, function_hypervisor, virtwho, esx_assertion):
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
        # username option is invalid value
        assertion = esx_assertion['username']
        assertion_invalid_list = list(assertion['invalid'].keys())
        for value in assertion_invalid_list:
            function_hypervisor.update('username', value)
            result = virtwho.run_service()
            assert (result['error'] is not 0
                    and result['send'] == 0
                    and result['thread'] == 1
                    and assertion['invalid'][f'{value}'] in result['error_msg'])

        # username option is disable
        function_hypervisor.delete('username')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 0
                and result['thread'] == 0
                and assertion['disable'] in result['error_msg'])

        # username option is disable but another config is ok
        hypervisor_create(HYPERVISOR, REGISTER, SECOND_HYPERVISOR_FILE, SECOND_HYPERVISOR_SECTION)
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and assertion['disable_multi_configs'] in result['error_msg'])

        # username option is null but another config is ok
        function_hypervisor.update('username', '')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and assertion['null_multi_configs'] in result['error_msg'])

    @pytest.mark.tier2
    def test_password(self, virtwho, function_hypervisor, esx_assertion):
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
        # password option is invalid value
        assertion = esx_assertion['password']
        assertion_invalid_list = list(assertion['invalid'].keys())
        for value in assertion_invalid_list:
            function_hypervisor.update('password', value)
            result = virtwho.run_service()
            assert (result['error'] is not 0
                    and result['send'] == 0
                    and result['thread'] == 1
                    and assertion['invalid'][f'{value}'] in result['error_msg'])

        # password option is disable
        function_hypervisor.delete('password')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 0
                and result['thread'] == 0
                and assertion['disable'] in result['error_msg'])

        # password option is disable but another config is ok
        hypervisor_create(HYPERVISOR, REGISTER, SECOND_HYPERVISOR_FILE, SECOND_HYPERVISOR_SECTION)
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and assertion['disable_multi_configs'] in result['error_msg'])

        # password option is null but another config is ok
        function_hypervisor.update('password', '')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and assertion['null_multi_configs'] in result['error_msg'])

    @pytest.mark.tier2
    def test_encrypted_password(self, virtwho, function_hypervisor, esx_assertion,
                                hypervisor_data, ssh_host):
        """Test the encrypted_password= option in /etc/virt-who.d/test_esx.conf

        :title: virt-who: esx: test encrypted_password option
        :id: 5014c314-8d57-44ce-820b-6de88810044e
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Configure password option with invalid value.
            2. Create another valid config file, run the virt-who service

        :expectedresults:
            1. Failed to run the virt-who service, find warning message:
            'Option "encrypted_password" cannot be decrypted'
            2. Find warning message: 'Option "encrypted_password" cannot be decrypted'
        """
        # encrypted_password option is invalid value
        function_hypervisor.delete('password')
        assertion = esx_assertion['encrypted_password']
        assertion_invalid_list = list(assertion['invalid'].keys())
        for value in assertion_invalid_list:
            function_hypervisor.update('encrypted_password', value)
            result = virtwho.run_service()
            assert (result['error'] is not 0
                    and result['send'] == 0
                    and result['thread'] == 0
                    and assertion['invalid'][f'{value}'] in result['warning_msg'])

        # encrypted_password option is valid but another config is ok
        hypervisor_create(HYPERVISOR, REGISTER, SECOND_HYPERVISOR_FILE, SECOND_HYPERVISOR_SECTION)
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and assertion['valid_multi_configs'] in result['warning_msg'])

    @pytest.mark.tier2
    def test_filter_hosts(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the filter_hosts= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test filter_hosts negative option
        :id: a32bacac-77e8-46a3-a2ca-b1f4691acb70
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Set hypervisor_id=hostname.
            2. Configure filter_hosts='*', run the virt-who service.
            3. Configure filter_hosts=wildcard, run the virt-who service.
            4. Configure filter_hosts=, run the virt-who service.
            5. Configure filter_hosts='', run the virt-who service.
            6. Configure filter_hosts="", run the virt-who service.
            7. Configure filter_hosts='{hostname}', run the virt-who service.
            8. Configure filter_hosts="{hostname}, run the virt-who service.
        :expectedresults:
            2. Succeeded to run the virt-who, can find hostname in the log message
            3. Succeeded to run the virt-who, can find hostname in the log message
            4. Succeeded to run the virt-who, cannot find hostname in the log message
            5. Succeeded to run the virt-who, cannot find hostname in the log message
            6. Succeeded to run the virt-who, cannot find hostname in the log message
            7. Succeeded to run the virt-who, can find hostname in the log message
            8. Succeeded to run the virt-who, can find hostname in the log message
        """
        hypervisor_ids = ['hostname', 'uuid', 'hwuuid']
        for hypervisor_id in hypervisor_ids:
            function_hypervisor.update('hypervisor_id', hypervisor_id)
            hypervisor_id_data = hypervisor_data[f'hypervisor_{hypervisor_id}']
            wildcard = hypervisor_id_data[:3] + '*' + hypervisor_id_data[4:]

            for filter_hosts in ['*', wildcard]:
                function_hypervisor.update('filter_hosts', filter_hosts)
                result = virtwho.run_service()
                assert (result['error'] == 0
                        and result['send'] == 1
                        and result['thread'] == 1
                        and hypervisor_id_data in str(result['mappings']))

            function_hypervisor.delete('hypervisor_id')

        hostname = hypervisor_data['hypervisor_hostname']
        function_hypervisor.update('hypervisor_id', 'hostname')

        # config filter_hosts with null option
        for filter_hosts in ['', "''", '""']:
            function_hypervisor.update('filter_hosts', filter_hosts)
            result = virtwho.run_service()
            assert (result['error'] == 0
                    and result['send'] == 1
                    and result['thread'] == 1
                    and hostname not in str(result['mappings']))

        # config filter_hosts with 'hostname' and "hostname"
        for filter_hosts in [f"'{hostname}'", f'"{hostname}"']:
            function_hypervisor.update('filter_hosts', filter_hosts)
            result = virtwho.run_service()
            assert (result['error'] == 0
                    and result['send'] == 1
                    and result['thread'] == 1
                    and hostname in str(result['mappings']))

    @pytest.mark.tier2
    def test_exclude_host(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the exclude_hosts= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test exclude_hosts negative option
        :id: fc8cd6bb-3e14-4929-8240-134d13995bfa
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Set hypervisor_id=hostname.
            2. Configure exclude_hosts='*', run the virt-who service.
            3. Configure exclude_hosts=wildcard, run the virt-who service.
            4. Configure exclude_hosts=, run the virt-who service.
            5. Configure exclude_hosts='', run the virt-who service.
            6. Configure exclude_hosts="", run the virt-who service.
            7. Configure exclude_hosts='{hostname}', run the virt-who service.
            8. Configure exclude_hosts="{hostname}, run the virt-who service.
        :expectedresults:
            2. Succeeded to run the virt-who, cannot find hostname in the log message
            3. Succeeded to run the virt-who, cannot find hostname in the log message
            4. Succeeded to run the virt-who, can find hostname in the log message
            5. Succeeded to run the virt-who, can find hostname in the log message
            6. Succeeded to run the virt-who, can find hostname in the log message
            7. Succeeded to run the virt-who, cannot find hostname in the log message
            8. Succeeded to run the virt-who, cannot find hostname in the log message
        """
        hypervisor_ids = ['hostname', 'uuid', 'hwuuid']
        for hypervisor_id in hypervisor_ids:
            function_hypervisor.update('hypervisor_id', hypervisor_id)
            hypervisor_id_data = hypervisor_data[f'hypervisor_{hypervisor_id}']
            wildcard = hypervisor_id_data[:3] + '*' + hypervisor_id_data[4:]

            for exclude_hosts in ['*', wildcard]:
                function_hypervisor.update('exclude_hosts', exclude_hosts)
                result = virtwho.run_service()
                assert (result['error'] == 0
                        and result['send'] == 1
                        and result['thread'] == 1
                        and hypervisor_id_data not in str(result['mappings']))

        hostname = hypervisor_data['hypervisor_hostname']
        function_hypervisor.update('hypervisor_id', 'hostname')

        for exclude_hosts in ['', "''", '""']:
            function_hypervisor.update('exclude_hosts', exclude_hosts)
            result = virtwho.run_service()
            assert (result['error'] == 0
                    and result['send'] == 1
                    and result['thread'] == 1
                    and hostname in str(result['mappings']))

        for exclude_hosts in [f"'{hostname}'", f'"{hostname}"']:
            function_hypervisor.update('exclude_hosts', exclude_hosts)
            result = virtwho.run_service()
            assert (result['error'] == 0
                    and result['send'] == 1
                    and result['thread'] == 1
                    and hostname not in str(result['mappings']))

    @pytest.mark.tier2
    def test_filter_exclude_mix(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the filter_hosts= and exclude_hosts= mix option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test filter_hosts and exclude_hosts related mix function
        :id: da952c46-6983-4c60-8b3d-c5704643ea2a
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Set hypervisor_id=host_uuid.
            2. run virt-who with filter_hosts=[host_uuid] and exclude_hosts=[host_uuid]
            3. run virt-who with filter_hosts=* and exclude_hosts=[host_uuid]
            4. run virt-who with exclude_hosts= and filter_hosts=[host_uuid]

        :expectedresults:
            2. Succeeded to run the virt-who, cannot find the log message "hypervisorId": "{host_uuid}"
            3. Succeeded to run the virt-who, cannot find the log message "hypervisorId": "{host_uuid}"
            4. Succeeded to run the virt-who, can find the log message "hypervisorId": "{host_uuid}"

        """
        # TODO: will add the filter_host_parents and exclude_host_parants related cases in next pr
        function_hypervisor.update('hypervisor_id', 'uuid')
        hypervisor_uuid = hypervisor_data['hypervisor_uuid']

        # run virt-who with filter_hosts=[host_uuid] and exclude_hosts=[host_uuid]
        function_hypervisor.update('filter_hosts', hypervisor_uuid)
        function_hypervisor.update('exclude_hosts', hypervisor_uuid)
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1
                and hypervisor_uuid not in str(result['mappings']))

        # run virt-who with filter_hosts=* and exclude_hosts=[host_uuid]
        function_hypervisor.update('filter_hosts', '*')
        function_hypervisor.update('exclude_hosts', hypervisor_uuid)
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1
                and hypervisor_uuid not in str(result['mappings']))

        # run virt-who with exclude_hosts= and filter_hosts=[host_uuid]
        function_hypervisor.update('filter_hosts', hypervisor_uuid)
        function_hypervisor.update('exclude_hosts', '')
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1
                and hypervisor_uuid in str(result['mappings']))
