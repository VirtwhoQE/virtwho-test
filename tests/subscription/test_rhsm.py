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


@pytest.mark.skip(reason="SCA mode is no longer available.")
@pytest.mark.usefixtures("class_globalconf_clean")
@pytest.mark.usefixtures("class_hypervisor")
@pytest.mark.usefixtures("class_guest_register")
@pytest.mark.usefixtures("class_guest_unregister")
@pytest.mark.usefixtures("function_host_register_for_local_mode")
@pytest.mark.usefixtures("class_rhsm_sca_enable")
class TestRHSM:
    @pytest.mark.tier1
    @pytest.mark.gating
    def test_guest_sub_man_status(self, ssh_guest):
        """

        :title: virt-who: rhsm: test guest subscription-manager status
        :id: 20c09b1b-f23e-4691-b927-ed5262c188da
        :caseimportance: Medium
        :tags: subscription,rhsm,tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. register guest
            2. check the #subscription-manager status

        :expectedresults:

            2. get the output with 'Content Access Mode is set to Simple Content Access.
            This host has access to content, regardless of subscription status'

        """
        ret, output = ssh_guest.runcmd("subscription-manager status")
        msg = (
            "Content Access Mode is set to Simple Content Access. "
            "This host has access to content, regardless of subscription status."
        )
        assert msg_search(output, msg)
        # Todo: design new steps and/or cases related to virt-who


@pytest.fixture(scope="class")
def class_rhsm_sca_enable(rhsm):
    """Enable sca mode for stage candlepin"""
    rhsm.sca(sca="enable")
