"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""
import pytest
import time
import os

from virtwho import REGISTER
from virtwho import RHEL_COMPOSE
from virtwho import HYPERVISOR
from virtwho import PRINT_JSON_FILE
from virtwho import SECOND_HYPERVISOR_FILE
from virtwho import SECOND_HYPERVISOR_SECTION


from virtwho.base import encrypt_password, is_host_responsive
from virtwho.configure import hypervisor_create

from hypervisor.virt.hyperv.hypervcli import HypervCLI

@pytest.mark.usefixtures("function_virtwho_d_conf_clean")
@pytest.mark.usefixtures("class_debug_true")
@pytest.mark.usefixtures("class_globalconf_clean")
class TestHypervPositive:
    @pytest.mark.tier1
    def test_encrypted_password(
        self, virtwho, function_hypervisor, hypervisor_data, ssh_host
    ):
        """Test the encrypted_password= option in /etc/virt-who.d/test_hyperv.conf

        :title: virt-who: hyperv: test encrypted_password option
        :id: f6f6523f-28f7-4cf7-8282-5820383c68f9
        :caseimportance: High
        :tags: hypervisor,hyperv,tier1
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
    def test_hypervisor_id(
        self, virtwho, function_hypervisor, hypervisor_data, globalconf, rhsm, satellite
    ):
        """Test the hypervisor_id= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: hyperv: test hypervisor_id function
        :id: 49349a44-18c1-45c8-8edf-758a4f95109d
        :caseimportance: High
        :tags: hypervisor,hyperv,tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. clean all virt-who global configurations
            2. run virt-who with hypervisor_id=uuid
            3. run virt-who with hypervisor_id=hostname

        :expectedresults:

            hypervisor id shows uuid/hostname in mapping as the setting.
        """
        hypervisor_ids = ["hostname", "uuid"]
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
                elif hypervisor_id == "uuid":
                    assert satellite.host_id(hypervisor_data["hypervisor_uuid"])
                    assert not satellite.host_id(hypervisor_data["hypervisor_hostname"])

    @pytest.mark.tier1
    def test_filter_hosts(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the filter_hosts= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: hyperv: test filter_hosts option
        :id: 45bd062a-96a9-44cf-ac00-4c108a4d3351
        :caseimportance: High
        :tags: hypervisor,hyperv,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Set hypervisor_id=hostname.
            2. Configure filter_hosts={hostname}, run the virt-who service.
            3. Configure filter_hosts={host_uuid}, run the virt-who service.
        :expectedresults:
            2. Succeeded to run the virt-who, can find hostname in the log message
            3. Succeeded to run the virt-who, can find host_uuid in the log message
        """
        hypervisor_ids = ["hostname", "uuid"]
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

        :title: virt-who: hyperv: test exclude_hosts option
        :id: 41677d4c-2bef-4e6d-8e48-55d1d6f7ae14
        :caseimportance: High
        :tags: hypervisor,hyperv,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Set hypervisor_id=hostname.
            2. Configure exclude_hosts={hostname}, run the virt-who service.
            3. Configure exclude_hosts={host_uuid}, run the virt-who service.
        :expectedresults:
            2. Succeeded to run the virt-who, cannot find hostname in the log message
            3. Succeeded to run the virt-who, cannot find host_uuid in the log message
        """
        hypervisor_ids = ["hostname", "uuid"]
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
    def test_fake_type(
        self, virtwho, function_hypervisor, hypervisor_data, function_host_register
    ):
        """Test the fake type in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: hyperv: test fake type
        :id: a2c30d57-4eae-451e-b131-2547f046463c
        :caseimportance: High
        :tags: hypervisor,hyperv,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Generate the json file by virt-who -p -d command
            2. Create the virt-who config for the fake mode testing
            3. Check the rhsm.log

        :expectedresults:
            1. Can find the json data in the specific path
            2. Succeed to run the virt-who service, can find the host_uuid and
                guest_uuid in the rhsm.log file
        """
        host_uuid = hypervisor_data["hypervisor_uuid"]
        guest_uuid = hypervisor_data["guest_uuid"]
        function_hypervisor.update("hypervisor_id", "uuid")
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
        # Todo: Need to add the test cases for host-guest association in mapping, web and the test
        #  cases for the vdc pool's subscription.


@pytest.mark.usefixtures("function_virtwho_d_conf_clean")
@pytest.mark.usefixtures("class_debug_true")
@pytest.mark.usefixtures("class_globalconf_clean")
class TestHypervNegative:
    @pytest.mark.tier2
    def test_type(self, virtwho, function_hypervisor, hyperv_assertion):
        """Test the type= option in /etc/virt-who.d/test_hyperv.conf

        :title: virt-who: hyperv: test type option
        :id: c51a3bcc-bca7-4b45-a55a-8230bb25d7f0
        :caseimportance: High
        :tags: hypervisor,hyperv,tier2
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
        assertion = hyperv_assertion["type"]
        assertion_invalid_list = list(assertion["invalid"].keys())
        for value in assertion_invalid_list:
            function_hypervisor.update("type", value)
            result = virtwho.run_service()
            assert (
                result["error"] is not 0
                and result["send"] == 0
                and result["thread"] == 0
            )
            if "RHEL-9" in RHEL_COMPOSE:
                assert assertion["invalid"][f"{value}"] in result["error_msg"]
            else:
                assert assertion["non_rhel9"] in result["error_msg"]

        # type option is disable
        function_hypervisor.delete("type")
        result = virtwho.run_service()
        assert (
            result["error"] is not 0
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
        if "RHEL-9" in RHEL_COMPOSE:
            assert result["error"] == 1
        else:
            assert result["error"] == 0

    @pytest.mark.tier2
    def test_server(self, virtwho, function_hypervisor, hyperv_assertion):
        """Test the server= option in /etc/virt-who.d/test_hyperv.conf

        :title: virt-who: hyperv: test server option
        :id: a31efe61-9368-470e-836a-bf4c59af1694
        :caseimportance: High
        :tags: hypervisor,hyperv,tier2
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
        assertion = hyperv_assertion["server"]
        assertion_invalid_list = list(assertion["invalid"].keys())
        for value in assertion_invalid_list:
            function_hypervisor.update("server", value)
            result = virtwho.run_service()
            assert (
                result["error"] is not 0
                and result["send"] == 0
                and assertion["invalid"][f"{value}"] in result["error_msg"]
            )

        # server option is disable
        function_hypervisor.delete("server")
        result = virtwho.run_service()
        assert (
            result["error"] is not 0
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
            result["error"] is not 0
            and result["send"] == 1
            and result["thread"] == 1
            and assertion["disable_multi_configs"] in result["error_msg"]
        )

        # server option is null but another config is ok
        function_hypervisor.update("server", "")
        result = virtwho.run_service()
        assert (
            result["error"] is not 0
            and result["send"] == 1
            and result["thread"] == 1
            and assertion["null_multi_configs"] in result["error_msg"]
        )

    @pytest.mark.tier2
    def test_username(self, function_hypervisor, virtwho, hyperv_assertion):
        """Test the username= option in /etc/virt-who.d/test_hyperv.conf

        :title: virt-who: hyperv: test username option
        :id: ea6c1a97-575d-4b8b-9100-bfd90ab5f26f
        :caseimportance: High
        :tags: hypervisor,hyperv,tier2
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
        assertion = hyperv_assertion["username"]
        assertion_invalid_list = list(assertion["invalid"].keys())
        for value in assertion_invalid_list:
            function_hypervisor.update("username", value)
            result = virtwho.run_service()
            assert (
                result["error"] is not 0
                and result["send"] == 0
                and result["thread"] == 1
                and assertion["invalid"][f"{value}"] in result["error_msg"]
            )

        # username option is disable
        function_hypervisor.delete("username")
        result = virtwho.run_service()
        assert (
            result["error"] is not 0
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
            result["error"] is not 0
            and result["send"] == 1
            and result["thread"] == 1
            and assertion["disable_multi_configs"] in result["error_msg"]
        )

    @pytest.mark.tier2
    def test_password(self, virtwho, function_hypervisor, hyperv_assertion):
        """Test the password= option in /etc/virt-who.d/test_hyperv.conf

        :title: virt-who: hyperv: test password option
        :id: efe153df-c9ac-4ae2-9ec1-e5c05a3cc3d0
        :caseimportance: High
        :tags: hypervisor,hyperv,tier2
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
        assertion = hyperv_assertion["password"]
        assertion_invalid_list = list(assertion["invalid"].keys())
        for value in assertion_invalid_list:
            function_hypervisor.update("password", value)
            result = virtwho.run_service()
            assert (
                result["error"] is not 0
                and result["send"] == 0
                and result["thread"] == 1
                and assertion["invalid"][f"{value}"] in result["error_msg"]
            )

        # password option is disable
        function_hypervisor.delete("password")
        result = virtwho.run_service()
        assert (
            result["error"] is not 0
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
            result["error"] is not 0
            and result["send"] == 1
            and result["thread"] == 1
            and assertion["disable_multi_configs"] in result["error_msg"]
        )

    @pytest.mark.tier2
    def test_encrypted_password(
        self, virtwho, function_hypervisor, hyperv_assertion, hypervisor_data, ssh_host
    ):
        """Test the encrypted_password= option in /etc/virt-who.d/test_hyperv.conf

        :title: virt-who: hyperv: test encrypted_password option
        :id: 273f9701-1eab-49b1-98c3-d1b38f6f6493
        :caseimportance: High
        :tags: hypervisor,hyperv,tier2
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
        assertion = hyperv_assertion["encrypted_password"]
        assertion_invalid_list = list(assertion["invalid"].keys())
        for value in assertion_invalid_list:
            function_hypervisor.update("encrypted_password", value)
            result = virtwho.run_service()
            assert (
                result["error"] is not 0
                and result["send"] == 0
                and result["thread"] == 0
                and assertion["invalid"][f"{value}"] in result["error_msg"]
            )

        # encrypted_password option is valid but another config is ok
        hypervisor_create(
            HYPERVISOR, REGISTER, SECOND_HYPERVISOR_FILE, SECOND_HYPERVISOR_SECTION
        )
        result = virtwho.run_service()
        assert (
            result["error"] is not 0
            and result["send"] == 1
            and result["thread"] == 1
            and assertion["valid_multi_configs"] in result["error_msg"]
        )

    @pytest.mark.tier2
    def test_filter_hosts(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the filter_hosts= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: hyperv: test filter_hosts negative option
        :id: 8531124d-cff1-4ca8-acca-56f28345dcaf
        :caseimportance: High
        :tags: hypervisor,hyperv,tier2
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
        hypervisor_ids = ["hostname", "uuid"]
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

        :title: virt-who: hyperv: test exclude_hosts negative option
        :id: b8b3d98a-0376-48de-88b6-9f7b4da849ac
        :caseimportance: High
        :tags: hypervisor,hyperv,tier2
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
        hypervisor_ids = ["hostname", "uuid"]
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
    
    @pytest.mark.tier3
    def test_biosguid_null(self, virtwho, function_hypervisor, hypervisor_data, register_data):
        """Test if the biosguid is null, whether virt-who can send the guest info to server.
        
        :title: virt-who: hyperv: test biosguid null
        :id: 4de4fed0-97c2-4146-9540-2223386297c4
        :caseimportance: High
        :tags: hypervisor,hyperv,tier3
        :customerscenario: false
        :upstream: no
        :steps:
            1. Run virt-who with normal guid.
            2. Download the New-VMBIOSGUID.ps1 script from the server.
            3. Import the New-VMBIOSGUID.ps1 script.
            4. Change the biosguid to null.
            5. Run virt-who again.
            6. Change the biosguid to the original value.
        :expectedresults:
            1. Succeeded to run the virt-who, can find the guest info in the server.
            2. Succeeded to download the New-VMBIOSGUID.ps1 script.
            3. Succeeded to import the New-VMBIOSGUID.ps1 script.
            4. Succeeded to change the biosguid to null.
            5. Succeeded to run the virt-who, cannot find the guest info in the server.
        """
        
        hyperv = HypervCLI(
            server = hypervisor_data["hypervisor_server"],
            ssh_user = hypervisor_data["hypervisor_username"],
            ssh_pwd = hypervisor_data["hypervisor_password"],
        )
        
        result = virtwho.run_service()
        assert (
            result["error"] == 0
            and result["send"] == 1
            and result["thread"] == 1
        )
        try:
            origin_guid = hyperv.guest_uuid()
            assert origin_guid != ""

            result = hyperv.guest_uuid_change("00000000-0000-0000-0000-000000000000", hypervisor_data['guest_name'])
            assert result is True
            
            timeout = 300
            interval = 5
            start_time = time.time()
            while not is_host_responsive(hypervisor_data["guest_ip"]):
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    assert False, f"Timeout reached after {timeout} seconds!"
                time.sleep(interval)
            
            result = virtwho.run_service()
            assert (
                result["error"] == 0
                and result["send"] == 1
                and result["thread"] == 1
                and len(result["mappings"][register_data["default_org"]][hypervisor_data["hypervisor_hostname"]]["guests"])==0
            )
            
            new_guid = hyperv.guest_uuid()
            assert new_guid == ""
        finally:
            result = hyperv.guest_uuid_change(origin_guid, hypervisor_data['guest_name'])
            assert result is True
            
            final_guid = hyperv.guest_uuid()
            assert final_guid == origin_guid
