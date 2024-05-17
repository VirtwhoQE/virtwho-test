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
@pytest.mark.usefixtures("class_guest_register")
@pytest.mark.usefixtures("function_host_register_for_local_mode")
@pytest.mark.usefixtures("class_satellite_sca_enable")
class TestSatellite:
    @pytest.mark.tier1
    @pytest.mark.satelliteSmoke
    def test_guest_sub_man_status(
        self,
        ssh_guest,
    ):
        """

        :title: virt-who: satellite: test guest subscription-manager status
        :id: fcbb4e43-da1e-49c8-a454-0f0979a7717a
        :caseimportance: Medium
        :tags: subscription,rhsm,tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. register guest
            2. check the #subscription-manager status

        :expectedresults:

            2. get the output with 'Content Access Mode is set to Simple Content Access'
            Access .* is enabled'
        """
        ret, output = ssh_guest.runcmd("subscription-manager status")
        msg = "Content Access Mode is set to Simple Content Access"
        assert msg_search(output, msg)
        # Todo: design new steps and/or cases related to virt-who


@pytest.fixture(scope="class")
def class_satellite_sca_enable(satellite):
    """Enable sca mode for default org"""
    satellite.sca(org=None, sca="enable")
