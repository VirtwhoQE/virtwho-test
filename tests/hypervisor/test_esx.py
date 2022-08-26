"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho import logger
from virtwho import REGISTER
from virtwho import RHEL_COMPOSE
from virtwho import HYPERVISOR
from virtwho.configure import VirtwhoHypervisorConfig


@pytest.mark.usefixtures('debug_true')
@pytest.mark.usefixtures('hypervisor_create')
@pytest.mark.usefixtures('globalconf_clean')
@pytest.mark.usefixtures('virtwho_d_conf_clean')
class TestEsx:
    @pytest.mark.tier2
    def test_type(self, virtwho, hypervisor, hypervisor_data):
        """Test the type= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test type option
        :id: 0f2fcf4f-ac60-4c3c-905a-fabe22536ab2
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        # # # type option is wrong value
        # validate_values = ['xxx', '红帽€467aa', '']
        # for value in validate_values:
        #     hypervisor.update('type', value)
        #     result = virtwho.run_service()
        #     assert (result['error'] is not 0
        #             and result['send'] == 0
        #             and result['thread'] == 0)
        #     if 'RHEL-9' in RHEL_COMPOSE:
        #         assert f"Unsupported virtual type '{value}' is set" in result['error_msg']
        #     else:
        #         assert "virt-who can't be started" in result['error_msg']

        # type option is disable
        hypervisor.delete('type')
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 0
                and result['thread'] == 1
                and 'Error in libvirt backend' in result['error_msg'])

        # # type option is disable but another config is ok
        new_file = '/etc/virt-who.d/new_config.conf'
        section_name = 'virtwho-config'
        new_hypervisor = VirtwhoHypervisorConfig(HYPERVISOR, REGISTER, new_file, section_name)
        new_hypervisor.create()
        result = virtwho.run_service()
        assert (result['error'] is not 0
                and result['send'] == 1
                and result['thread'] == 1
                and 'Error in libvirt backend' in result['error_msg'])

        # type option is null but another config is ok
        hypervisor.update('type', '')
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['thread'] == 1)
        if 'RHEL-9' in RHEL_COMPOSE:
            assert result['error'] == 1
        else:
            assert result['error'] == 0


    @pytest.mark.tier2
    def test_server(self, virtwho, hypervisor, hypervisor_data, owner_data):
        """Test the server= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test server option
        :id: 0f2fcf4f-ac60-4c3c-905a-fabe22536ab2
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """



    @pytest.mark.tier1
    def test_hypervisor_id(self, virtwho, hypervisor, hypervisor_data, globalconf, rhsm, satellite):
        """Test the hypervisor_id= option in /etc/virt-who.d/hypervisor.conf

        :title: virt-who: esx: test hypervisor_id function
        :id: be5877d9-3a59-46aa-bd9a-6c1e3ed5f5ee
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. clean all virt-who global configurations
            2. run virt-who with hypervisor_id=uuid
            3. run virt-who with hypervisor_id=hostname
            4. run virt-who with hypervisor_id=hwuuid

        :expectedresults:

            hypervisor id shows uuid/hostname/hwuuid in mapping as the setting.
        """
        hypervisor_ids = ['hostname', 'uuid', 'hwuuid']
        for hypervisor_id in hypervisor_ids:
            hypervisor.update('hypervisor_id', hypervisor_id)
            result = virtwho.run_service()
            assert (result['error'] == 0
                    and result['send'] == 1
                    and result['thread'] == 1
                    and result['hypervisor_id'] == hypervisor_data[f'hypervisor_{hypervisor_id}'])
            if REGISTER == 'rhsm':
                assert rhsm.consumers(hypervisor_data['hypervisor_hostname'])
                rhsm.delete(hypervisor_data['hypervisor_hostname'])
            else:
                if hypervisor_id == 'hostname':
                    assert satellite.host_id(hypervisor_data['hypervisor_hostname'])
                    assert not satellite.host_id(hypervisor_data['hypervisor_uuid'])
                    assert not satellite.host_id(hypervisor_data['hypervisor_hwuuid'])
                elif hypervisor_id == 'uuid':
                    assert satellite.host_id(hypervisor_data['hypervisor_uuid'])
                    assert not satellite.host_id(hypervisor_data['hypervisor_hostname'])
                    assert not satellite.host_id(hypervisor_data['hypervisor_hwuuid'])
                else:
                    assert satellite.host_id(hypervisor_data['hypervisor_hwuuid'])
                    assert not satellite.host_id(hypervisor_data['hypervisor_hostname'])
                    assert not satellite.host_id(hypervisor_data['hypervisor_uuid'])

    def test_hostname_option(self):
        """Just a demo

        :title: virt-who: esx: test hostname option
        :id: fb1f5dec-89c7-41e7-a15b-52b843f6f590
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        logger.info("Succeeded to run the 'test_hostname_option'")

    @pytest.mark.tier2
    def test_http_option(self):
        """Just a demo

        :title: virt-who: esx: test http option
        :id: 37ee22b4-5105-4693-857d-4003715606ef
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        logger.info("Succeeded to run the 'test_http_option'")
