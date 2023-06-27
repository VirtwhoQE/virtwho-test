"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""
import time
import pytest
from virtwho.base import msg_search
from virtwho.settings import config
from virtwho import HYPERVISOR, FAKE_CONFIG_FILE
from virtwho.configure import hypervisor_create
from virtwho.configure import get_hypervisor_handler
from virtwho.register import SubscriptionManager, Satellite

vdc_physical_sku = config.sku.vdc
vdc_virtual_sku = config.sku.vdc_virtual
limit_sku = config.sku.limit

activation_key = config.satellite.activation_key
default_org = config.satellite.default_org
second_org = config.satellite.secondary_org

hypervisor_handler = get_hypervisor_handler(HYPERVISOR)


@pytest.mark.usefixtures("module_satellite_sca_recover")
@pytest.mark.usefixtures("class_hypervisor")
@pytest.mark.usefixtures("class_virtwho_d_conf_clean")
@pytest.mark.usefixtures("class_globalconf_clean")
@pytest.mark.usefixtures("function_guest_unattach")
@pytest.mark.usefixtures("class_guest_register")
@pytest.mark.usefixtures("function_host_register_for_local_mode")
@pytest.mark.usefixtures("class_satellite_sca_disable")
class TestSatelliteScaDisable:
    @pytest.mark.tier1
    def test_vdc_virtual_pool_attach_by_poolId(
        self, virtwho, sm_guest, satellite, hypervisor_data, vdc_pool_physical
    ):
        """Test the guest can get and attach the virtual vdc pool by pool id

        :title: virt-who: satellite: [sca/disable] test guest attach virtual vdc pool by pool id
        :id: 38e213ef-70cc-445a-85b2-8f9639064f12
        :caseimportance: High
        :tags: subscription,satellite,tier1
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

        # remove the physical vdc from hypervisor
        satellite.unattach(host=hypervisor_hostname, pool=vdc_pool_physical)
        sm_guest.refresh()
        consumed_data = sm_guest.consumed(sku_id=vdc_virtual_sku)
        assert consumed_data is None

    @pytest.mark.tier1
    def test_vdc_virtual_pool_attach_by_auto(
        self, virtwho, sm_guest, satellite, hypervisor_data, vdc_pool_physical
    ):
        """Test the guest can get and attach the virtual vdc pool by auto

        :title: virt-who: satellite: [sca/disable] test guest attach virtual vdc pool by auto
        :id: 812aac00-5b4d-4307-bb4e-bdd774330128
        :caseimportance: High
        :tags: subscription,satellite,tier1
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
        satellite.attach(host=hypervisor_hostname, pool=vdc_pool_physical)

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
        satellite.host_delete(host=hypervisor_hostname)
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
        satellite,
        hypervisor_data,
        vdc_pool_physical,
    ):
        """Test the temporary vdc pool in guest

        :title: virt-who: satellite: [sca/disable] test temporary vdc pool in guest
        :id: 733ce7d0-bb51-4d80-87cc-a5ee5fbdf542
        :caseimportance: High
        :tags: subscription,satellite,tier1
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
            3. The guest repo status is "no repositories available"
            4. The guest subscription status is "Overall Status: Current"
        """
        hypervisor_hostname = hypervisor_data["hypervisor_hostname"]

        virtwho.stop()
        satellite.host_delete(host=hypervisor_hostname)

        sm_guest.refresh()
        available_data_virt = sm_guest.available(vdc_virtual_sku, "Virtual")
        sm_guest.attach(pool=available_data_virt["pool_id"])
        consumed_data = sm_guest.consumed(sku_id=vdc_virtual_sku)
        assert (
            consumed_data["sku"] == vdc_virtual_sku
            and consumed_data["sku_type"] == "Virtual"
            and consumed_data["temporary"] is True
        )

        if HYPERVISOR == "local":
            sm_host.register()
        _ = virtwho.run_cli()
        satellite.attach(host=hypervisor_hostname, pool=vdc_pool_physical)

        sm_guest.refresh()
        consumed_data = sm_guest.consumed(sku_id=vdc_virtual_sku)
        assert (
            consumed_data["sku"] == vdc_virtual_sku
            and consumed_data["sku_type"] == "Virtual"
            and consumed_data["temporary"] is False
        )

        # check repo status in guest
        _, output = ssh_guest.runcmd("subscription-manager repos --list")
        assert msg_search(output, "no repositories available")

        # check subscription status in guest
        _, output = ssh_guest.runcmd("subscription-manager status")
        assert msg_search(output, "Overall Status: Current") and not msg_search(
            output, "Invalid"
        )

    @pytest.mark.tier1
    def test_vdc_virtual_pool_attach_in_fake_mode(
        self, virtwho, sm_guest, satellite, hypervisor_data, vdc_pool_physical
    ):
        """Test the guest can get and attach the virtual vdc pool in fake mode

        :title: virt-who: satellite: [sca/disable] test guest attach virtual vdc pool in fake mode
        :id: 164f2d20-d357-4f25-a0e4-f5260012a266
        :caseimportance: High
        :tags: subscription,satellite,tier1
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
            satellite.host_delete(host=hypervisor_hostname)

        _ = virtwho.run_cli(prt=True)
        _ = hypervisor_create(
            mode="fake", register_type="satellite", config_name=FAKE_CONFIG_FILE
        )
        result = virtwho.run_cli(config=FAKE_CONFIG_FILE)
        assert result["send"] == 1 and result["error"] == 0

        # attach vdc for hypervisor
        satellite.attach(host=hypervisor_hostname, pool=vdc_pool_physical)

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
        satellite.host_delete(host=hypervisor_hostname)
        sm_guest.refresh()
        consumed_data = sm_guest.consumed(sku_id=vdc_virtual_sku)
        assert consumed_data is None

    @pytest.mark.tier2
    def test_guest_auto_attach_rule_by_activation_key(
        self,
        virtwho,
        sm_guest_ack,
        satellite,
        hypervisor_data,
        register_data,
        vdc_pool_physical,
    ):
        """Test the guest register by activation_key

        :title: virt-who: satellite: [sca/disable] test guest attach rule by activation_key
        :id: 6d0e169c-74a7-41a0-a97a-81e084f0aabf
        :caseimportance: High
        :tags: subscription,satellite,tier2
        :customerscenario: false
        :upstream: no
        :steps:

            1. Create a clean activation key
            2. (Scenario 1) Register guest by activation key with
                activation key auto-attach disabled and
                both the virtual limit and vdc sku out of the key
            3. (Scenario 2) Register guest by activation key with
                activation key auto-attach disabled and
                both the virtual limit and vdc sku in the key
            4. (Scenario 3) Register guest by activation key with
                activation key auto-attach enabled and
                virtual limit sku in the key, virtual vdc sku out of the key
            5. (Scenario 4) Register guest by activation key with
                activation key auto-attach enabled and
                both the vdc and limit virt sku out of the key

        :expectedresults:

            1. (Scenario 1) guest will not auto attach any sku
            2. (Scenario 2) guest will auto attach all the matched sku
            3. (Scenario 3) guest will only auto attach the virtual sku that
                in the key
            4. (Scenario 4) guest will auto attach the matched sku from out of
                the key
        """
        hypervisor_hostname = hypervisor_data["hypervisor_hostname"]
        limit_pool_physical = sm_guest_ack.pool_id_get(limit_sku, "Physical")

        # create a clean activation key
        satellite.activation_key_delete(activation_key)
        satellite.activation_key_create(activation_key)

        # disable the auto-attach for activation key
        satellite.activation_key_update(auto_attach="no")

        # register guest by activation key with
        # activation key auto-attach disabled and
        # both the virtual limit and vdc sku out of the key
        # behavior: guest will not auto-attach any one
        _ = virtwho.run_cli()
        satellite.attach(host=hypervisor_hostname, pool=vdc_pool_physical)
        satellite.attach(host=hypervisor_hostname, pool=limit_pool_physical)
        sm_guest_ack.unregister()
        sm_guest_ack.register()
        vdc_consumed_data = sm_guest_ack.consumed(vdc_virtual_sku, "Virtual")
        limit_consumed_data = sm_guest_ack.consumed(limit_sku, "Virtual")
        assert not vdc_consumed_data and not limit_consumed_data

        # get the vdc and limit sku virtual pool id
        vdc_available_data = sm_guest_ack.available(vdc_virtual_sku, "Virtual")
        vdc_virt_pool = vdc_available_data["pool_id"]
        limit_available_data = sm_guest_ack.available(limit_sku, "Virtual")
        limit_virt_pool = limit_available_data["pool_id"]

        # register guest by activation key with
        # activation key auto-attach disabled and
        # both the virtual limit and vdc sku in the key
        # behavior: guest will auto-attach the both one
        satellite.activation_key_attach(pool=vdc_virt_pool, key=activation_key)
        satellite.activation_key_attach(pool=limit_virt_pool, key=activation_key)
        sm_guest_ack.unregister()
        sm_guest_ack.register()
        vdc_consumed_data = sm_guest_ack.consumed(vdc_virtual_sku, "Virtual")
        limit_consumed_data = sm_guest_ack.consumed(limit_sku, "Virtual")
        assert vdc_consumed_data and limit_consumed_data

        # enable the auto-attach for activation key
        satellite.activation_key_update(auto_attach="yes")

        # register guest by activation key with
        # activation key auto-attach enabled and
        # virtual limit sku in the key, virtual vdc sku out of the key
        # behavior: guest will auto-attach the limit virtual sku
        satellite.activation_key_unattach(pool=vdc_virt_pool, key=activation_key)
        sm_guest_ack.unregister()
        sm_guest_ack.register()
        vdc_consumed_data = sm_guest_ack.consumed(vdc_virtual_sku, "Virtual")
        limit_consumed_data = sm_guest_ack.consumed(limit_sku, "Virtual")
        assert limit_consumed_data and not vdc_consumed_data

        # register guest by activation key with
        # activation key auto-attach enabled and
        # the both vdc and limit virt sku out of the key
        # behavior: guest will auto-attach the best matched sku
        satellite.activation_key_unattach(pool=limit_virt_pool, key=activation_key)
        sm_guest_ack.unregister()
        sm_guest_ack.register()
        vdc_consumed_data = sm_guest_ack.consumed(vdc_virtual_sku, "Virtual")
        limit_consumed_data = sm_guest_ack.consumed(limit_sku, "Virtual")
        assert (vdc_consumed_data and not limit_consumed_data) or (
            not vdc_consumed_data and limit_consumed_data
        )

    @pytest.mark.tier2
    def test_guest_auto_attach_temporary_pool_by_activation_key(
        self, virtwho, sm_guest_ack, satellite, hypervisor_data, sm_host
    ):
        """Test the guest can auto attach temporary sku when registering with
            activation key

        :title: virt-who: satellite: [sca/disable] test guest auto attach temporay sku with activation key
        :id: ae58e185-3e78-4c3d-90fb-c5bd1ff01382
        :caseimportance: Medium
        :tags: subscription,satellite,tier2
        :customerscenario: false
        :upstream: no
        :steps:

            1. Create a clean activation key
            2. Unregister/delete the hypervisor from satellite
            3. Register guest with activation key to check comsumed status
            4. Run virt-who to report mappings to satellite
            5. Check the guest consumed status again

        :expectedresults:

            1. Guest can auto attach temporary sku with register with
                activation key.
            2. After guest is associated to hypervisor, the temporary sku will
                change to stable by auto.
        """
        hypervisor_hostname = hypervisor_data["hypervisor_hostname"]
        satellite.host_delete(host=hypervisor_hostname)

        # create a clean activation key
        satellite.activation_key_delete(activation_key)
        satellite.activation_key_create(activation_key)
        satellite.activation_key_update(auto_attach="yes")

        sm_guest_ack.unregister()
        sm_guest_ack.register()
        consumed_data_vdc = sm_guest_ack.consumed(vdc_virtual_sku)
        consumed_data_limit = sm_guest_ack.consumed(limit_sku)
        consumed_data_1 = consumed_data_vdc
        if consumed_data_limit is not None:
            consumed_data_1 = consumed_data_limit
        assert consumed_data_1["temporary"] is True

        if HYPERVISOR == "local":
            sm_host.register()
        _ = virtwho.run_cli()
        sm_guest_ack.refresh()
        consumed_data_vdc = sm_guest_ack.consumed(vdc_virtual_sku)
        consumed_data_limit = sm_guest_ack.consumed(limit_sku)
        consumed_data_2 = consumed_data_vdc
        if consumed_data_limit is not None:
            consumed_data_2 = consumed_data_limit
        assert consumed_data_2["temporary"] is False

    @pytest.mark.tier2
    @pytest.mark.notLocal
    def test_non_default_org_with_rhsm_options(
        self,
        virtwho,
        satellite,
        satellite_second_org,
        hypervisor_data,
        sm_guest_second_org,
        class_hypervisor,
        sku_data,
    ):
        """

        :title: virt-who: satellite: [sca/disable] test non-default org with rhsm options
        :id: c372adf9-645e-4b79-9bcd-af462e5be03a
        :caseimportance: High
        :tags: subscription,satellite,tier2
        :customerscenario: false
        :upstream: no
        :steps:

            1. define virt-who configure file with all rhsm options
            2. define the owner= to the non-default org
            3. run virt-who to report mappings to the non-default org
            4. register guest to the non-default org
            5. attach physical vdc to the hypervisor
            6. attach the bonus virtual vdc to the guest

        :expectedresults:

            1. virt-who can report mappings to the non-default org
            2. in non-default org, hypervisor can deprecate bonus virtual vdc
                for guest
        """
        hypervisor_hostname = hypervisor_data["hypervisor_hostname"]
        try:
            guest_id = hypervisor_data["guest_uuid"]
            satellite.host_delete(host=hypervisor_hostname)

            class_hypervisor.update("owner", second_org)
            result = virtwho.run_cli()
            mappings = result["mappings"]
            assert (
                result["error"] == 0
                and result["send"] == 1
                and guest_id in mappings[second_org]
            )

            satellite.sca(org=sm_guest_second_org.org, sca="disable")
            sm_guest_second_org.register()
            vdc_sku_id = sku_data["vdc_physical"]
            vdc_pool_id = sm_guest_second_org.pool_id_get(vdc_sku_id, "Physical")
            # attach physcial vdc for hypervisor
            satellite_second_org.attach(host=hypervisor_hostname, pool=vdc_pool_id)

            # attach virtual vdc pool for guest by pool id
            sm_guest_second_org.refresh()
            sku_data_virt = sm_guest_second_org.available(vdc_virtual_sku, "Virtual")
            sm_guest_second_org.attach(pool=sku_data_virt["pool_id"])
            consumed_data = sm_guest_second_org.consumed(sku_id=vdc_virtual_sku)
            assert (
                consumed_data["sku"] == vdc_virtual_sku
                and consumed_data["sku_type"] == "Virtual"
                and consumed_data["temporary"] is False
            )

        finally:
            class_hypervisor.update("owner", default_org)
            satellite_second_org.host_delete(host=hypervisor_hostname)

    @pytest.mark.tier2
    @pytest.mark.notLocal
    def test_non_default_org_without_rhsm_options(
        self,
        virtwho,
        satellite,
        satellite_second_org,
        function_hypervisor,
        hypervisor_data,
        sm_host,
        sm_guest_second_org,
        sku_data,
    ):
        """

        :title: virt-who: satellite: [sca/disable] test the non-default org without rhsm options
        :id: e6702ccb-d0ad-4215-9503-cf973c14b31c
        :caseimportance: High
        :tags: subscription,satellite,tier2
        :customerscenario: false
        :upstream: no
        :steps:

            1. define virt-who configure file without rhsm option
            2. register virt-who host to the non-default org
            3. define the owner= to the non-default org
            4. run virt-who to report mappings to the non-default org
            5. register guest to the non-default org
            6. attach physical vdc to the hypervisor
            7. attach the bonus virtual vdc to the guest

        :expectedresults:

            1. virt-who can report mappings to the non-default org
            2. in non-default org, hypervisor can deprecate bonus virtual vdc
                for guest
        """
        hypervisor_hostname = hypervisor_data["hypervisor_hostname"]
        guest_id = hypervisor_data["guest_uuid"]
        try:
            function_hypervisor.create(rhsm=False)
            sm_host.register()
            satellite.host_delete(host=hypervisor_hostname)

            function_hypervisor.update("owner", second_org)
            result = virtwho.run_cli()
            mappings = result["mappings"]
            assert (
                result["error"] == 0
                and result["send"] == 1
                and guest_id in mappings[second_org]
            )

            satellite.sca(org=sm_guest_second_org.org, sca="disable")
            sm_guest_second_org.register()
            vdc_sku_id = sku_data["vdc_physical"]
            vdc_pool_id = sm_guest_second_org.pool_id_get(vdc_sku_id, "Physical")
            # attach physcial vdc for hypervisor
            satellite_second_org.attach(host=hypervisor_hostname, pool=vdc_pool_id)

            # attach virtual vdc pool for guest by pool id
            sm_guest_second_org.refresh()
            sku_data_virt = sm_guest_second_org.available(vdc_virtual_sku, "Virtual")
            sm_guest_second_org.attach(pool=sku_data_virt["pool_id"])
            consumed_data = sm_guest_second_org.consumed(sku_id=vdc_virtual_sku)
            assert (
                consumed_data["sku"] == vdc_virtual_sku
                and consumed_data["sku_type"] == "Virtual"
                and consumed_data["temporary"] is False
            )

        finally:
            function_hypervisor.create(rhsm=True)
            satellite_second_org.host_delete(host=hypervisor_hostname)

    @pytest.mark.tier2
    def test_vdc_virtual_subscription_on_webui(
        self, virtwho, sm_guest, satellite, hypervisor_data, vdc_pool_physical
    ):
        """Test the virtual vdc content subscriptions on satellite webui

        :title: virt-who: satellite: [sca/disable] test vdc virtual subscriptions on webui
        :id: 5c71d37c-b5e2-4789-87f6-24357a96819b
        :caseimportance: Medium
        :tags: subscription,satellite,tier2
        :customerscenario: false
        :upstream: no
        :steps:

            1. Register guest to entitlement server
            2. Attach physical vdc pool to hypervisor
            3. Check the virtual vdc subscription
            4. Attach virtual vdc pool to sm
            5. Check the virtual vdc subscription again

        :expectedresults:

            1. When guest doesn't attach any virtual vdc, the subscription
                consumed number is 0
            2. When guest attached virtual vdc, the subscription consumed number
                will not be 0
        """
        hypervisor_hostname = hypervisor_data["hypervisor_hostname"]
        if HYPERVISOR == "local":
            hypervisor_name = [f"{hypervisor_hostname}"]
        else:
            key = f"virt-who-{hypervisor_hostname}"
            hypervisor_name = [key, key.lower()]

        # check the subscription without virtual vdc pool attached for guest
        if HYPERVISOR != "local":
            satellite.host_delete(host=hypervisor_hostname)
        _ = virtwho.run_cli()
        satellite.attach(host=hypervisor_hostname, pool=vdc_pool_physical)
        vdc_virt_data = sm_guest.available(vdc_virtual_sku, "Virtual")
        vdc_virt_pool = vdc_virt_data["pool_id"]
        subscription = satellite.subscription_on_webui(vdc_virt_pool)
        assert (
            subscription["type"] == "STACK_DERIVED"
            and subscription["virt_only"] is True
            and any(
                key in subscription["hypervisor"]["name"] for key in hypervisor_name
            )
        )
        assert (
            subscription["available"] == -1
            and subscription["quantity"] == -1
            and subscription["consumed"] == 0
        )

        # check the subscription with virtual vdc pool attached for guest
        sm_guest.refresh()
        sm_guest.attach(pool=vdc_virt_pool)
        for i in range(3):
            time.sleep(30)
            subscription = satellite.subscription_on_webui(vdc_virt_pool)
            assert subscription["consumed"] == 1

    # def test_register_by_item_on_webui(
    #         self, virtwho, sm_guest, satellite, hypervisor_data,
    #         vdc_pool_physical
    # ):
    #     """Test the register_by item on satellite webui
    #
    #     :title: virt-who: satellite: test vdc virtual subscriptions on webui
    #     :id: 9f2f64d5-d5fc-425a-8f11-33a1cadc1acd
    #     :caseimportance: Medium
    #     :tags: subscription,satellite,tier2
    #     :customerscenario: false
    #     :upstream: no
    #     :steps:
    #
    #         1.
    #
    #     :expectedresults:
    #
    #         1.
    #     """
    #     hypervisor_hostname = hypervisor_data['hypervisor_hostname']
    #     guest_hostname = hypervisor_data['guest_hostname']
    #     satellite.host_delete(hypervisor_hostname)
    #
    #     # hypervisor
    #     register_by_exp = 'null'
    #     if HYPERVISOR == 'local':
    #         register_by_exp = 'admin'
    #     _ = virtwho.run_cli()
    #     register_by = satellite.hosts_info_on_webui(hypervisor_hostname)
    #     assert register_by == register_by_exp
    #
    #     # guest
    #     register_by = satellite.hosts_info_on_webui(guest_hostname)
    #     assert register_by == 'admin'


@pytest.mark.usefixtures("module_satellite_sca_recover")
@pytest.mark.usefixtures("class_hypervisor")
@pytest.mark.usefixtures("class_virtwho_d_conf_clean")
@pytest.mark.usefixtures("class_globalconf_clean")
@pytest.mark.usefixtures("function_guest_unattach")
@pytest.mark.usefixtures("class_guest_register")
@pytest.mark.usefixtures("function_host_register_for_local_mode")
@pytest.mark.usefixtures("class_satellite_sca_enable")
class TestSatelliteScaEnable:
    @pytest.mark.tier1
    def test_hypervisor_entitlement_status(
        self, virtwho, hypervisor_data, satellite, vdc_pool_physical
    ):
        """Test the hypervisor entitlement status.

        :title: virt-who: satellite: [sca/enable] test hypervisor entitlement status
        :id: bda68020-b17e-4442-bcfd-91537e9499e1
        :caseimportance: High
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
        :caseimportance: High
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
        msg = "Attaching subscriptions is disabled .* because Simple Content Access .* is enabled."
        assert msg_search(output, msg)

        msg = "This host's organization is in Simple Content Access mode. Attaching subscriptions is disabled."
        result = satellite.attach(host=guest_hostname, pool=vdc_pool_physical)
        assert msg in result


@pytest.fixture(scope="class")
def sm_guest_ack(register_data):
    """
    Instantication of class SubscriptionManager() for hypervisor guest
    with default org and activation key
    """
    port = 22
    if HYPERVISOR == "kubevirt":
        port = hypervisor_handler.guest_port
    return SubscriptionManager(
        host=hypervisor_handler.guest_ip,
        username=hypervisor_handler.guest_username,
        password=hypervisor_handler.guest_password,
        port=port,
        register_type="satellite",
        org=config.satellite.default_org,
        activation_key=register_data["activation_key"],
    )


@pytest.fixture(scope="class")
def sm_guest_second_org(register_data):
    """
    Instantication of class SubscriptionManager() for hypervisor guest
    with the second org
    """
    port = 22
    if HYPERVISOR == "kubevirt":
        port = hypervisor_handler.guest_port
    return SubscriptionManager(
        host=hypervisor_handler.guest_ip,
        username=hypervisor_handler.guest_username,
        password=hypervisor_handler.guest_password,
        port=port,
        register_type="satellite",
        org=second_org,
    )


@pytest.fixture(scope="session")
def satellite_second_org():
    """Instantication of class Satellite() with the second org"""
    return Satellite(
        server=config.satellite.server,
        org=config.satellite.secondary_org,
        activation_key=config.satellite.activation_key,
    )


# used by the draft case 'test_register_by_item_on_webui'
# def host_register_by_on_webui(satellite, host):
#     host_info = satellite.hosts_info_on_webui(host)
#     if host_info:
#         register_by = host_info['subscription_facet_attributes']['user']['login']
#         if register_by:
#             return register_by
#     logger.error(f'Failed to get the register_by value for {host}')
#     return None


@pytest.fixture(scope="class")
def class_satellite_sca_disable(satellite):
    """Disable sca mode for default org"""
    satellite.sca(org=None, sca="disable")


@pytest.fixture(scope="class")
def class_satellite_sca_enable(satellite):
    """Enable sca mode for default org"""
    satellite.sca(org=None, sca="enable")


@pytest.fixture(scope="module")
def module_satellite_sca_recover(satellite):
    """Recover the sca mode for default org as configuration in virtwho.ini."""
    yield
    satellite.sca(org=None, sca=config.job.sca)
