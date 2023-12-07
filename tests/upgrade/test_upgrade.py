"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""
import pytest

from virtwho import REGISTER
from virtwho.base import hypervisors_list
from virtwho.configure import hypervisor_create
from virtwho.settings import config

vdc_physical_sku = config.sku.vdc
vdc_virtual_sku = config.sku.vdc_virtual


@pytest.mark.usefixtures("class_guest_register")
@pytest.mark.usefixtures("function_virtwho_d_conf_clean")
@pytest.mark.usefixtures("class_debug_true")
@pytest.mark.usefixtures("class_globalconf_clean")
class TestUpgrade:
    def test_pre_upgrade(self, virtwho, sm_guest, rhsm, satellite, hypervisor_data, vdc_pool_physical):
        """Pre-upgrade test cases for virt-who

        :title: virt-who: upgrade : pre-upgrade test cases for virt-who
        :id: 97e5f32d-7d56-4be1-97b3-c368519cd448
        :caseimportance: High
        :tags: upgrade
        :customerscenario: false
        :upstream: no
        :steps:
            1. Create the virt-who config files for the multi hypervisors list
            2. Run the virt-who service

        :expectedresults:
            1. Succeed to run the virt-who, no error messages in the rhsm.log
        """

        for mode in hypervisors_list():
            hypervisor_create(mode)
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

        # Configure global options by /etc/virt-who.conf ann /etc/sysconfig/virtwho

        # attach physcial vdc for hypervisor
        hypervisor_hostname = hypervisor_data["hypervisor_hostname"]
        if REGISTER == "rhsm":
            rhsm.attach(host_name=hypervisor_hostname, pool=vdc_pool_physical)
        else:
            satellite.attach(host=hypervisor_hostname, pool=vdc_pool_physical)

        # attach virtual vdc pool for guest by pool id
        sm_guest.refresh()
        sku_data_virt = sm_guest.available(vdc_virtual_sku, "Virtual")
        sm_guest.attach(pool=sku_data_virt["pool_id"])
        consumed_data = sm_guest.consumed(sku_id=vdc_virtual_sku)

        assert (
            consumed_data["sku"] == vdc_virtual_sku
            and consumed_data["sku_type"] == "Virtual"
            and consumed_data["temporary"] is False
        )

    def test_post_upgrade(self, virtwho, sm_guest, hypervisor_data, vdc_pool_physical):
        """Post-upgrade test cases for virt-who

        :title: virt-who: upgrade : post-upgrade test cases for virt-who
        :id: 40db5c14-1c86-4371-b9f7-89b00612cb96
        :caseimportance: High
        :tags: upgrade
        :customerscenario: false
        :upstream: no
        :steps:
            1. Create the virt-who config files for the multi hypervisors list
            2. Run the virt-who service

        :expectedresults:
            1. Succeed to run the virt-who, no error messages in the rhsm.log
        """
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1

        # Check all the configurations in /etc/virt-who.conf
        # and /etc/sysconfig/virt-who still exist

        # Check the /etc/virt-who.d/virtwho.conf file still exists

        consumed_data = sm_guest.consumed(sku_id=vdc_virtual_sku)
        assert (
            consumed_data["sku"] == vdc_virtual_sku
            and consumed_data["sku_type"] == "Virtual"
            and consumed_data["temporary"] is False
        )
