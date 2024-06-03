"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""
import pytest
from virtwho.base import msg_search
from virtwho import REGISTER, HYPERVISOR
from virtwho import SECOND_HYPERVISOR_FILE
from virtwho import SECOND_HYPERVISOR_SECTION

from virtwho.base import encrypt_password
from virtwho.configure import hypervisor_create


@pytest.mark.usefixtures("class_yield_rhsmconf_recovery")
@pytest.mark.usefixtures("class_host_unregister")
@pytest.mark.usefixtures("function_virtwho_d_conf_clean")
@pytest.mark.usefixtures("class_debug_true")
@pytest.mark.usefixtures("class_globalconf_clean")
@pytest.mark.usefixtures("function_rhsmconf_recovery")
@pytest.mark.notLocal
class TestSubscriptionPositive:
    @pytest.mark.tier1
    @pytest.mark.satelliteSmoke
    def test_no_rhsm_options(
        self, virtwho, function_hypervisor, sm_host, register_assertion
    ):
        """Test the /etc/virt-who.d/x.conf without any rhsm option

        :title: virt-who: rhsm_option: test no rhsm options in config file (positive)
        :id: 09167890-bbd0-470a-a342-66bbe29f91f9
        :caseimportance: High
        :tags: subscription,rhsm_option,tier1
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
        assert result["send"] == 1 and result["error"] == 0

        sm_host.unregister()
        result = virtwho.run_cli()
        assert (
            result["send"] == 0
            and result["error"] != 0
            and msg_search(result["log"], register_assertion["unregister_host"])
        )

    @pytest.mark.tier1
    @pytest.mark.satelliteSmoke
    def test_rhsm_encrypted_password(
        self, virtwho, function_hypervisor, ssh_host, register_data
    ):
        """Test the rhsm_encrypted_password= option in /etc/virt-who.d/x.conf

        :title: virt-who: rhsm_option: test rhsm_encrypted_password option (positive)
        :id: a748e63c-0c80-444d-8bc4-0f6cad783be6
        :caseimportance: High
        :tags: subscription,rhsm_option,tier1
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
        function_hypervisor.delete("rhsm_password")
        encrypted_pwd = encrypt_password(ssh_host, register_data["password"])
        function_hypervisor.update("rhsm_encrypted_password", encrypted_pwd)
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

    @pytest.mark.tier1
    @pytest.mark.satelliteSmoke
    @pytest.mark.fipsEnable
    @pytest.mark.fedoraSmoke
    def test_rhsm_proxy(self, virtwho, function_hypervisor, rhsmconf, proxy_data):
        """

        :title: virt-who: rhsm_option: test rhsm_proxy=
        :id: a1b22c6c-74f7-4c14-8276-f55f589ba746
        :caseimportance: High
        :tags: subscription,rhsm_option,tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. run virt-who with good proxy in /etc/rhsm/rhsm.conf
            2. run virt-who with good proxy in /etc/virt-who.d/
            3. run virt-who with good proxy in /etc/rhsm/rhsm.conf
                and bad proxy in /etc/virt-who.d/.

        :expectedresults:

            1. virt-who can run successfully with good proxy
            2. the rhsm_proxy in /etc/virt-who.d/ has high priority than
                the /etc/rhsm/rhsm.conf.
        """
        # run virt-who with good proxy in /etc/rhsm/rhsm.conf
        for scheme in ["http", "https"]:
            rhsmconf.update("server", "proxy_hostname", proxy_data["server"])
            rhsmconf.update("server", "proxy_port", proxy_data["port"])
            rhsmconf.update("server", "proxy_scheme", scheme)
            connection_msg = proxy_data["connection_log"]
            proxy_msg = proxy_data["proxy_log"]
            result = virtwho.run_service()
            assert (
                result["error"] == 0
                and result["send"] == 1
                and result["thread"] == 1
                and connection_msg in result["log"]
                and proxy_msg in result["log"]
            )
        rhsmconf.recovery()

        # run virt-who with good proxy in /etc/virt-who.d/
        function_hypervisor.update("rhsm_proxy_hostname", proxy_data["server"])
        function_hypervisor.update("rhsm_proxy_port", proxy_data["port"])
        connection_msg = proxy_data["connection_log"]
        proxy_msg = proxy_data["proxy_log"]
        result = virtwho.run_service()
        assert (
            result["error"] == 0
            and result["send"] == 1
            and result["thread"] == 1
            and connection_msg in result["log"]
            and proxy_msg in result["log"]
        )

        # test the rhsm_proxy in /etc/virt-who.d/ has high priority
        rhsmconf.update("server", "proxy_hostname", proxy_data["server"])
        rhsmconf.update("server", "proxy_port", proxy_data["port"])
        function_hypervisor.update("rhsm_proxy_hostname", proxy_data["bad_server"])
        function_hypervisor.update("rhsm_proxy_port", proxy_data["bad_port"])
        result = virtwho.run_service()
        assert (
            result["error"] == 1
            or 2
            and msg_search(result["error_msg"], proxy_data["error"])
        )


@pytest.mark.usefixtures("class_yield_rhsmconf_recovery")
@pytest.mark.usefixtures("class_host_unregister")
@pytest.mark.usefixtures("class_debug_true")
@pytest.mark.usefixtures("class_globalconf_clean")
@pytest.mark.usefixtures("function_virtwho_d_conf_clean")
@pytest.mark.usefixtures("function_rhsmconf_recovery")
@pytest.mark.notLocal
class TestSubscriptionNegative:
    @pytest.mark.tier2
    def test_owner(self, virtwho, function_hypervisor, register_assertion):
        """Test the owner= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm_option: test owner option (negative)
        :id: ae0abf52-ab25-4544-a0f7-5ba13bcfaf3e
        :caseimportance: High
        :tags: subscription,rhsm_option,tier2
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
        assertion = register_assertion["owner"]

        # invalid
        invalid = assertion["invalid"]
        for key, value in invalid.items():
            function_hypervisor.update("owner", key)
            result = virtwho.run_service()
            assert (
                result["error"] is not 0
                and result["send"] == 0
                and result["thread"] == 1
                and msg_search(result["error_msg"], value)
            )

        # disable
        function_hypervisor.delete("owner")
        result = virtwho.run_service()
        assert (
            result["error"] is not 0
            and result["send"] == 0
            and result["thread"] == 0
            and msg_search(result["error_msg"], assertion["disable"])
        )

        # disable but another config is ok
        hypervisor_create(
            HYPERVISOR, REGISTER, SECOND_HYPERVISOR_FILE, SECOND_HYPERVISOR_SECTION
        )
        result = virtwho.run_service()
        assert (
            result["error"] is not 0
            and result["send"] == 1
            and result["thread"] == 1
            and msg_search(result["error_msg"], assertion["disable_with_another_good"])
        )

        # null but another config is ok
        function_hypervisor.update("owner", "")
        result = virtwho.run_service()
        assert (
            result["error"] is not 0
            and result["send"] == 1
            and result["thread"] == 1
            and msg_search(result["error_msg"], assertion["null_with_another_good"])
        )

    @pytest.mark.tier2
    def test_rhsm_hostname(self, virtwho, function_hypervisor, register_assertion):
        """Test the rhsm_hostname= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm_option: test rhsm_hostname option (negative)
        :id: 055f5ea2-e4f2-4342-9fb8-aa0e4b765394
        :caseimportance: High
        :tags: subscription,rhsm_option,tier2
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
        assertion = register_assertion["rhsm_hostname"]

        # invalid value
        invalid = assertion["invalid"]
        for key, value in invalid.items():
            function_hypervisor.update("rhsm_hostname", key)
            result = virtwho.run_service()
            assert (
                result["error"] is not 0
                and result["send"] == 0
                and result["thread"] == 1
                and msg_search(result["log"], value)
            )

        # disable
        function_hypervisor.delete("rhsm_hostname")
        result = virtwho.run_service()
        assert (
            result["error"] is not 0
            and result["send"] == 0
            and result["thread"] == 1
            and msg_search(result["error_msg"], assertion["disable"])
        )

    @pytest.mark.tier2
    @pytest.mark.notLocal
    def test_rhsm_port(
        self, virtwho, function_hypervisor, rhsmconf, register_assertion
    ):
        """Test the rhsm_port= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm_option: test rhsm_port option (negative)
        :id: a1149344-b6c0-485c-96fc-9da4705e6b15
        :caseimportance: High
        :tags: subscription,rhsm_option,tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Unregister virt-who host
            2. Recover /etc/rhsm/rhsm.conf to default
            4. Delete the port= option in /etc/rhsm/rhsm.conf
            5. Run virt-who with rhsm_port=[invalid value]
            6. Run virt-who with rhsm_port=null
            7. Run virt-who without rhsm_port=
        :expectedresults:
            1. Invalid: virt-who starts but fails to report with error
            2. Null: virt-who reports successfully
                (use the port=443 as default)
            3. Disable: virt-who reports successfully
                (use the port=443 as default)
        """
        assertion = register_assertion["rhsm_port"]
        rhsmconf.delete("server", "port")

        # invalid value
        invalid = assertion["invalid"]
        for key, value in invalid.items():
            function_hypervisor.update("rhsm_port", key)

            result = virtwho.run_service(wait=120)
            assert (
                result["error"] is not 0
                and result["send"] == 0
                and result["thread"] == 1
                and msg_search(result["log"], value)
            )

        # null, will use the default 443
        function_hypervisor.update("rhsm_port", "")
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

        # disable, will use the default 443
        function_hypervisor.delete("rhsm_port")
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

    @pytest.mark.tier2
    def test_rhsm_prefix(
        self, virtwho, function_hypervisor, register_assertion, rhsmconf
    ):
        """Test the rhsm_prefix= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm_option: test rhsm_prefix option (negative)
        :id: 5c91dca3-835a-4d5a-936e-e93d3a13d1f6
        :caseimportance: High
        :tags: subscription,rhsm_option,tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. Unregister virt-who host
            2. Recover /etc/rhsm/rhsm.conf to default
            3. Delete/disable prefix= option in /etc/rhsm/rhsm.conf
            4. Run virt-who with rhsm_prefix=[invalid value]
            5. Run virt-who with rhsm_prefix=null
            6. Run virt-who without rhsm_prefix=
        :expectedresults:
            1. Invalid: virt-who starts but fails to report with error
            2. Null:
                RHSM: virt-who reports successfully
                    (use the prefix=/subscription as default)
                Satellite: virt-who starts but fails to report with error
            3. Disable:
                RHSM: virt-who reports successfully
                    (use the prefix=/subscription as default)
                Satellite: virt-who starts but fails to report with error
        """
        assertion = register_assertion["rhsm_prefix"]
        rhsmconf.delete("server", "prefix")

        # invalid value
        invalid = assertion["invalid"]
        for key, value in invalid.items():
            function_hypervisor.update("rhsm_prefix", key)
            result = virtwho.run_service()
            assert (
                result["error"] is not 0
                and result["send"] == 0
                and result["thread"] == 1
                and msg_search(result["error_msg"], value)
            )

        if REGISTER == "satellite":
            # null
            function_hypervisor.update("rhsm_prefix", "")
            result = virtwho.run_service()
            assert (
                result["error"] is not 0
                and result["send"] == 0
                and result["thread"] == 1
                and msg_search(result["error_msg"], assertion["null"])
            )

            # disable
            function_hypervisor.delete("rhsm_prefix")
            result = virtwho.run_service()
            assert (
                result["error"] is not 0
                and result["send"] == 0
                and result["thread"] == 1
                and msg_search(result["error_msg"], assertion["disable"])
            )
        else:
            # null, will use the default /subscription
            function_hypervisor.update("rhsm_prefix", "")
            result = virtwho.run_service()
            assert (
                result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
            )

            # disable, will use the default /subscription
            function_hypervisor.delete("rhsm_prefix")
            result = virtwho.run_service()
            assert (
                result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
            )

    @pytest.mark.tier2
    def test_rhsm_username(self, virtwho, function_hypervisor, register_assertion):
        """Test the rhsm_username= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm_option: test rhsm_username option (negative)
        :id: c6db8133-678f-41e0-8ce9-649afe6a6615
        :caseimportance: High
        :tags: subscription,rhsm_option,tier2
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
        assertion = register_assertion["rhsm_username"]

        # invalid value
        invalid = assertion["invalid"]
        for key, value in invalid.items():
            function_hypervisor.update("rhsm_username", key)
            result = virtwho.run_service()
            assert (
                result["error"] is not 0
                and result["send"] == 0
                and result["thread"] == 1
                and msg_search(result["log"], value)
            )

        # disable
        function_hypervisor.delete("rhsm_username")
        result = virtwho.run_service()
        assert (
            result["error"] is not 0
            and result["send"] == 0
            and result["thread"] == 1
            and msg_search(result["log"], assertion["disable"])
        )

    @pytest.mark.tier2
    def test_rhsm_password(self, virtwho, function_hypervisor, register_assertion):
        """Test the rhsm_password= option in /etc/virt-who.d/xx.conf

        :title: virt-who: rhsm_option: test rhsm_password option (negative)
        :id: 0a9496e2-8634-4725-983f-d56a2133e3d4
        :caseimportance: High
        :tags: subscription,rhsm_option,tier2
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
        assertion = register_assertion["rhsm_password"]

        # invalid value
        invalid = assertion["invalid"]
        for key, value in invalid.items():
            function_hypervisor.update("rhsm_password", key)
            result = virtwho.run_service()
            assert (
                result["error"] is not 0
                and result["send"] == 0
                and result["thread"] == 1
                and msg_search(result["log"], value)
            )

        # disable
        function_hypervisor.delete("rhsm_password")
        result = virtwho.run_service()
        assert (
            result["error"] is not 0
            and result["send"] == 0
            and result["thread"] == 1
            and msg_search(result["log"], assertion["disable"])
        )

    @pytest.mark.tier2
    def test_rhsm_encrypted_password(
        self, virtwho, function_hypervisor, ssh_host, register_assertion
    ):
        """Test the rhsm_encrypted_password= option in /etc/virt-who.d/x.conf

        :title: virt-who: rhsm_option: test rhsm_encrypted_password option
            (negative)
        :id: daab24a6-21a9-49dc-a129-46c742a9ef84
        :caseimportance: High
        :tags: subscription,rhsm_option,tier2
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
        assertion = register_assertion["rhsm_encrypted_password"]
        function_hypervisor.delete("rhsm_password")

        # invalid value
        invalid = assertion["invalid"]
        for key, value in invalid.items():
            function_hypervisor.update("rhsm_encrypted_password", key)
            result = virtwho.run_service()
            assert (
                result["error"] is not 0
                and result["send"] == 0
                and result["thread"] == 1
                and msg_search(result["log"], value)
            )

    @pytest.mark.tier2
    def test_rhsm_proxy_in_rhsmconf(
        self,
        virtwho,
        function_hypervisor,
        globalconf,
        rhsmconf,
        proxy_data,
        register_data,
    ):
        """

        :title: virt-who: rhsm_option: test rhsm_proxy= in /etc/rhsm/rhsm.conf
            (negative)
        :id: a1e0f565-bdd2-43af-914a-d21f6d247227
        :caseimportance: High
        :tags: subscription,rhsm_option,tier2
        :customerscenario: false
        :upstream: no
        :steps:

            1. run virt-who with bad proxy in /etc/rhsm/rhsm.conf
            2. set no_proxy=* in /etc/rhsm/rhsm.conf
            3. set no_proxy=[rhsm_server] in /etc/rhsm/rhsm.conf
            4. set no_proxy=[rhsm_server] in /etc/virt-who.conf
            5. set rhsm_no_proxy=[rhsm_server] in /etc/virt-who.conf
            6. set rhsm_no_proxy=[rhsm_server] in /etc/virt-who.d/

        :expectedresults:

            1. virt-who cannot report with bad proxy in /etc/rhsm/rhsm.conf
            2. the no_proxy or rhsm_no_proxy in /etc/rhsm/rhsm.conf,
                /etc/virt-who.conf or /etc/virt-who.d/ can help virt-who
                ignoring the bad proxy
        """
        register_server = register_data["server"]
        error_msg = proxy_data["error"]

        for scheme in ["http", "https"]:
            # run virt-who with bad proxy in /etc/rhsm/rhsm.conf
            rhsmconf.update("server", "proxy_hostname", proxy_data["bad_server"])
            rhsmconf.update("server", "proxy_port", proxy_data["bad_port"])
            rhsmconf.update("server", "proxy_scheme", scheme)
            result = virtwho.run_service()
            assert (
                result["error"] == 1
                or 2
                and result["mappings"]
                and msg_search(result["error_msg"], error_msg)
            )

            # set no_proxy=* in /etc/rhsm/rhsm.conf
            rhsmconf.update("server", "no_proxy", "*")
            result = virtwho.run_service()
            assert (
                result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
            )

            # set no_proxy=[rhsm_server] in /etc/rhsm/rhsm.conf
            rhsmconf.update("server", "no_proxy", register_server)
            result = virtwho.run_service()
            assert (
                result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
            )
            rhsmconf.update("server", "no_proxy", "")

            # set no_proxy=[rhsm_server] in /etc/virt-who.conf
            globalconf.update("system_environment", "no_proxy", register_server)
            result = virtwho.run_service()
            assert (
                result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
            )
            globalconf.delete("system_environment")

            # set rhsm_no_proxy=[rhsm_server] in /etc/virt-who.conf
            globalconf.update("defaults", "rhsm_no_proxy", register_server)
            result = virtwho.run_service()
            assert (
                result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
            )
            globalconf.delete("defaults", "rhsm_no_proxy")

            # set rhsm_no_proxy=[rhsm_server] in /etc/virt-who.d/
            function_hypervisor.update("rhsm_no_proxy", register_server)
            result = virtwho.run_service()
            assert (
                result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
            )
            function_hypervisor.delete("rhsm_no_proxy")

    @pytest.mark.tier2
    def test_rhsm_proxy_in_virtwho_d(
        self,
        virtwho,
        function_hypervisor,
        globalconf,
        rhsmconf,
        proxy_data,
        register_data,
    ):
        """

        :title: virt-who: rhsm_option: test rhsm_proxy= in /etc/virt-who.d/
        :id: 3cc1562b-3843-42fe-80a9-4d5b6801b703
        :caseimportance: High
        :tags: subscription,rhsm_option,tier2
        :customerscenario: false
        :upstream: no
        :steps:

            1. run virt-who with bad proxy in /etc/virt-who.d/
            2. set rhsm_no_proxy=* in /etc/virt-who.d/
            3. set rhsm_no_proxy=[rhsm_server] in /etc/virt-who.d/
            4. set no_proxy=[rhsm_server] in /etc/rhsm/rhsm.conf
            5. set no_proxy=[rhsm_server] in /etc/virt-who.conf
            6. set rhsm_no_proxy=[rhsm_server] in /etc/virt-who.conf

        :expectedresults:

            1. virt-who cannot report with bad proxy in /etc/virt-who.d/
            2. the no_proxy or rhsm_no_proxy in /etc/rhsm/rhsm.conf,
                /etc/virt-who.conf or /etc/virt-who.d/ can help virt-who
                ignoring the bad proxy
        """
        register_server = register_data["server"]
        error_msg = proxy_data["error"]

        # run virt-who with bad proxy in /etc/virt-who.d/
        function_hypervisor.update("rhsm_proxy_hostname", proxy_data["bad_server"])
        function_hypervisor.update("rhsm_proxy_port", proxy_data["bad_port"])
        result = virtwho.run_service()
        assert (
            result["error"] == 1
            or 2
            and result["mappings"]
            and msg_search(result["error_msg"], error_msg)
        )

        # set rhsm_no_proxy=* in /etc/virt-who.d/
        function_hypervisor.update("rhsm_no_proxy", "*")
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

        # set rhsm_no_proxy=[rhsm_server] in /etc/virt-who.d/
        function_hypervisor.update("rhsm_no_proxy", register_server)
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

        # set no_proxy=[rhsm_server] in /etc/rhsm/rhsm.conf
        rhsmconf.update("server", "no_proxy", register_server)
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
        rhsmconf.update("server", "no_proxy", "")

        # set no_proxy=[rhsm_server] in /etc/virt-who.conf
        globalconf.update("system_environment", "no_proxy", register_server)
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
        globalconf.delete("system_environment")

        # set rhsm_no_proxy=[rhsm_server] in /etc/virt-who.conf
        globalconf.update("defaults", "rhsm_no_proxy", register_server)
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
        globalconf.delete("defaults", "rhsm_no_proxy")


@pytest.fixture(scope="class")
def class_yield_rhsmconf_recovery(rhsmconf):
    """Recover the /etc/rhsm/rhsm.conf to default one."""
    yield
    rhsmconf.recovery()
