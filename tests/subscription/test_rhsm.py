"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""
import pytest
from virtwho.base import msg_search
from virtwho.settings import config
from virtwho import HYPERVISOR, FAKE_CONFIG_FILE
from virtwho.configure import hypervisor_create

vdc_physical_sku = config.sku.vdc
vdc_virtual_sku = config.sku.vdc_virtual


@pytest.mark.usefixtures("module_rhsm_sca_recover")
@pytest.mark.usefixtures("class_globalconf_clean")
@pytest.mark.usefixtures("class_hypervisor")
@pytest.mark.usefixtures("class_guest_register")
@pytest.mark.usefixtures("function_guest_unattach")
@pytest.mark.usefixtures("function_host_register_for_local_mode")
@pytest.mark.usefixtures("class_rhsm_sca_disable")
class TestRhsmScaDisable:
    @pytest.mark.tier1
    def test_vdc_virtual_pool_attach_by_poolId(
        self, virtwho, sm_guest, rhsm, hypervisor_data, vdc_pool_physical
    ):
        """Test the guest can get and attach the virtual vdc pool by pool id

        :title: virt-who: rhsm: test guest attach virtual vdc pool by pool id
        :id: 39717357-eadb-4ac7-bf44-2b323cda3717
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Register guest to entitlement server
            2. Run virt-who to report mappings to entitlement server
            3. Attach physical vdc for hypervisor
            4. Check and attach virtual vdc pool for guest by pool id
            5. Remove the physical vdc from hypervisor
            6. Check the consumed status from guest

        :expectedresults:

            1. The hysical vdc pool can derive virtual vdc pool for guest using.
            2. Guest can subscribe the virtual vdc pool by pool id.
            3. The vdc virtual pool disappear in guest after remove the
                physical pool from hypervisor.
        """
        hypervisor_hostname = hypervisor_data["hypervisor_hostname"]
        result = virtwho.run_cli()
        assert result["send"] == 1 and result["error"] == 0

        # attach physcial vdc for hypervisor
        rhsm.attach(host_name=hypervisor_hostname, pool=vdc_pool_physical)

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

        # remove the physical vdc from hypervisor
        rhsm.unattach(host_name=hypervisor_hostname, pool=vdc_pool_physical)
        sm_guest.refresh()
        consumed_data = sm_guest.consumed(sku_id=vdc_virtual_sku)
        assert consumed_data is None

    @pytest.mark.tier1
    def test_vdc_virtual_pool_attach_by_auto(
        self, virtwho, sm_guest, rhsm, hypervisor_data, vdc_pool_physical
    ):
        """Test the guest can get and attach the virtual vdc pool by auto

        :title: virt-who: rhsm: test guest attach virtual vdc pool by auto
        :id: d082e0c1-e925-46ea-8ab1-d65355709f55
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Register guest to entitlement server
            2. Run virt-who to report mappings to entitlement server
            3. Attach physical vdc for hypervisor
            4. Check and attach virtual vdc pool for guest by auto attach
            5. Unregister/delete the hyperviosr from entitlement server
            6. Check the consumed status from guest

        :expectedresults:

            1. The hysical vdc pool can derive virtual vdc pool for guest using.
            2. Guest can subscribe the virtual vdc pool by auto attach.
            3. The vdc virtual pool disappear in guest after unregister the
                hypervisor.
        """
        hypervisor_hostname = hypervisor_data["hypervisor_hostname"]
        result = virtwho.run_cli()
        assert result["send"] == 1 and result["error"] == 0

        # attach physcial vdc for hypervisor
        rhsm.attach(host_name=hypervisor_hostname, pool=vdc_pool_physical)

        # attach virtual vdc pool for guest by auto
        sm_guest.refresh()
        sm_guest.attach(pool=None)
        consumed_data = sm_guest.consumed(sku_id=vdc_virtual_sku)
        assert (
            consumed_data["sku"] == vdc_virtual_sku
            and consumed_data["sku_type"] == "Virtual"
            and consumed_data["temporary"] is False
        )

        # unregister hypervisor
        rhsm.host_delete(host_name=hypervisor_hostname)
        sm_guest.refresh()
        consumed_data = sm_guest.consumed(sku_id=vdc_virtual_sku)
        assert consumed_data is None

    @pytest.mark.tier1
    def test_vdc_temporary_pool_by_poolId(
        self,
        virtwho,
        sm_guest,
        ssh_guest,
        sm_host,
        rhsm,
        hypervisor_data,
        vdc_pool_physical,
    ):
        """Test the temporary vdc pool in guest

        :title: virt-who: rhsm: test temporary vdc pool in guest
        :id: d1c42adf-dee5-42bf-80b6-017948e77baf
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Register guest to entitlement server
            2. Stop the virt-who service
            3. Delete the hypervisor from entitlement server
            4. Attach the vdc virtual pool for guest
            5. Start virt-who service to report mappings to entitlement server
            6. Attach the physical vdc pool for hypervisor
            7. Check the virtual vdc pool status in guest
            8. Check repo status in guest
            9. Check subscription status in guest

        :expectedresults:

            1. The guest can get and attach a temporary virtual vdc when no
                hypervisor associated in the entitlement server
            2. The teporary virtual vdc pool changes to stable one after
                associating again to the hypervisor with the physical vdc pool
                attached
            3. The guest repo status is "Available Repositories"
            4. The guest subscription status is "Overall Status: Current"
        """
        hypervisor_hostname = hypervisor_data["hypervisor_hostname"]
        # delete the host-to-guest association in server
        virtwho.stop()
        rhsm.host_delete(host_name=hypervisor_hostname)

        # attach temporary virtual vdc pool for guest
        sm_guest.refresh()
        sku_data_virt = sm_guest.available(vdc_virtual_sku, "Virtual")
        sm_guest.attach(pool=sku_data_virt["pool_id"])
        consumed_data = sm_guest.consumed(sku_id=vdc_virtual_sku)
        assert (
            consumed_data["sku"] == vdc_virtual_sku
            and consumed_data["sku_type"] == "Virtual"
            and consumed_data["temporary"] is True
        )

        # run virt-who and attach physcial vdc for hypervisor
        if HYPERVISOR == "local":
            sm_host.register()
        _ = virtwho.run_cli()
        rhsm.attach(host_name=hypervisor_hostname, pool=vdc_pool_physical)

        # check the temporary vdc changed to stable one in guest
        sm_guest.refresh()
        consumed_data = sm_guest.consumed(sku_id=vdc_virtual_sku)
        assert (
            consumed_data["sku"] == vdc_virtual_sku
            and consumed_data["sku_type"] == "Virtual"
            and consumed_data["temporary"] is False
        )

        # check repo status in guest
        _, output = ssh_guest.runcmd("subscription-manager repos --list")
        assert msg_search(output, "Available Repositories")

        # check subscription status in guest
        _, output = ssh_guest.runcmd("subscription-manager status")
        assert msg_search(output, "Overall Status: Current") and not msg_search(
            output, "Invalid"
        )

    @pytest.mark.tier1
    @pytest.mark.notRemote
    def test_vdc_physcial_pool_consumed_status_in_physical_host(
        self, sm_host, vdc_pool_physical
    ):
        """Test vdc physcial pool consumed status in physical host when
            set cpu_socket(s).

        :title: virt-who: rhsm: test physcial vdc pool consumed status in
            physical host
        :id: cbf0e07b-c51c-4e6d-9c80-07c2c8dd7692
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Create facts with 'cpu.cpu_socket(s): 4' for physical host
            2. Attach physcial vdc pool for local host with quantity=1
            3. Check the consumed status for host
            4. Remove the consumed pool from host
            5. Attach physcial vdc pool for local host without quantity setting
            6. Check the consumed status for host
            7. Remove the custom facts setting

        :expectedresults:

            1. With cpu_socket(s)=4, the physical host can subscribe only one
                physical vdc pool with status 'Only supports 2 of 4 sockets.'
                because 1 pool can cover 2 sockets
            2. Without quantity setting, the physcial host default to subscribe
                2 vdc pool with status 'Subscription is current'
        """
        try:
            sm_host.facts_create("cpu.cpu_socket(s)", "4")
            sm_host.unattach()
            # Attach physcial vdc pool with quantity=1
            sm_host.attach(pool=vdc_pool_physical, quantity=1)
            consumed_data = sm_host.consumed(
                sku_id=vdc_physical_sku, sku_type="Physical"
            )
            assert (
                consumed_data["quantity_used"] == "1"
                and consumed_data["status_details"] == "Only supports 2 of 4 sockets."
            )

            # Attach physcial vdc pool without quantity setting
            sm_host.unattach()
            sm_host.attach(pool=vdc_pool_physical)
            consumed_data = sm_host.consumed(
                sku_id=vdc_physical_sku, sku_type="Physical"
            )
            assert (
                consumed_data["quantity_used"] == "2"
                and consumed_data["status_details"] == "Subscription is current"
            )

        finally:
            sm_host.facts_remove()

    @pytest.mark.tier1
    def test_vdc_virtual_pool_consumed_status_in_guest(
        self, virtwho, sm_guest, rhsm, hypervisor_data, vdc_pool_physical
    ):
        """Test vdc virtual pool consumed status in guest when
            set cpu_socket(s).

        :title: virt-who: rhsm: test vdc virtual pool consumed status in guest
        :id: 93af0dad-21e6-4732-8a06-2fb2e86a05a3
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:

            1. Register guest to stage account
            2. Create facts with 'cpu.cpu_socket(s): 4' for guest
            3. Run virt-who to report mappings to entitlement server
            4. Attach physical vdc for hypervisor
            5. Attach virtual vdc pool for guest with quantity=1
            6. Check the consumed status for guest
            7. Remove the consumed pool from host
            8. Attach physcial vdc pool for local host with quantity=2
            9. Check the consumed status for guest
            10. Remove the custom facts setting

        :expectedresults:

            1. With cpu_socket(s)=4, the rhel guest can subscribe only one
                virtual vdc pool with status 'Subscription is current.'.
            2. It shows 'Multi-entitlement not supported' when try to attach 2
                virtual vdc for the guest, that is not supported.
        """
        hypervisor_hostname = hypervisor_data["hypervisor_hostname"]
        try:
            sm_guest.facts_create("cpu.cpu_socket(s)", "4")

            rhsm.attach(host_name=hypervisor_hostname, pool=vdc_pool_physical)
            _ = virtwho.run_cli()
            sku_data_virt = sm_guest.available(vdc_virtual_sku, "Virtual")
            sm_guest.attach(pool=sku_data_virt["pool_id"])

            consumed_data = sm_guest.consumed(sku_id=vdc_virtual_sku)
            assert (
                consumed_data["quantity_used"] == "1"
                and consumed_data["status_details"] == "Subscription is current"
            )

            sm_guest.unattach()
            output = sm_guest.attach(pool=sku_data_virt["pool_id"], quantity=2)
            assert "Multi-entitlement not supported" in output

        finally:
            sm_guest.facts_remove()

    @pytest.mark.tier2
    def test_vdc_virtual_pool_attach_in_fake_mode(
        self, virtwho, sm_guest, rhsm, hypervisor_data, vdc_pool_physical
    ):
        """Test the guest can get and attach the virtual vdc pool in fake mode

        :title: virt-who: rhsm: test guest attach virtual vdc pool in fake mode
        :id: f97afcd8-2b23-4754-8c40-a70605009e8f
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:

            1. Register guest to entitlement server
            2. Get fake json with print function
            2. Run virt-who in fake mode to report mappings
            3. Attach physical vdc for hypervisor
            4. Attach virtual vdc pool for guest
            5. Unregister/delte the hyperviosr
            6. Check the consumed status from guest

        :expectedresults:

            1. The physical vdc pool can derive virtual vdc pool for guest using.
            2. Guest can subscribe the virtual vdc pool by auto attach.
            3. The vdc virtual pool disappear in guest after unregister the
                hypervisor.
        """
        hypervisor_hostname = hypervisor_data["hypervisor_hostname"]
        virtwho.stop()
        if HYPERVISOR != "local":
            rhsm.host_delete(host_name=hypervisor_hostname)

        _ = virtwho.run_cli(prt=True)
        _ = hypervisor_create(mode="fake", config_name=FAKE_CONFIG_FILE)
        result = virtwho.run_cli(config=FAKE_CONFIG_FILE)
        assert result["send"] == 1 and result["error"] == 0

        # attach vdc for hypervisor
        rhsm.attach(host_name=hypervisor_hostname, pool=vdc_pool_physical)

        # guest can get the bonus virtual pool.
        sm_guest.refresh()
        sku_data_virt = sm_guest.available(vdc_virtual_sku, "Virtual")
        sm_guest.attach(pool=sku_data_virt["pool_id"])
        consumed_data = sm_guest.consumed(sku_id=vdc_virtual_sku)
        assert (
            consumed_data["sku"] == vdc_virtual_sku
            and consumed_data["sku_type"] == "Virtual"
            and consumed_data["temporary"] is False
        )

        # unregister hypervisor
        rhsm.host_delete(host_name=hypervisor_hostname)
        sm_guest.refresh()
        consumed_data = sm_guest.consumed(sku_id=vdc_virtual_sku)
        assert consumed_data is None


# @pytest.mark.usefixtures("module_rhsm_sca_recover")
# @pytest.mark.usefixtures("class_globalconf_clean")
# @pytest.mark.usefixtures("class_hypervisor")
# @pytest.mark.usefixtures("class_guest_register")
# @pytest.mark.usefixtures("function_guest_unattach")
# @pytest.mark.usefixtures("function_host_register_for_local_mode")
# @pytest.mark.usefixtures("class_rhsm_sca_enable")
# class TestRhsmScaEnable:


@pytest.fixture(scope="class")
def class_rhsm_sca_disable(rhsm):
    """Disable sca mode for stage candlepin"""
    rhsm.sca(sca="disable")


@pytest.fixture(scope="module")
def module_rhsm_sca_recover(rhsm):
    """Recover the sca mode as configuration in virtwho.ini."""
    yield
    rhsm.sca(sca=config.job.sca)
