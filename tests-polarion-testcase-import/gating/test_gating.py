"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho import logger


@pytest.mark.usefixtures('globalconf_clean')
@pytest.mark.usefixtures('hypervisor_create')
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
        assert (result['send'] == 1
                and result['error'] == 0
                and result['debug'] is False)

        result = virtwho.run_cli(debug=True)
        assert (result['send'] == 1
                and result['error'] == 0
                and result['debug'] is True)

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
        assert (result['send'] == 1
                and result['error'] == 0
                and result['thread'] == 1
                and result['terminate'] == 0
                and result['oneshot'] is False)

        result = virtwho.run_cli(oneshot=True)
        assert (result['send'] == 1
                and result['error'] == 0
                and result['thread'] == 0
                and result['terminate'] == 1
                and result['oneshot'] is True)

    def test_interval(self, virtwho, globalconf, global_debug_true):
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
        assert (result['send'] == 1
                and result['interval'] == 3600)

        globalconf.update('global', 'interval', '10')
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['interval'] == 3600)

        globalconf.update('global', 'interval', '60')
        result = virtwho.run_service(wait=60)
        assert (result['send'] == 1
                and result['interval'] == 60
                and result['loop'] == 60)

    def test_hypervisor_id(self, virtwho, hypervisor, hypervisor_data, hypervisor_handler):
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
        hypervisor.update('hypervisor_id', 'uuid')
        result = virtwho.run_cli()
        id_1 = result['hypervisor_id']
        id_2 = hypervisor_data['hypervisor_uuid']
        assert (result['send'] == 1
                and
                result['hypervisor_id'] == hypervisor_data['hypervisor_uuid'])

        hypervisor.update('hypervisor_id', 'hostname')
        result = virtwho.run_cli()
        assert (result['send'] == 1
                and
                result['hypervisor_id'] == hypervisor_data['hypervisor_hostname'])

        if hypervisor_handler in ['esx', 'rhevm']:
            hypervisor.update('hypervisor_id', 'hwuuid')
            result = virtwho.run_cli()
            assert (result['send'] == 1
                    and
                    result['hypervisor_id'] == hypervisor_data['hypervisor_hwuuid'])

    # def host_guest_association_in_mapping(self):
    #     pass

    # def test_vdc_bonus_pool(self, virtwho, sm_guest, register):
    #     """Test the vdc subscription can be derive bonus pool for guest using
    #
    #     :title: virt-who: gating: test the derived vdc virtual bonus pool
    #     :id: 03b79c0b-8b1f-4f32-8285-370773b7124b
    #     :caseimportance: High
    #     :tags: gating
    #     :customerscenario: false
    #     :upstream: no
    #     :steps:
    #
    #         1. Register guest to entitlement server
    #         2. Run virt-who to report mappings to entitlement server
    #         3. Attach physical vdc for hypervisor
    #         4. Check and attach virtual bonus pool for guest
    #
    #     :expectedresults:
    #
    #         1. Attach vdc physical pool for hypervisor successfully
    #         2. Virtual bonus vdc pool is created
    #         3. Guest can subscribe the bonus vdc pool
    #     """
    #     sm_guest.register()
    #
    #     result = virtwho.run_cli()
    #     assert (result['send'] == 1)
    #
    #     register.attach()
