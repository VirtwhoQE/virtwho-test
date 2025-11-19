"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""

import os
import random
import string
import json
import uuid
import pytest

from virtwho import logger
from virtwho import REGISTER
from virtwho import RHEL_COMPOSE
from virtwho import HYPERVISOR
from virtwho import FAKE_CONFIG_FILE
from virtwho import PRINT_JSON_FILE
from virtwho import SECOND_HYPERVISOR_FILE
from virtwho import SECOND_HYPERVISOR_SECTION

from virtwho.base import encrypt_password, msg_search
from virtwho.base import get_host_domain_id
from virtwho.configure import hypervisor_create
from virtwho.settings import TEMP_DIR

from hypervisor.virt.esx.powercli import PowerCLI


@pytest.mark.usefixtures("function_virtwho_d_conf_clean")
@pytest.mark.usefixtures("class_debug_true")
@pytest.mark.usefixtures("class_globalconf_clean")
class TestEsxPositive:
    @pytest.mark.tier1
    def test_encrypted_password(
        self, virtwho, function_hypervisor, hypervisor_data, ssh_host
    ):
        """Test the encrypted_password= option in /etc/virt-who.d/test_esx.conf

        :title: virt-who: esx: test encrypted_password option (positive)
        :id: f07205a4-8f18-4c6b-8a2c-285664b59ed3
        :caseimportance: High
        :tags: hypervisor,esx,tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Delete the password option, encrypted password for the hypervisor.
            2. Configure encrypted_password option with valid value, run the virt-who service.

        :expectedresults:
            2. Succeeded to run the virt-who, no error messages in the log info
        """
        # encrypted_password option is valid value
        function_hypervisor.delete("password")
        encrypted_pwd = encrypt_password(
            ssh_host, hypervisor_data["hypervisor_password"]
        )
        function_hypervisor.update("encrypted_password", encrypted_pwd)
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

    @pytest.mark.tier1
    @pytest.mark.satelliteSmoke
    @pytest.mark.fedoraSmoke
    def test_hypervisor_id(
        self, virtwho, function_hypervisor, hypervisor_data, globalconf, rhsm, satellite
    ):
        """Test the hypervisor_id= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test hypervisor_id function
        :id: be5877d9-3a59-46aa-bd9a-6c1e3ed5f5ee
        :caseimportance: High
        :tags: hypervisor,esx,tier1
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
        hypervisor_ids = ["uuid", "hwuuid", "hostname"]
        for hypervisor_id in hypervisor_ids:
            function_hypervisor.update("hypervisor_id", hypervisor_id)
            result = virtwho.run_service()
            assert (
                result["error"] == 0
                and result["send"] == 1
                and result["thread"] == 1
                and result["hypervisor_id"]
                == hypervisor_data[f"hypervisor_{hypervisor_id}"]
            )
            if REGISTER == "rhsm":
                assert rhsm.consumers(hypervisor_data["hypervisor_hostname"])
                rhsm.host_delete(hypervisor_data["hypervisor_hostname"])
            else:
                if hypervisor_id == "hostname":
                    assert satellite.host_id(hypervisor_data["hypervisor_hostname"])
                    assert not satellite.host_id(hypervisor_data["hypervisor_uuid"])
                    assert not satellite.host_id(hypervisor_data["hypervisor_hwuuid"])
                elif hypervisor_id == "uuid":
                    assert satellite.host_id(hypervisor_data["hypervisor_uuid"])
                    assert not satellite.host_id(hypervisor_data["hypervisor_hostname"])
                    assert not satellite.host_id(hypervisor_data["hypervisor_hwuuid"])
                else:
                    assert satellite.host_id(hypervisor_data["hypervisor_hwuuid"])
                    assert not satellite.host_id(hypervisor_data["hypervisor_hostname"])
                    assert not satellite.host_id(hypervisor_data["hypervisor_uuid"])

    @pytest.mark.tier1
    def test_filter_hosts(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the filter_hosts= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test filter_hosts option
        :id: fd3e4f83-af37-4947-aa45-297ec47ccade
        :caseimportance: High
        :tags: hypervisor,esx,tier1
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
        hypervisor_ids = ["hostname", "uuid", "hwuuid"]
        for hypervisor_id in hypervisor_ids:
            function_hypervisor.update("hypervisor_id", hypervisor_id)
            hypervisor_id_data = hypervisor_data[f"hypervisor_{hypervisor_id}"]

            function_hypervisor.update("filter_hosts", hypervisor_id_data)
            result = virtwho.run_service()
            assert (
                result["error"] == 0
                and result["send"] == 1
                and result["thread"] == 1
                and hypervisor_id_data in str(result["mappings"])
            )

    @pytest.mark.tier1
    def test_exclude_hosts(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the exclude_hosts= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test exclude_hosts option
        :id: ca2f2c5e-cb2a-4dea-9d8e-010058e31947
        :caseimportance: High
        :tags: hypervisor,esx,tier1
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
        hypervisor_ids = ["hostname", "uuid", "hwuuid"]
        for hypervisor_id in hypervisor_ids:
            function_hypervisor.update("hypervisor_id", hypervisor_id)
            hypervisor_id_data = hypervisor_data[f"hypervisor_{hypervisor_id}"]

            function_hypervisor.update("exclude_hosts", hypervisor_id_data)
            result = virtwho.run_service()
            assert (
                result["error"] == 0
                and result["send"] == 1
                and result["thread"] == 1
                and hypervisor_id_data not in str(result["mappings"])
            )

    @pytest.mark.tier1
    def test_filter_host_parents(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the filter_host_parents= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test filter_host_parents option
        :id: 8569eb02-3953-4c00-bfe6-df55fc386e90
        :caseimportance: High
        :tags: hypervisor,esx,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Run virt-who with filter_host_parents='' to get domain_id
            2. Set the hypervisor_id=hostname, run virt-who with filter_host_parents=[domain_id]
            3. Set the hypervisor_id=uuid, run virt-who with filter_host_parents=[domain_id]
            4. Set the hypervisor_id=hwuuid, run virt-who with filter_host_parents=[domain_id]

        :expectedresults:
            1. Succeeded to find the domain_id from the rhsm.log
            2. Succeeded to run virt-who, can find hostname from the mapping info in rhsm.log
            3. Succeeded to run virt-who, can find uuid from the mapping info in rhsm.log
            4. Succeeded to run virt-who, can find hwuuid from the mapping info in rhsm.log
        """
        host_hwuuid = hypervisor_data["hypervisor_hwuuid"]
        function_hypervisor.update("filter_host_parents", "")
        result = virtwho.run_service()
        domain_id = get_host_domain_id(host_hwuuid, result["log"])

        hypervisor_ids = ["hostname", "uuid", "hwuuid"]
        for hypervisor_id in hypervisor_ids:
            function_hypervisor.update("hypervisor_id", hypervisor_id)
            hypervisor_id_data = hypervisor_data[f"hypervisor_{hypervisor_id}"]
            function_hypervisor.update("filter_host_parents", domain_id)
            result = virtwho.run_service()
            assert (
                result["error"] == 0
                and result["send"] == 1
                and result["thread"] == 1
                and hypervisor_id_data in str(result["mappings"])
            )

    @pytest.mark.tier1
    def test_exclude_host_parents(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the exclude_host_parents= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test exclude_host_parents option
        :id: 6b8d2dc1-f4ea-4f82-b39d-2fc1260c949d
        :caseimportance: High
        :tags: hypervisor,esx,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Run virt-who with exclude_host_parents='' to get domain_id
            2. Set the hypervisor_id=hostname, run virt-who with filter_host_parents=[domain_id]
            3. Set the hypervisor_id=uuid, run virt-who with filter_host_parents=[domain_id]
            4. Set the hypervisor_id=hwuuid, run virt-who with filter_host_parents=[domain_id]

        :expectedresults:
            1. Succeeded to find the domain_id from the rhsm.log
            2. Succeeded to run virt-who, cannot find hostname from the mapping info in rhsm.log
            3. Succeeded to run virt-who, cannot find uuid from the mapping info in rhsm.log
            4. Succeeded to run virt-who, cannot find hwuuid from the mapping info in rhsm.log
        """
        host_hwuuid = hypervisor_data["hypervisor_hwuuid"]
        function_hypervisor.update("exclude_host_parents", "*")
        result = virtwho.run_service()
        domain_id = get_host_domain_id(host_hwuuid, result["log"])

        hypervisor_ids = ["hostname", "uuid", "hwuuid"]
        for hypervisor_id in hypervisor_ids:
            function_hypervisor.update("hypervisor_id", hypervisor_id)
            hypervisor_id_data = hypervisor_data[f"hypervisor_{hypervisor_id}"]
            function_hypervisor.update("exclude_host_parents", domain_id)
            result = virtwho.run_service()
            assert (
                result["error"] == 0
                and result["send"] == 1
                and result["thread"] == 1
                and hypervisor_id_data not in str(result["mappings"])
            )

    @pytest.mark.tier1
    def test_simplified_vim(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the simplified_vim option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test simplified_vim option
        :id: 4e0a0ab3-8426-4121-8bbd-2e39794043d8
        :caseimportance: High
        :tags: hypervisor,esx,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. run virt-who with simplified_vim=true
            2. run virt-who with simplified_vim=false
        :expectedresults:
            1. Succeed to run the virt-who
            2. Succeed to run the virt-who
        """
        function_hypervisor.update("simplified_vim", "true")
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

        function_hypervisor.update("simplified_vim", "false")
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

    @pytest.mark.tier1
    def test_fake_type(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the fake type in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test fake type
        :id: 14d3af84-92c3-4335-8bff-8a96cf211c1d
        :caseimportance: High
        :tags: hypervisor,esx,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Generate the json file by virt-who -p -d command
            2. Create the virt-who config for the fake mode testing
            3. Check the rhsm.log

        :expectedresults:
            1. Can find the json data in the specific path
            2. Succeed to run the virt-who service, can find the host_uuid and guest_uuid in the
            rhsm.log file
        """
        host_uuid = hypervisor_data["hypervisor_uuid"]
        guest_uuid = hypervisor_data["guest_uuid"]
        virtwho.run_cli(prt=True, oneshot=False)
        function_hypervisor.destroy()

        fake_config = hypervisor_create("fake", REGISTER, rhsm=True)
        fake_config.update("file", PRINT_JSON_FILE)
        fake_config.update("is_hypervisor", "True")
        result = virtwho.run_service()
        assert (
            result["error"] == 0
            and result["send"] == 1
            and result["thread"] == 1
            and host_uuid in result["log"]
            and guest_uuid in result["log"]
        )
        # Todo: Need to add the test cases for host-guest association in mapping, web

    @pytest.mark.tier1
    def test_read_only_account(
        self, virtwho, function_hypervisor, hypervisor_data, register_data
    ):
        """
        :title: virt-who: esx: check mapping info by the read only account
        :id: c13c05c0-fadb-4187-80f1-a2f52f0610db
        :caseimportance: High
        :tags: hypervisor,esx,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. set the username to the read only account for esxi
            2. run the virt-who service
        :expectedresults:

            2. Succeed to run the virt-who service, can find the host-to-guest association
            in rhsm.log
        """
        host_name = hypervisor_data["hypervisor_hostname"]
        guest_uuid = hypervisor_data["guest_uuid"]

        read_only_username = "tester@vsphere.local"
        function_hypervisor.update("username", read_only_username)

        result = virtwho.run_service()
        assert (
            result["error"] == 0
            and result["send"] == 1
            and result["thread"] == 1
            and virtwho.associate_in_mapping(
                result, register_data["default_org"], host_name, guest_uuid
            )
        )


@pytest.mark.usefixtures("function_virtwho_d_conf_clean")
@pytest.mark.usefixtures("class_debug_true")
@pytest.mark.usefixtures("class_globalconf_clean")
class TestEsxNegative:
    @pytest.mark.tier2
    def test_type(self, virtwho, function_hypervisor, esx_assertion):
        """Test the type= option in /etc/virt-who.d/test_esx.conf

        :title: virt-who: esx: test type option
        :id: abc67f6f-c79d-4458-9c69-ac788f0697a6
        :caseimportance: High
        :tags: hypervisor,esx,tier2
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
        assertion = esx_assertion["type"]
        assertion_invalid_list = list(assertion["invalid"].keys())
        for value in assertion_invalid_list:
            function_hypervisor.update("type", value)
            result = virtwho.run_service()
            assert (
                result["error"] != 0 and result["send"] == 0 and result["thread"] == 0
            )
            if "RHEL-9" in RHEL_COMPOSE:
                assert assertion["invalid"][f"{value}"] in result["error_msg"]
            else:
                assert assertion["non_rhel9"] in result["error_msg"]

        # type option is disable
        function_hypervisor.delete("type")
        result = virtwho.run_service()
        assert (
            result["error"] != 0
            and result["send"] == 0
            and result["thread"] == 1
            and assertion["disable"] in result["error_msg"]
        )

        # type option is null but another config is ok
        hypervisor_create(
            HYPERVISOR, REGISTER, SECOND_HYPERVISOR_FILE, SECOND_HYPERVISOR_SECTION
        )
        function_hypervisor.update("type", "")
        result = virtwho.run_service()
        assert result["send"] == 1 and result["thread"] == 1
        if "RHEL-8" in RHEL_COMPOSE:
            assert result["error"] == 0
        else:
            assert result["error"] == 1

    @pytest.mark.tier2
    def test_server(self, virtwho, function_hypervisor, esx_assertion):
        """Test the server= option in /etc/virt-who.d/test_esx.conf

        :title: virt-who: esx: test server option
        :id: 428aad86-947d-40f1-aac4-ddd2676ad855
        :caseimportance: High
        :tags: hypervisor,esx,tier2
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
        assertion = esx_assertion["server"]
        assertion_invalid_list = list(assertion["invalid"].keys())
        for value in assertion_invalid_list:
            function_hypervisor.update("server", value)
            result = virtwho.run_service()
            assert (
                result["error"] != 0
                and result["send"] == 0
                and msg_search(result["error_msg"], assertion["invalid"][f"{value}"])
            )

        # server option is disable
        function_hypervisor.delete("server")
        result = virtwho.run_service()
        assert (
            result["error"] != 0
            and result["send"] == 0
            and result["thread"] == 0
            and assertion["disable"] in result["error_msg"]
        )

        # server option is disable but another config is ok
        hypervisor_create(
            HYPERVISOR, REGISTER, SECOND_HYPERVISOR_FILE, SECOND_HYPERVISOR_SECTION
        )
        result = virtwho.run_service()
        assert (
            result["error"] != 0
            and result["send"] == 1
            and result["thread"] == 1
            and assertion["disable_multi_configs"] in result["error_msg"]
        )

        # server option is null but another config is ok
        function_hypervisor.update("server", "")
        result = virtwho.run_service()
        assert (
            result["error"] != 0
            and result["send"] == 1
            and result["thread"] == 1
            and assertion["null_multi_configs"] in result["error_msg"]
        )

    @pytest.mark.tier2
    def test_username(self, function_hypervisor, virtwho, esx_assertion):
        """Test the username= option in /etc/virt-who.d/test_esx.conf

        :title: virt-who: esx: test username option
        :id: 98359dec-7e49-4037-8399-8224e054c5b4
        :caseimportance: High
        :tags: hypervisor,esx,tier2
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
        assertion = esx_assertion["username"]
        assertion_invalid_list = list(assertion["invalid"].keys())
        for value in assertion_invalid_list:
            function_hypervisor.update("username", value)
            result = virtwho.run_service()
            assert (
                result["error"] != 0
                and result["send"] == 0
                and result["thread"] == 1
                and assertion["invalid"][f"{value}"] in result["error_msg"]
            )

        # username option is disable
        function_hypervisor.delete("username")
        result = virtwho.run_service()
        assert (
            result["error"] != 0
            and result["send"] == 0
            and result["thread"] == 0
            and assertion["disable"] in result["error_msg"]
        )

        # username option is disable but another config is ok
        hypervisor_create(
            HYPERVISOR, REGISTER, SECOND_HYPERVISOR_FILE, SECOND_HYPERVISOR_SECTION
        )
        result = virtwho.run_service()
        assert (
            result["error"] != 0
            and result["send"] == 1
            and result["thread"] == 1
            and assertion["disable_multi_configs"] in result["error_msg"]
        )

    @pytest.mark.tier2
    def test_password(self, virtwho, function_hypervisor, esx_assertion):
        """Test the password= option in /etc/virt-who.d/test_esx.conf

        :title: virt-who: esx: test password option
        :id: 19f7305b-0ac5-4ac8-8d39-d32168e5b634
        :caseimportance: High
        :tags: hypervisor,esx,tier2
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
        assertion = esx_assertion["password"]
        assertion_invalid_list = list(assertion["invalid"].keys())
        for value in assertion_invalid_list:
            function_hypervisor.update("password", value)
            result = virtwho.run_service()
            assert (
                result["error"] != 0
                and result["send"] == 0
                and result["thread"] == 1
                and assertion["invalid"][f"{value}"] in result["error_msg"]
            )

        # password option is disable
        function_hypervisor.delete("password")
        result = virtwho.run_service()
        assert (
            result["error"] != 0
            and result["send"] == 0
            and result["thread"] == 0
            and assertion["disable"] in result["error_msg"]
        )

        # password option is disable but another config is ok
        hypervisor_create(
            HYPERVISOR, REGISTER, SECOND_HYPERVISOR_FILE, SECOND_HYPERVISOR_SECTION
        )
        result = virtwho.run_service()
        assert (
            result["error"] != 0
            and result["send"] == 1
            and result["thread"] == 1
            and assertion["disable_multi_configs"] in result["error_msg"]
        )

    @pytest.mark.tier2
    def test_encrypted_password(
        self, virtwho, function_hypervisor, esx_assertion, hypervisor_data, ssh_host
    ):
        """Test the encrypted_password= option in /etc/virt-who.d/test_esx.conf

        :title: virt-who: esx: test encrypted_password option (negative)
        :id: 5014c314-8d57-44ce-820b-6de88810044e
        :caseimportance: High
        :tags: hypervisor,esx,tier2
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
        function_hypervisor.delete("password")
        assertion = esx_assertion["encrypted_password"]
        assertion_invalid_list = list(assertion["invalid"].keys())
        for value in assertion_invalid_list:
            function_hypervisor.update("encrypted_password", value)
            result = virtwho.run_service()
            assert (
                result["error"] != 0
                and result["send"] == 0
                and result["thread"] == 0
                and assertion["invalid"][f"{value}"] in result["warning_msg"]
            )

        # encrypted_password option is valid but another config is ok
        hypervisor_create(
            HYPERVISOR, REGISTER, SECOND_HYPERVISOR_FILE, SECOND_HYPERVISOR_SECTION
        )
        result = virtwho.run_service()
        assert (
            result["error"] != 0
            and result["send"] == 1
            and result["thread"] == 1
            and assertion["valid_multi_configs"] in result["warning_msg"]
        )

    @pytest.mark.tier2
    def test_filter_hosts(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the filter_hosts= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test filter_hosts negative option
        :id: a32bacac-77e8-46a3-a2ca-b1f4691acb70
        :caseimportance: High
        :tags: hypervisor,esx,tier2
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
        hypervisor_ids = ["hostname", "uuid", "hwuuid"]
        for hypervisor_id in hypervisor_ids:
            function_hypervisor.update("hypervisor_id", hypervisor_id)
            hypervisor_id_data = hypervisor_data[f"hypervisor_{hypervisor_id}"]
            wildcard = hypervisor_id_data[:3] + "*" + hypervisor_id_data[4:]

            for filter_hosts in ["*", wildcard]:
                function_hypervisor.update("filter_hosts", filter_hosts)
                result = virtwho.run_service()
                assert (
                    result["error"] == 0
                    and result["send"] == 1
                    and result["thread"] == 1
                    and hypervisor_id_data in str(result["mappings"])
                )

            function_hypervisor.delete("hypervisor_id")

        hostname = hypervisor_data["hypervisor_hostname"]
        function_hypervisor.update("hypervisor_id", "hostname")

        # config filter_hosts with null option
        for filter_hosts in ["", "''", '""']:
            function_hypervisor.update("filter_hosts", filter_hosts)
            result = virtwho.run_service()
            assert (
                result["error"] == 0
                and result["send"] == 1
                and result["thread"] == 1
                and hostname not in str(result["mappings"])
            )

        # config filter_hosts with 'hostname' and "hostname"
        for filter_hosts in [f"'{hostname}'", f'"{hostname}"']:
            function_hypervisor.update("filter_hosts", filter_hosts)
            result = virtwho.run_service()
            assert (
                result["error"] == 0
                and result["send"] == 1
                and result["thread"] == 1
                and hostname in str(result["mappings"])
            )

    @pytest.mark.tier2
    def test_exclude_host(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the exclude_hosts= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test exclude_hosts negative option
        :id: fc8cd6bb-3e14-4929-8240-134d13995bfa
        :caseimportance: High
        :tags: hypervisor,esx,tier2
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
        hypervisor_ids = ["hostname", "uuid", "hwuuid"]
        for hypervisor_id in hypervisor_ids:
            function_hypervisor.update("hypervisor_id", hypervisor_id)
            hypervisor_id_data = hypervisor_data[f"hypervisor_{hypervisor_id}"]
            wildcard = hypervisor_id_data[:3] + "*" + hypervisor_id_data[4:]

            for exclude_hosts in ["*", wildcard]:
                function_hypervisor.update("exclude_hosts", exclude_hosts)
                result = virtwho.run_service()
                assert (
                    result["error"] == 0
                    and result["send"] == 1
                    and result["thread"] == 1
                    and hypervisor_id_data not in str(result["mappings"])
                )

        hostname = hypervisor_data["hypervisor_hostname"]
        function_hypervisor.update("hypervisor_id", "hostname")

        for exclude_hosts in ["", "''", '""']:
            function_hypervisor.update("exclude_hosts", exclude_hosts)
            result = virtwho.run_service()
            assert (
                result["error"] == 0
                and result["send"] == 1
                and result["thread"] == 1
                and hostname in str(result["mappings"])
            )

        for exclude_hosts in [f"'{hostname}'", f'"{hostname}"']:
            function_hypervisor.update("exclude_hosts", exclude_hosts)
            result = virtwho.run_service()
            assert (
                result["error"] == 0
                and result["send"] == 1
                and result["thread"] == 1
                and hostname not in str(result["mappings"])
            )

    @pytest.mark.tier2
    def test_filter_exclude_mix(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the filter_hosts= and exclude_hosts= mix option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test filter_hosts and exclude_hosts related mix function
        :id: da952c46-6983-4c60-8b3d-c5704643ea2a
        :caseimportance: High
        :tags: hypervisor,esx,tier1
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
        function_hypervisor.update("hypervisor_id", "uuid")
        hypervisor_uuid = hypervisor_data["hypervisor_uuid"]

        # run virt-who with filter_hosts=[host_uuid] and exclude_hosts=[host_uuid]
        function_hypervisor.update("filter_hosts", hypervisor_uuid)
        function_hypervisor.update("exclude_hosts", hypervisor_uuid)
        result = virtwho.run_service()
        assert (
            result["error"] == 0
            and result["send"] == 1
            and result["thread"] == 1
            and hypervisor_uuid not in str(result["mappings"])
        )

        # run virt-who with filter_hosts=* and exclude_hosts=[host_uuid]
        function_hypervisor.update("filter_hosts", "*")
        function_hypervisor.update("exclude_hosts", hypervisor_uuid)
        result = virtwho.run_service()
        assert (
            result["error"] == 0
            and result["send"] == 1
            and result["thread"] == 1
            and hypervisor_uuid not in str(result["mappings"])
        )

        # run virt-who with exclude_hosts= and filter_hosts=[host_uuid]
        function_hypervisor.update("filter_hosts", hypervisor_uuid)
        function_hypervisor.update("exclude_hosts", "")
        result = virtwho.run_service()
        assert (
            result["error"] == 0
            and result["send"] == 1
            and result["thread"] == 1
            and hypervisor_uuid in str(result["mappings"])
        )

    @pytest.mark.tier2
    def test_filter_host_parents(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the filter_host_parents option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test filter_host_parents negative function
        :id: c16e70f8-a343-4a66-b206-644011688a34
        :caseimportance: High
        :tags: hypervisor,esx,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Run virt-who with filter_host_parents='' to get domain_id
            2. Set hypervisor_id=hostname.
            3. Configure filter_host_parents='', run the virt-who service.
            4. Configure filter_host_parents='*', run the virt-who service.
            5. Configure filter_hosts=wildcard, run the virt-who service.
            6. Set hypervisor_id=uuid and hwuuid, run the above steps.
        :expectedresults:
            1. Succeeded to find the domain_id from the rhsm.log
            3. Succeeded to run the virt-who, cannot find hostname in the log message
            4. Succeeded to run the virt-who, can find hostname in the log message
            5. Succeeded to run the virt-who, can find hostname in the log message
            6. The same as above
        """
        function_hypervisor.update("filter_host_parents", "")
        result = virtwho.run_service()
        domain_id = get_host_domain_id(
            hypervisor_data["hypervisor_hwuuid"], result["log"]
        )

        hypervisor_ids = ["hostname", "uuid", "hwuuid"]
        for hypervisor_id in hypervisor_ids:
            function_hypervisor.update("hypervisor_id", hypervisor_id)
            hypervisor_id_data = hypervisor_data[f"hypervisor_{hypervisor_id}"]
            wildcard = domain_id[:3] + "*" + domain_id[4:]

            for filter_host_parents in ["", "*", wildcard]:
                function_hypervisor.update("filter_host_parents", filter_host_parents)
                result = virtwho.run_service()
                if filter_host_parents == "":
                    assert (
                        result["error"] == 0
                        and result["send"] == 1
                        and result["thread"] == 1
                        and hypervisor_id_data not in str(result["mappings"])
                    )
                else:
                    assert (
                        result["error"] == 0
                        and result["send"] == 1
                        and result["thread"] == 1
                        and hypervisor_id_data in str(result["mappings"])
                    )

            function_hypervisor.delete("hypervisor_id")

    @pytest.mark.tier2
    def test_exclude_host_parents(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the exclude_host_parents option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test exclude_host_parents negative function
        :id: fd3534a1-4c79-4c3d-bdc5-b795919dea0a
        :caseimportance: High
        :tags: hypervisor,esx,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Run virt-who with exclude_host_parents='*' to get domain_id
            2. Set hypervisor_id=hostname.
            3. Configure exclude_host_parents='', run the virt-who service.
            4. Configure exclude_host_parents='*', run the virt-who service.
            5. Configure exclude_host_parents=wildcard, run the virt-who service.
            6. Set hypervisor_id=uuid and hwuuid, run the above steps.
        :expectedresults:
            1. Succeeded to find the domain_id from the rhsm.log
            3. Succeeded to run the virt-who, can find hostname in the log message
            4. Succeeded to run the virt-who, cannot find hostname in the log message
            5. Succeeded to run the virt-who, cannot find hostname in the log message
            6. The same as above

        """
        function_hypervisor.update("exclude_host_parents", "*")
        result = virtwho.run_service()
        domain_id = get_host_domain_id(
            hypervisor_data["hypervisor_hwuuid"], result["log"]
        )

        hypervisor_ids = ["hostname", "uuid", "hwuuid"]
        for hypervisor_id in hypervisor_ids:
            function_hypervisor.update("hypervisor_id", hypervisor_id)
            hypervisor_id_data = hypervisor_data[f"hypervisor_{hypervisor_id}"]
            wildcard = domain_id[:3] + "*" + domain_id[4:]

            for exclude_host_parents in ["", "*", wildcard]:
                function_hypervisor.update("exclude_host_parents", exclude_host_parents)
                result = virtwho.run_service()
                if exclude_host_parents == "":
                    assert (
                        result["error"] == 0
                        and result["send"] == 1
                        and result["thread"] == 1
                        and hypervisor_id_data in str(result["mappings"])
                    )
                else:
                    assert (
                        result["error"] == 0
                        and result["send"] == 1
                        and result["thread"] == 1
                        and hypervisor_id_data not in str(result["mappings"])
                    )

            function_hypervisor.delete("hypervisor_id")

    @pytest.mark.tier2
    def test_unsupported_option(
        self, virtwho, function_hypervisor, hypervisor_data, register_data
    ):
        """
        :title: virt-who: esx: test unsupported options in /etc/virt-who.d/ dir
        :id: ffd1fe9f-8c85-43ab-b2ae-16e824b5e880
        :caseimportance: High
        :tags: hypervisor,esx,tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Set up an unsupported option like 'xxxxx' option in the config file
            2. Run the virt-who service

        :expectedresults:

            2. Succeed to run the vir-tho, can find the ignore message in rhsm.log
        """
        unsupported_option = "xxxxx"
        function_hypervisor.update(unsupported_option, "aaaa")
        result = virtwho.run_service()
        assert (
            result["error"] == 0
            and result["send"] == 1
            and result["thread"] == 1
            and f'Ignoring unknown configuration option "{unsupported_option}"'
            in result["log"]
        )

    @pytest.mark.tier2
    def test_extension_file_name(
        self,
        virtwho,
        function_hypervisor,
        hypervisor_data,
        register_data,
        ssh_host,
        esx_assertion,
    ):
        """
        :title: virt-who: esx: test extension file name in /etc/virt-who.d/ dir
        :id: 3e5ca411-147b-4ac6-87b0-fe2720ff2e17
        :caseimportance: High
        :tags: hypervisor,esx,tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Create virt-who config file with the expected file name
            2. Rename the config file with the invalid extension file name like esx.conf.txt
            3. Run the virt-who service

        :expectedresults:
            1. Succeed to run the virt-who
            3. Failed to run the virt-who, can fin the expected error and warning messages
            in rhsm.log
        """
        invalid_file_name = esx_assertion["extension_file_name"]["file_name"]
        cmd = f"mv {function_hypervisor.remote_file} {invalid_file_name}"
        ssh_host.runcmd(cmd)

        warning_msg = esx_assertion["extension_file_name"]["warining_msg"]
        error_msg = esx_assertion["extension_file_name"]["error_msg"]
        result = virtwho.run_service()
        if result["error"]:
            assert (
                result["send"] == 0
                and result["thread"] == 1
                and error_msg in result["error_msg"]
                and warning_msg in result["warning_msg"]
            )
        else:
            # Now we also have the libvirt local mode on host, so just assert the warning msg
            assert warning_msg in result["warning_msg"]

    @pytest.mark.tier2
    def test_quoted_options(self, virtwho, function_hypervisor, ssh_host):
        """
        :title: virt-who: esx: test the quoted options in /etc/virt-who.d/ dir
        :id: 75dc69a9-e025-401c-bf84-8dea86263e77
        :caseimportance: High
        :tags: hypervisor,esx,tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Create the expected config file in /etc/virt-who.d dir
            2. Run virt-who when all the options enabled with single quotes such as type='esx'
            3. Rn virt-who when all the options enabled with double quotes such as type="esx"

        :expectedresults:
            2. Succeed to run the virt-who without any error messages
            3. Succeed to run the virt-who without any error messages
        """
        # run virt-who when all the options enabled with single quotes
        cmd = rf"""sed -i "s|=\(.*\)|='\1'|g" {function_hypervisor.remote_file}"""
        ssh_host.runcmd(cmd)
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

        # run virt-who when all the options enabled with double quotes
        cmd = rf"""sed -i "s|'|\"|g" {function_hypervisor.remote_file}"""
        ssh_host.runcmd(cmd)
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

    @pytest.mark.tier2
    def test_redundant_options(
        self, virtwho, function_hypervisor, ssh_host, hypervisor_data, esx_assertion
    ):
        """
        :title: virt-who: esx: test the redundant options in /etc/virt-who.d/ dir
        :id: cba7b507-f490-405b-85b7-ca448da901f2
        :caseimportance: High
        :tags: hypervisor,esx,tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Create the expected config file in /etc/virt-who.d dir, default to add the
            hypervisor_id=hostname
            2. Add another hypervisor_id=uuid, run the virt-who service
            3. Add another hypervisor_id=xxx, run the virt-who service

        :expectedresults:
            2. Succeed to run the virt-who without any error messages, can find the related
            warning message and "hypervisorId": "{host_uuid}" in rhsm.log
            3. Failed to run the virt-who, can find the related warning message in rhsm.log
        """
        host_name = hypervisor_data["hypervisor_hostname"]
        host_uuid = hypervisor_data["hypervisor_uuid"]
        option = "hypervisor_id"
        warning_msg = f"option '{option}' in section '{function_hypervisor.section}' already exists"

        # run virt-who with hypervisor_id=uuid and hypervisor_id=hostname together
        cmd = f'echo -e "{option}=uuid" >> {function_hypervisor.remote_file}'
        ssh_host.runcmd(cmd)
        result = virtwho.run_service()
        assert (
            result["error"] == 0
            and result["send"] == 1
            and result["thread"] == 1
            and f'"hypervisorId": "{host_uuid}"' in result["log"]
            and f'"hypervisorId": "{host_name}"' not in result["log"]
        )
        if "RHEL-8" in RHEL_COMPOSE:
            assert warning_msg in result["warning_msg"]

        # add another hypervisor_id=xxx
        invalid_value = "xxx"
        cmd = f'echo -e "{option}={invalid_value}" >> {function_hypervisor.remote_file}'
        ssh_host.runcmd(cmd)
        result = virtwho.run_service()
        assert (
            result["error"] != 0
            and result["send"] == 0
            and result["thread"] == 0
            and esx_assertion["redundant_options"]["error_msg"] in result["error_msg"]
        )
        if "RHEL-8" in RHEL_COMPOSE:
            assert warning_msg in result["warning_msg"]

    @pytest.mark.tier2
    def test_commented_line_with_tab_space(
        self, virtwho, function_hypervisor, ssh_host
    ):
        """
        :title: virt-who: esx: test commented line with tab space virt-who config file
        :id: d2444fd4-0a2c-4a08-a873-cb9d39e6b98b
        :caseimportance: High
        :tags: hypervisor,esx,tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Create the expected config file in /etc/virt-who.d dir
            2. Add another invalid line with tab space, run the virt-who service
            3. Comment the line to ignore it in the config file, run the virt-who service

        :expectedresults:
            2. Failed to run the virt-who, can find the related Error message in rhsm.log
            3. Succeed to run the virt-who without any error messages.
        """
        # add useless line with tab spaces after type=
        error_msg = "virt-who can't be started: no valid configuration found"

        cmd = f"sed -i '/^type=/a \\\txxx=xxx' {function_hypervisor.remote_file}"
        ssh_host.runcmd(cmd)
        result = virtwho.run_service()

        assert (
            result["error"] != 0
            and result["send"] == 0
            and result["thread"] == 0
            and error_msg in result["error_msg"]
        )

        # comment out the useless line
        cmd = f'sed -i "s/xxx/#xxx/" {function_hypervisor.remote_file}'
        ssh_host.runcmd(cmd)
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

    @pytest.mark.tier2
    @pytest.mark.notRHSM
    def test_hypervisors_fqdn(
        self, virtwho, function_hypervisor, hypervisor_data, satellite, ssh_host
    ):
        """
        :title: virt-who: esx: test the hypervisors fqdn
        :id: ef3ecbc5-2433-44ae-9517-39dbe9590726
        :caseimportance: High
        :tags: hypervisor,esx,tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Create fake json file by the default configuration
            2. Run virt-who with the fake config
            3. Use hammer command to check hypervisor's fqdn
            4. Run virt-who with the new hypervisor's fqdn
            5. Use hammer command to check the new hypervisor's fqdn

        :expectedresults:
            1. Created the fake json file in /root/print.json
            2. Succeed to run the virt-who service
            3. Can find the hypervisor's fqdn by the hammer command
            5. Can find the new hypervisor's fqdn by the hammer command, cannot find the previous
            hypervisor' fqdn
        """
        host_name = hypervisor_data["hypervisor_hostname"]

        # create fake json file
        virtwho.run_cli(prt=True)

        # run virt-who with fake conf
        hypervisor_create(
            mode="fake", register_type="satellite", config_name=FAKE_CONFIG_FILE
        )
        result = virtwho.run_cli(config=FAKE_CONFIG_FILE)
        assert result["error"] == 0 and result["send"] == 1

        # use hammer command to check hypervisor's FQDN
        hypervisor_fqdn = "virt-who-" + host_name
        assert satellite.host_id(hypervisor_fqdn)

        # run virt-who with the new hypervisor's FQDN
        new_host_name = (
            "new" + str(random.randint(1, 10000)) + ".rhts.eng.pek2.redhat.com"
        )

        cmd = f'sed -i "s|{host_name}|{new_host_name}|g" {PRINT_JSON_FILE}'
        ssh_host.runcmd(cmd)

        result = virtwho.run_cli(config=FAKE_CONFIG_FILE)
        assert result["error"] == 0 and result["send"] == 1

        new_hypervisor_fqdn = "virt-who-" + new_host_name
        assert satellite.host_id(new_hypervisor_fqdn)
        assert not satellite.host_id(hypervisor_fqdn)

    @pytest.mark.tier2
    def test_trigger_event_with_different_interval(
        self, virtwho, function_hypervisor, hypervisor_data, register_data, globalconf
    ):
        """
        :title: virt-who: esx: trigger event with different interval
        :id: a1972ea5-3c4b-455e-8690-c9f69fa88972
        :caseimportance: High
        :tags: hypervisor,esx,tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Configure the interval with 60 in /etc/virtwho.conf
            2. Suspend the guest and run the virt-who service
            3. Configure the interval with 120 in /etc/virtwho.conf
            4. Resume the guest and run the virt-who service

        :expectedresults:
            2. Succeed to run the virt-who, and  virt-who starting infinite loop with
            60 seconds interval
            4. Succeed to run the virt-who, and  virt-who starting infinite loop with
            120 seconds interval
        """
        esx = PowerCLI(
            server=hypervisor_data["hypervisor_server"],
            admin_user=hypervisor_data["hypervisor_username"],
            admin_passwd=hypervisor_data["hypervisor_password"],
            client_server=hypervisor_data["ssh_ip"],
            client_user=hypervisor_data["ssh_username"],
            client_passwd=hypervisor_data["ssh_password"],
        )

        try:
            # run virt-who with event(guest_suspend) for interval 60
            globalconf.update("global", "interval", "60")
            virtwho.run_service()
            esx.guest_suspend(hypervisor_data["guest_name"])
            rhsm_log = virtwho.rhsm_log_get(80)
            result = virtwho.analyzer(rhsm_log)
            assert (
                result["error"] == 0
                and result["send"] == 2
                and result["thread"] == 1
                and result["loop"] in [60, 61]
            )

        finally:
            # run virt-who with event(guest_resume) for interval 120
            globalconf.update("global", "interval", "120")
            virtwho.run_service()
            esx.guest_resume(hypervisor_data["guest_name"])
            rhsm_log = virtwho.rhsm_log_get(150)
            result = virtwho.analyzer(rhsm_log)
            assert (
                result["error"] == 0
                and result["send"] == 2
                and result["thread"] == 1
                and result["loop"] in [120, 121]
            )

    @pytest.mark.tier2
    def test_hostname_without_domain(
        self, virtwho, function_hypervisor, hypervisor_data, satellite, rhsm
    ):
        """
        :title: virt-who: esx: Run virt-who for hostname without domain name
        :id: 5a100319-b68e-44db-a3ac-172f9ae90bec
        :caseimportance: High
        :tags: hypervisor,esx,tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Change the hostname to the name without domain
            2. Run virt-who with the new hostname
            3. Change back the hostname

        :expectedresults:
            2. Virt-who works fine without any error messages

        """
        hostname = hypervisor_data["hypervisor_hostname"]
        hostname_non_domain = hostname.split(".")[0]

        esx = PowerCLI(
            server=hypervisor_data["hypervisor_server"],
            admin_user=hypervisor_data["hypervisor_username"],
            admin_passwd=hypervisor_data["hypervisor_password"],
            client_server=hypervisor_data["ssh_ip"],
            client_user=hypervisor_data["ssh_username"],
            client_passwd=hypervisor_data["ssh_password"],
        )
        try:
            # change the hostname to non domain hostname
            esx.host_name_set(hypervisor_data["host_ip"], hostname_non_domain)

            result = virtwho.run_service()
            assert (
                result["error"] == 0
                and result["send"] == 1
                and result["thread"] == 1
                and hostname_non_domain in result["log"]
                and hostname not in result["log"]
            )
        finally:
            # change back the hostname
            esx.host_name_set(hypervisor_data["host_ip"], hostname)

    @pytest.mark.tier2
    def test_cluster_name_with_special_char(
        self, virtwho, function_hypervisor, hypervisor_data, satellite, rhsm
    ):
        """
        :title: virt-who: esx: Run virt-who for cluster name with special char
        :id: 4de43160-1db8-4516-a2e2-1955f6f4f612
        :caseimportance: High
        :tags: hypervisor,esx,tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Change the vcenter cluster name to: virtwho/test
            2. Run virt-who service with the new cluster name
            3. Change back the cluster name

        :expectedresults:
            2. Virt-who works fine without any error messages

        """
        host_name = hypervisor_data["hypervisor_hostname"]
        host_ip = hypervisor_data["host_ip"]

        cluster_name = hypervisor_data["cluster"]
        new_cluster_name = "virtwho/test-" + "".join(random.sample(string.digits, 6))

        esx = PowerCLI(
            server=hypervisor_data["hypervisor_server"],
            admin_user=hypervisor_data["hypervisor_username"],
            admin_passwd=hypervisor_data["hypervisor_password"],
            client_server=hypervisor_data["ssh_ip"],
            client_user=hypervisor_data["ssh_username"],
            client_passwd=hypervisor_data["ssh_password"],
        )

        try:
            # change the vcenter cluster name to: virtwho/test
            esx.cluster_name_set(host_ip, cluster_name, new_cluster_name)

            # run virt-who service with the new cluster name
            result = virtwho.run_service()
            assert (
                result["error"] == 0
                and result["send"] == 1
                and result["thread"] == 1
                and f'"hypervisor.cluster": "{new_cluster_name}"' in result["log"]
            )

            # check the hyperivsor facts
            if REGISTER == "satellite":
                host_id = satellite.host_id(host_name)
                hypervisor_facts = satellite.facts_get(host_id)
            else:
                output = rhsm.info(host_name)
                hypervisor_facts = output["facts"]["hypervisor.cluster"]
            assert new_cluster_name in hypervisor_facts

        finally:
            # change back the vcenter cluster name
            esx.cluster_name_set(host_ip, new_cluster_name, cluster_name)

    @pytest.mark.tier2
    @pytest.mark.notStage
    def test_post_large_json_to_rhsm(self, register_data, ssh_host):
        """
        :title: virt-who: esx: post large json data to satellite server
        :id: 8b14bb1f-7b92-483f-af35-7ec97a621436
        :caseimportance: High
        :tags: hypervisor,esx,tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Create json data with 100 hypervisors, every hypervisor has 30 guests
            2. Post the json data to satellite

        :expectedresults:
            2. Succeeded to post 100 hypervisors and 3000 guests to satellite

        """
        # create json data
        local_file = os.path.join(TEMP_DIR, "test.json")
        json_file = "/root/test.json"
        json_data = json_data_create(100, 30)
        with open(local_file, "w") as f:
            json.dump(json_data, f)
        ssh_host.put_file(local_file, json_file)

        # post json data
        curl_header = (
            '-H "accept:application/json,version=2" -H "content-type:application/json"'
        )
        curl_cert = "--cert /etc/pki/consumer/cert.pem --key /etc/pki/consumer/key.pem"
        curl_json = f'-d @"{json_file}"'
        curl_host = f"https://{register_data['server']}/rhsm/hypervisors"
        cmd = f"curl -X POST -s -k {curl_header} {curl_cert} {curl_json} {curl_host}"

        ret, output = ssh_host.runcmd(cmd)
        if ret == 0 and "error" not in output:
            logger.info(
                "Succeeded to post 100 hypervisors and 3000 guests to satellite"
            )
        else:
            logger.warning("Failed to post json to satellite")
            logger.warning(output)


def json_data_create(hypervisors_num, guests_num):
    """
    Generate the json date to performance testing
    :param hypervisors: number of hypervisors
    :param guests: number of guests for each hypervisor
    :return: json data
    """
    virtwho = {}
    for i in range(hypervisors_num):
        guest_list = []
        for c in range(guests_num):
            guest_list.append(
                {
                    "guestId": str(uuid.uuid4()),
                    "state": 1,
                    "attributes": {"active": 1, "virtWhoType": "esx"},
                }
            )
        virtwho[str(uuid.uuid4()).replace("-", ".")] = guest_list
    return virtwho
