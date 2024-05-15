"""Test cases Global fields

:casecomponent: virt-who
:testtype: nonfunctional
:subtype1: Interoperability
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""
import pytest
from virtwho.base import msg_search
from virtwho import HYPERVISOR
from virtwho.configure import get_hypervisor_handler

hypervisor_handler = get_hypervisor_handler(HYPERVISOR)


@pytest.mark.usefixtures("class_hypervisor")
@pytest.mark.usefixtures("class_virtwho_d_conf_clean")
@pytest.mark.usefixtures("class_globalconf_clean")
@pytest.mark.usefixtures("function_guest_unattach")
@pytest.mark.usefixtures("class_guest_register")
@pytest.mark.usefixtures("function_host_register_for_local_mode")
@pytest.mark.usefixtures("class_satellite_sca_enable")
class TestSatelliteScaEnable:
    @pytest.mark.tier1
    @pytest.mark.satelliteSmoke
    def test_hypervisor_entitlement_status(
        self, virtwho, hypervisor_data, satellite, vdc_pool_physical
    ):
        """Test the hypervisor entitlement status.

        :title: virt-who: satellite: [sca/enable] test hypervisor entitlement status
        :id: bda68020-b17e-4442-bcfd-91537e9499e1
        :caseimportance: Medium
        :tags: subscription,satellite,tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. run virt-who to report mappings
            2. try to attach vdc sku for hypervisor

        :expectedresults:

            get the 'This host's organization is in Simple Content Access mode.
            Attaching subscriptions is disabled.'
        """
        hypervisor_hostname = hypervisor_data["hypervisor_hostname"]
        result = virtwho.run_cli()
        assert result["send"] == 1 and result["error"] == 0

        msg = "This host's organization is in Simple Content Access mode. Attaching subscriptions is disabled."
        result = satellite.attach(host=hypervisor_hostname, pool=vdc_pool_physical)
        assert msg_search(result, msg)

    @pytest.mark.tier1
    @pytest.mark.satelliteSmoke
    def test_guest_entitlement_status(
        self,
        virtwho,
        ssh_guest,
        sm_guest,
        function_guest_register,
        hypervisor_data,
        satellite,
        vdc_pool_physical,
    ):
        """

        :title: virt-who: satellite: [sca/enable] test guest entitlement status
        :id: fcbb4e43-da1e-49c8-a454-0f0979a7717a
        :caseimportance: Medium
        :tags: subscription,rhsm,tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. register guest
            2. check the #subscription-manager status
            3. try to attach vdc sku for guest by terminal
            4. try to attach vdc sku for guest by satellite web

        :expectedresults:

            2. get the output with 'Content Access Mode is set to Simple Content Access'
            3. get the 'Attaching subscriptions is disabled .* because Simple Content
            Access .* is enabled'
            4. get the 'This host's organization is in Simple Content Access mode.
            Attaching subscriptions is disabled.'
        """
        guest_hostname = hypervisor_data["guest_hostname"]
        # virtwho.run_cli()

        ret, output = ssh_guest.runcmd("subscription-manager status")
        msg = "Content Access Mode is set to Simple Content Access"
        assert msg_search(output, msg)

        output = sm_guest.attach(pool=vdc_pool_physical)
        msg = [
            "Attaching subscriptions is disabled .* "
            "because Simple Content Access .* is enabled.",
            "Ignoring request to attach. It is disabled for org .* "
            "because of the content access mode setting.",
        ]
        assert msg_search(output, msg)

        msg = (
            "This host's organization is in Simple Content Access mode. "
            "Attaching subscriptions is disabled."
        )
        result = satellite.attach(host=guest_hostname, pool=vdc_pool_physical)
        assert msg in result


@pytest.fixture(scope="class")
def class_satellite_sca_enable(satellite):
    """Enable sca mode for default org"""
    satellite.sca(org=None, sca="enable")
