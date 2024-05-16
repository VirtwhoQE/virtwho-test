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
from virtwho import RHEL_COMPOSE, logger


@pytest.mark.usefixtures("class_globalconf_clean")
@pytest.mark.usefixtures("class_hypervisor")
@pytest.mark.usefixtures("class_guest_register")
@pytest.mark.usefixtures("class_guest_unregister")
@pytest.mark.usefixtures("function_guest_unattach")
@pytest.mark.usefixtures("function_host_register_for_local_mode")
@pytest.mark.usefixtures("class_rhsm_sca_enable")
class TestRhsmScaEnable:
    @pytest.mark.tier1
    @pytest.mark.gating
    def test_hypervisor_entitlement_status(
        self, virtwho, hypervisor_data, rhsm, vdc_pool_physical
    ):
        """Test the hypervisor entitlement status.

        :title: virt-who: rhsm: [sca/enable] test hypervisor entitlement status
        :id: c505edb4-9afa-401f-bc3d-f562d8081955
        :caseimportance: Medium
        :tags: subscription,rhsm,tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. run virt-who to report mappings
            2. try to attach vdc sku for hypervisor

        :expectedresults:

            failed to attach any sku with sca enabled. bz2017774 exists for rhsm.
        """
        hypervisor_hostname = hypervisor_data["hypervisor_hostname"]
        result = virtwho.run_cli()
        assert result["send"] == 1 and result["error"] == 0

        logger.info("=== RHSM has bz2017774, skip the checking tempoparily ===")
        rhsm.attach(host_name=hypervisor_hostname, pool=vdc_pool_physical)

    @pytest.mark.tier1
    @pytest.mark.gating
    def test_guest_entitlement_status(
        self,
        virtwho,
        ssh_guest,
        sm_guest,
        function_guest_register,
        hypervisor_data,
        rhsm,
        vdc_pool_physical,
    ):
        """

        :title: virt-who: rhsm: [sca/enable] test guest entitlement status
        :id: 20c09b1b-f23e-4691-b927-ed5262c188da
        :caseimportance: Medium
        :tags: subscription,rhsm,tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. register guest
            2. check the #subscription-manager status
            3. try to attach vdc sku for guest by terminal
            4. try to attach vdc sku for guest by rhsm web

        :expectedresults:

            2. get the output with 'Content Access Mode is set to Simple Content Access.
            This host has access to content, regardless of subscription status'
            3. get the 'Attaching subscriptions is disabled .* because Simple Content
            Access .* is enabled.'
            4. failed to attach any sku with sca enabled. bz2017774 exists for rhsm.
        """
        guest_hostname = hypervisor_data["guest_hostname"]
        virtwho.run_cli()

        ret, output = ssh_guest.runcmd("subscription-manager status")
        msg = (
            "Content Access Mode is set to Simple Content Access. "
            "This host has access to content, regardless of subscription status."
        )
        assert msg_search(output, msg)

        output = sm_guest.attach(pool=vdc_pool_physical)

        msg = "Attaching subscriptions is disabled .* because Simple Content Access .* is enabled."
        if "RHEL-8" in RHEL_COMPOSE:
            msg = [
                "Ignoring request to attach. "
                "It is disabled for org .* because of the content access mode setting.",  # esx
                "Ignoring the request to attach. Attaching subscriptions is disabled "
                "for organization .* because Simple Content Access .* is enabled",  # kubevirt
            ]

        assert msg_search(output, msg)

        logger.info("=== RHSM has bz2017774, skip the checking tempoparily ===")
        rhsm.attach(host_name=guest_hostname, pool=vdc_pool_physical)


@pytest.fixture(scope="class")
def class_rhsm_sca_enable(rhsm):
    """Enable sca mode for stage candlepin"""
    rhsm.sca(sca="enable")
