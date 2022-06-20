"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho.base import hostname_get


@pytest.mark.usefixtures('globalconf_clean')
@pytest.mark.usefixtures('hypervisor_create')
class TestConfiguration:
    @pytest.mark.tier1
    def test_debug_in_virtwho_conf(self, virtwho, globalconf):
        """Test the debug option in /etc/virtwho.conf

        :title: virt-who: config: test debug option
        :id: 6f238133-43db-4a52-b01c-441faba0cf74
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Run virt-who with "debug=True" in [global] section in /etc/virt-who.conf file
            2. Run virt-who with "debug=False" in [global] section in /etc/virt-who.conf file

        :expectedresults:

            1. no [DEBUG] log printed
            2. [DEBUG] logs are printed with the configuration
        """
        globalconf.update('global', 'debug', 'True')
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0
                and result['debug'] is True)

        globalconf.update('global', 'debug', 'False')
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0
                and result['debug'] is False)

    @pytest.mark.tier1
    def test_interval_in_virtwho_conf(self, virtwho, globalconf):
        """Test the interval option in /etc/virtwho.conf

        :title: virt-who: config: test interval option
        :id: f1d39429-62c0-44f0-a6d3-4ffc8dc704b1
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Enable interval and set to 10 in /etc/virt-who.conf
            2. Enable interval and set to 60 in /etc/virt-who.conf
            3. Enable interval and set to 120 in /etc/virt-who.conf
        :expectedresults:

            1. Default value of 3600 seconds will be used when configure lower than 60 seconds
            2. Configure successfully, and virt-who starting infinite loop with 60 seconds interval
            3. Configure successfully, and virt-who starting infinite loop with 120 seconds interval
        """
        globalconf.update('global', 'debug', 'True')
        globalconf.update('global', 'interval', '10')
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0
                and result['interval'] == 3600)

        globalconf.update('global', 'interval', '60')
        result = virtwho.run_service(wait=60)
        assert (result['send'] == 1
                and result['error'] == 0
                and result['loop'] == 60)

    @pytest.mark.tier1
    def test_oneshot_in_virtwho_conf(self, virtwho, globalconf):
        """Test the oneshot option in /etc/virtwho.conf

        :title: virt-who: config: test oneshot option
        :id: 9e39f91f-80b5-4773-bef0-7facf8cb85e2
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Run virt-who with "oneshot=True" in /etc/virt-who.conf
            2. Run virt-who with "oneshot=False" in /etc/virt-who.conf file

        :expectedresults:

            1. Can see 'Thread X stopped after running once' log in rhsm.log
            2. Cannot see 'Thread X stopped after running once' log in rhsm.log
        """
        globalconf.update('global', 'debug', 'True')
        globalconf.update('global', 'oneshot', 'True')
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0
                and result['terminate'] == 1
                and result['oneshot'] is True)

        globalconf.update('global', 'oneshot', 'False')
        result = virtwho.run_service()
        assert (result['send'] == 1
                and result['error'] == 0
                and result['terminate'] == 0
                and result['oneshot'] is False)

    def test_print_in_virtwho_conf(self, virtwho, globalconf, hypervisor_handler):
        """Test the print_ option in /etc/virtwho.conf

        :title: virt-who: config: test print_ option
        :id: 25de8130-677f-43ca-b07d-a15f49e91205
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. Run virt-who with "print_=True" in /etc/virt-who.conf
            2. Run virt-who with "print_=False" in /etc/virt-who.conf

        :expectedresults:

            1. the mappings send number and alive thread number of the virt-who is 0
            2. the mappings send number and alive thread number of the virt-who is 1
        """
        globalconf.update('global', 'print_', 'False')
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1)

        guest_id = hypervisor_handler.guest_uuid
        globalconf.update('global', 'print_', 'True')
        globalconf.update('global', 'debug', 'True')
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 0
                and result['thread'] == 0
                and result['debug'] is True
                and guest_id in result['log'])

        globalconf.update('global', 'print_', 'True')
        globalconf.update('global', 'debug', 'False')
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 0
                and result['thread'] == 0
                and result['debug'] is False
                and guest_id not in result['log'])

    @pytest.mark.usefixtures('hypervisor_data')
    def test_reporter_id_in_virtwho_conf(self, virtwho, globalconf, ssh_host):
        """Test the reporter_id option in /etc/virtwho.conf

        :title: virt-who: config: test reporter_id option
        :id: 83df76e6-27c6-4429-b32b-fbc2be0564a4
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. run virt-who to with default configured
            2. update the reporter_id in /etc/virtwho.conf file and run virt-who

        :expectedresults:

            1. the hostname of the virt-who host shout be included in default reporter_id
            2. the reporter_id should be updated to the setting reporter_id
        """
        virtwho_hostname = hostname_get(ssh_host)
        globalconf.update('global', 'debug', 'True')
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1
                and virtwho_hostname in result['reporter_id'])
        reporter_id = "virtwho_reporter_id"
        globalconf.update('global', 'reporter_id', reporter_id)
        result = virtwho.run_service()
        assert (result['error'] == 0
                and result['send'] == 1
                and result['thread'] == 1
                and result['reporter_id'] == reporter_id)
