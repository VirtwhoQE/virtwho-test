"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""
import pytest

from virtwho import REGISTER
from virtwho import RHEL_COMPOSE
from virtwho import HYPERVISOR
from virtwho import PRINT_JSON_FILE
from virtwho import SECOND_HYPERVISOR_FILE
from virtwho import SECOND_HYPERVISOR_SECTION


from virtwho.configure import hypervisor_create


@pytest.mark.usefixtures("function_virtwho_d_conf_clean")
@pytest.mark.usefixtures("class_debug_true")
@pytest.mark.usefixtures("class_globalconf_clean")
class TestKubevirtPositive:
    @pytest.mark.tier1
    def test_hypervisor_id(
        self, virtwho, function_hypervisor, hypervisor_data, globalconf, rhsm, satellite
    ):
        """Test the hypervisor_id= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: kubevirt: test hypervisor_id function
        :id: c72b5b8b-3b10-49e4-8268-540d1b5a2630
        :caseimportance: High
        :tags: hypervisor,kubevirt,tier1
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

        :title: virt-who: kubevirt: test filter_hosts option
        :id: b26052e6-daba-467c-ac2c-012fe0fd8248
        :caseimportance: High
        :tags: hypervisor,kubevirt,tier1
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

        :title: virt-who: kubevirt: test exclude_hosts option
        :id: 7067ef5a-6289-4db1-b7bd-a4466407f522
        :caseimportance: High
        :tags: hypervisor,kubevirt,tier1
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
    def test_fake_type(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the fake type in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: kubevirt: test fake type
        :id: 8f130d78-28c4-4efb-9e02-3167b4e15be1
        :caseimportance: High
        :tags: hypervisor,kubevirt,tier1
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
        function_hypervisor.update("hypervisor_id", "uuid")
        virtwho.run_cli(prt=True, oneshot=False)
        function_hypervisor.destroy()

        fake_config = hypervisor_create("fake", REGISTER, rhsm=False)
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
class TestKubevirtNegative:
    @pytest.mark.tier2
    def test_type(self, virtwho, function_hypervisor, kubevirt_assertion):
        """Test the type= option in /etc/virt-who.d/test_kubevirt.conf

        :title: virt-who: kubevirt: test type option
        :id: cf06f7a2-e417-45bd-bcea-48d1cac3736c
        :caseimportance: High
        :tags: hypervisor,kubevirt,tier2
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
        assertion = kubevirt_assertion["type"]
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

        # type option is disable but another config is ok
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

        # type option is null but another config is ok
        function_hypervisor.update("type", "")
        result = virtwho.run_service()
        assert result["send"] == 1 and result["thread"] == 1
        if "RHEL-9" in RHEL_COMPOSE:
            assert result["error"] == 1
        else:
            assert result["error"] == 0

    @pytest.mark.tier2
    def test_filter_hosts(self, virtwho, function_hypervisor, hypervisor_data):
        """Test the filter_hosts= option in /etc/virt-who.d/kubevirtisor.conf

        :title: virt-who: kubevirt: test filter_hosts negative option
        :id: 24d7bb49-cd9b-4cd3-85d1-fa86af2d581d
        :caseimportance: High
        :tags: hypervisor,kubevirt,tier2
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

        :title: virt-who: kubevirt: test exclude_hosts negative option
        :id: ee14d972-cd47-4f64-9237-f704f275cf56
        :caseimportance: High
        :tags: hypervisor,kubevirt,tier2
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

    @pytest.mark.tier2
    @pytest.mark.notRHEL8
    def test_insecure(self, virtwho, function_hypervisor, hypervisor_data, ssh_host):
        """Test the insecure option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: kubevirt: test insecure option
        :id: bb777123-3210-4392-9c0d-e7fc332dc762
        :caseimportance: High
        :tags: hypervisor,kubevirt,tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Configure kubeconfig without cert
            2. Configure the insecure option with "none", "", "0", "False" value and run virt-who
            3. Configure the insecure option with "1", "True" value and run virt-who
        :expectedresults:
            2. Failed to run the virt-who service with the error message:
            "certificate verify failed"
            3. Succeed to start the virt-who service
        """
        config_file_no_cert = "/root/kube.conf_no_cert"
        config_url_no_cert = hypervisor_data["hypervisor_config_url_no_cert"]
        cmd = (
            f"rm -f {config_file_no_cert}; "
            f"curl -L {config_url_no_cert} -o {config_file_no_cert}; sync"
        )
        ssh_host.runcmd(cmd)
        function_hypervisor.update("kubeconfig", config_file_no_cert)

        # configure kubeconfig without cert and run virt-who
        for value in ("none", "", "0", "False"):
            # none -> run virt-who without insecure= option
            if value != "none":
                function_hypervisor.update("insecure", value)
            result = virtwho.run_service()
            error_msg = "certificate verify failed"
            assert (
                result["error"] == 1
                and result["send"] == 0
                and result["thread"] == 1
                and error_msg in result["log"]
            )
            function_hypervisor.delete("insecure")

        # test insecure=1/True can ignore checking cert"
        for value in ("1", "True"):
            function_hypervisor.update("insecure", value)
            result = virtwho.run_service()
            assert (
                result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
            )
            function_hypervisor.delete("insecure")

        ssh_host.runcmd(f"rm -rf {config_file_no_cert}")
