"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho import HYPERVISOR, REGISTER


@pytest.mark.usefixtures("class_globalconf_clean")
@pytest.mark.usefixtures("class_hypervisor")
class TestGating:
    def test_debug(self, virtwho):
        """Test the '-d' option in virt-who command line

        :title: virt-who: gating: test debug function
        :id: 4ba50cb9-c431-4283-bb8c-1d4a8ff0a036
        :caseimportance: High
        :tags: gating
        :customerscenario: false
        :upstream: no
        :steps:

            1. clean all virt-who global configurations
            2. run "#virt-who -c" without "-d"
            3. run "#virt-who -d -c"

        :expectedresults:

            1. no [DEBUG] log printed without "-d" option
            2. [DEBUG] logs are printed with "-d" option
        """
        result = virtwho.run_cli(debug=False)
        assert result["send"] == 1 and result["error"] == 0 and result["debug"] is False

        result = virtwho.run_cli(debug=True)
        assert result["send"] == 1 and result["error"] == 0 and result["debug"] is True

    def test_oneshot(self, virtwho):
        """Test the '-o' option in virt-who command line

        :title: virt-who: gating: test oneshot function
        :id: 2ec0f2c4-9633-48cd-8d61-7872d0e23117
        :caseimportance: High
        :tags: gating
        :customerscenario: false
        :upstream: no
        :steps:

            1. clean all virt-who global configurations
            2. run "#virt-who -c" without "-o"
            3. run "#virt-who -o -c"

        :expectedresults:

            1. virt-who thread is not terminated automatically without "-o"
            2. virt-who thread is terminated after reporting once with "-o"
        """
        result = virtwho.run_cli(oneshot=False)
        assert (
            result["send"] == 1
            and result["error"] == 0
            and result["thread"] == 1
            and result["terminate"] == 0
        )

        result = virtwho.run_cli(oneshot=True)
        assert (
            result["send"] == 1
            and result["error"] == 0
            and result["thread"] == 0
            and result["terminate"] == 1
        )

    def test_interval(self, virtwho, globalconf, class_debug_true):
        """Test the interval option in /etc/virt-who.conf

        :title: virt-who: gating: test interval function
        :id: e226ed41-454d-4855-8c1d-5ab2ba5293e4
        :caseimportance: High
        :tags: gating
        :customerscenario:
        :upstream: no
        :steps:

            1. clean all virt-who global configurations
            2. run virt-who without #interval=
            3. run virt-who with interval=10
            4. run virt-who with interval=60

        :expectedresults:

            1. the default interval=3600 when do not set interval=
            2. the interval=3600 when run with interval < 60
            3. the interval uses the setting value when run with interval >= 60
        """
        result = virtwho.run_service()
        assert result["send"] == 1 and result["interval"] == 3600

        globalconf.update("global", "interval", "10")
        result = virtwho.run_service()
        assert result["send"] == 1 and result["interval"] == 3600

        globalconf.update("global", "interval", "60")
        result = virtwho.run_service(wait=60)
        assert result["send"] == 1 and result["interval"] == 60 and result["loop"] == 60

    def test_hypervisor_id(self, virtwho, class_hypervisor, hypervisor_data):
        """Test the hypervisor_id= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: gating: test hypervisor_id function
        :id: 03b79c0b-8b1f-4f32-8285-370773b7124b
        :caseimportance: High
        :tags: gating
        :customerscenario: false
        :upstream: no
        :steps:

            1. clean all virt-who global configurations
            2. run virt-who with hypervisor_id=uuid
            3. run virt-who with hypervisor_id=hostname
            4. run virt-who with hypervisor_id=hwuuid (Only for esx and rhevm)

        :expectedresults:

            hypervisor id shows uuid/hostname/hwuuid in mapping as the setting.
        """
        try:
            class_hypervisor.update("hypervisor_id", "uuid")
            result = virtwho.run_cli()
            assert (
                result["send"] == 1
                and result["hypervisor_id"] == hypervisor_data["hypervisor_uuid"]
            )

            class_hypervisor.update("hypervisor_id", "hostname")
            result = virtwho.run_cli()
            assert (
                result["send"] == 1
                and result["hypervisor_id"] == hypervisor_data["hypervisor_hostname"]
            )

            if HYPERVISOR in ["esx", "rhevm"]:
                class_hypervisor.update("hypervisor_id", "hwuuid")
                result = virtwho.run_cli()
                assert (
                    result["send"] == 1
                    and result["hypervisor_id"] == hypervisor_data["hypervisor_hwuuid"]
                )
        finally:
            class_hypervisor.update("hypervisor_id", "hostname")

    def test_host_guest_association(self, virtwho, register_data, hypervisor_data):
        """Test the host to guest association from mapping

        :title: virt-who: gating: test host-to-guest association
        :id: a0cd029e-de88-40e6-bbf3-00d2508d20e5
        :caseimportance: High
        :tags: gating
        :customerscenario: false
        :upstream: no
        :steps:

            1. clean all virt-who global configurations
            2. run "virt-who -d" to get mapping
            3. check the host-to-guest mapping correctly

        :expectedresults:

            host associated correctly with guest in mapping.
        """
        guest_uuid = hypervisor_data["guest_uuid"]
        hypervisor_hostname = hypervisor_data["hypervisor_hostname"]
        default_org = register_data["default_org"]
        # assert the association in mapping
        result = virtwho.run_cli()
        assert (
            result["send"] == 1
            and result["error"] == 0
            and virtwho.associate_in_mapping(
                result, default_org, hypervisor_hostname, guest_uuid
            )
        )

    def test_vdc_bonus_pool(
        self,
        virtwho,
        sm_guest,
        function_guest_register,
        satellite,
        rhsm,
        hypervisor_data,
        sku_data,
        vdc_pool_physical,
    ):
        """Test the vdc subscription can derive bonus pool for guest using

        :title: virt-who: gating: test the derived vdc virtual bonus pool
        :id: 03b79c0b-8b1f-4f32-8285-370773b7124b
        :caseimportance: High
        :tags: gating
        :customerscenario: false
        :upstream: no
        :steps:

            1. Register guest to entitlement server
            2. Run virt-who to report mappings to entitlement server
            3. Attach physical vdc for hypervisor
            4. Check and attach virtual bonus pool for guest

        :expectedresults:

            1. Attach vdc physical pool for hypervisor successfully
            2. Virtual bonus vdc pool is created
            3. Guest can subscribe the bonus vdc pool
        """
        sku_virt = sku_data["vdc_virtual"]
        hypervisor_hostname = hypervisor_data["hypervisor_hostname"]
        result = virtwho.run_cli()
        assert result["send"] == 1 and result["error"] == 0

        # attach vdc for hypervisor, guest can get the bonus virtual pool.
        if REGISTER == "rhsm":
            rhsm.attach(host_name=hypervisor_hostname, pool=vdc_pool_physical)
        else:
            satellite.attach(host=hypervisor_hostname, pool=vdc_pool_physical)
        sm_guest.refresh()
        sku_data_virt = sm_guest.available(sku_virt, "Virtual")
        sm_guest.attach(pool=sku_data_virt["pool_id"])
        consumed_data = sm_guest.consumed(sku_id=sku_virt)
        assert (
            consumed_data["sku"] == sku_virt
            and consumed_data["sku_type"] == "Virtual"
            and consumed_data["temporary"] is False
        )
