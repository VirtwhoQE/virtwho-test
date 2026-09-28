"""Test cases for HyperV Kerberos authentication

Basic coverage of the auth_method/kerberos_keytab/kerberos_principal
support added to virt-who's HyperV backend (virt-who commit 9bb793b,
CCT-2189).

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
:subsystemteam: rhel-sst-csi-client-tools
:caselevel: Component
"""

import pytest

from virtwho import RHEL_VERSION

pytestmark = pytest.mark.skipif(
    RHEL_VERSION < 10, reason="HyperV Kerberos auth requires RHEL 10+"
)


def _require_kerberos_creds(hypervisor_data):
    """Skip when no real kerberos_keytab_b64/kerberos_principal are
    configured in virtwho.ini, since these tests need to actually
    authenticate."""
    if not hypervisor_data.get("kerberos_keytab_b64") or not hypervisor_data.get(
        "kerberos_principal"
    ):
        pytest.skip(
            "kerberos_keytab_b64/kerberos_principal are not configured in "
            "virtwho.ini; cannot exercise real Kerberos authentication"
        )


@pytest.mark.usefixtures("function_virtwho_d_conf_clean")
@pytest.mark.usefixtures("class_debug_true")
@pytest.mark.usefixtures("class_globalconf_clean")
class TestHypervKerberosPositive:
    @pytest.mark.tier1
    def test_kerberos_auth_with_keytab_and_principal(
        self, virtwho, function_hypervisor, hypervisor_data
    ):
        """Test auth_method=kerberos with kerberos_keytab and kerberos_principal set

        :title: virt-who: hyperv: test kerberos auth with keytab and principal
        :id: 7e3b7a4a-6b3a-4e7a-9a3a-1b7a4a6b3a4e
        :caseimportance: High
        :tags: hypervisor,hyperv,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Delete username/password, set auth_method=kerberos.
            2. Set kerberos_keytab and kerberos_principal to valid values.
            3. Run the virt-who service.
        :expectedresults:
            3. Succeeded to run the virt-who, no error messages in the log info
        """
        _require_kerberos_creds(hypervisor_data)
        function_hypervisor.enable_kerberos_auth()
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

    @pytest.mark.tier1
    def test_kerberos_ignores_username_and_password(
        self, virtwho, function_hypervisor, hypervisor_data, hyperv_kerberos_assertion
    ):
        """Test that username/password are ignored (with a warning) when
        auth_method=kerberos

        :title: virt-who: hyperv: test kerberos auth ignores username/password
        :id: 5e6f7a8b-9c0d-4e5f-8a6b-7c8d9e0f1a2b
        :caseimportance: Medium
        :tags: hypervisor,hyperv,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Set auth_method=kerberos with valid kerberos_keytab/kerberos_principal.
            2. Also set valid username and password.
            3. Run the virt-who service.
        :expectedresults:
            3. Succeeded to run the virt-who via kerberos, and warning messages
                state that username/password are ignored
        """
        _require_kerberos_creds(hypervisor_data)
        function_hypervisor.enable_kerberos_auth()
        function_hypervisor.update("username", hypervisor_data["hypervisor_username"])
        function_hypervisor.update("password", hypervisor_data["hypervisor_password"])
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
        assert hyperv_kerberos_assertion["username_ignored"] in result["warning_msg"]
        assert hyperv_kerberos_assertion["password_ignored"] in result["warning_msg"]


@pytest.mark.usefixtures("function_virtwho_d_conf_clean")
@pytest.mark.usefixtures("class_debug_true")
@pytest.mark.usefixtures("class_globalconf_clean")
class TestHypervKerberosNegative:
    @pytest.mark.tier1
    def test_auth_method_invalid(
        self, virtwho, function_hypervisor, hyperv_kerberos_assertion
    ):
        """Test the auth_method= option with an invalid value

        Pure config validation -- no real Kerberos infra required.

        :title: virt-who: hyperv: test invalid auth_method value
        :id: 7a8b9c0d-1e2f-4a7b-8c9d-0e1f2a3b4c5d
        :caseimportance: High
        :tags: hypervisor,hyperv,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Configure auth_method with an invalid value.
        :expectedresults:
            1. Failed to run virt-who, find the invalid auth_method error message,
                and the configuration is dropped
        """
        assertion = hyperv_kerberos_assertion["auth_method"]["invalid"]
        for value in assertion:
            function_hypervisor.update("auth_method", value)
            result = virtwho.run_service()
            assert (
                result["error"] != 0
                and result["send"] == 0
                and result["thread"] == 0
                and assertion[value] in result["error_msg"]
                and hyperv_kerberos_assertion["dropped_config"] in result["warning_msg"]
            )

    @pytest.mark.tier1
    def test_kerberos_keytab_missing_file(
        self, virtwho, function_hypervisor, hyperv_kerberos_assertion
    ):
        """Test the kerberos_keytab= option pointing to a non-existent file

        Pure config validation -- no real Kerberos infra required.

        :title: virt-who: hyperv: test kerberos_keytab missing file
        :id: 8b9c0d1e-2f3a-4b8c-9d0e-1f2a3b4c5d6e
        :caseimportance: High
        :tags: hypervisor,hyperv,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Set auth_method=kerberos.
            2. Configure kerberos_keytab with a path that does not exist.
        :expectedresults:
            2. Failed to run virt-who, find the keytab error message, and the
                configuration is dropped
        """
        function_hypervisor.enable_kerberos_auth(keytab=False, principal=False)
        function_hypervisor.update("kerberos_keytab", "/no/such/file.keytab")
        result = virtwho.run_service()
        assert (
            result["error"] != 0
            and result["send"] == 0
            and result["thread"] == 0
            and hyperv_kerberos_assertion["kerberos_keytab"]["missing_file"]
            in result["error_msg"]
        )

    @pytest.mark.tier1
    def test_kerberos_principal_empty(
        self, virtwho, function_hypervisor, hyperv_kerberos_assertion
    ):
        """Test the kerberos_principal= option with an empty value

        Pure config validation -- no real Kerberos infra required.

        :title: virt-who: hyperv: test kerberos_principal empty value
        :id: 9c0d1e2f-3a4b-4c9d-8e1f-2a3b4c5d6e7f
        :caseimportance: High
        :tags: hypervisor,hyperv,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. Set auth_method=kerberos.
            2. Configure kerberos_principal with an empty value.
        :expectedresults:
            2. Failed to run virt-who, find the principal error message, and the
                configuration is dropped
        """
        function_hypervisor.enable_kerberos_auth(keytab=False, principal=False)
        function_hypervisor.update("kerberos_principal", "")
        result = virtwho.run_service()
        assert (
            result["error"] != 0
            and result["send"] == 0
            and result["thread"] == 0
            and hyperv_kerberos_assertion["kerberos_principal"]["empty"]
            in result["error_msg"]
        )
