"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho import logger


@pytest.mark.usefixtures('globalconf_clean')
@pytest.mark.usefixtures('hypervisor_create')
class TestConfiguration:
    @pytest.mark.tier1
    def test_debug_in_virtwho_conf(self, virtwho, globalconf):
        """Just a demo

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
            2. [DEBUG] logs are printed with "-d" option
        """
        globalconf.update('global', 'debug', 'True')
        result = virtwho.run_cli(debug=False)
        assert (result['send'] == 1
                and result['error'] == 0
                and result['debug'] is True)

        globalconf.update('global', 'debug', 'False')
        result = virtwho.run_cli(debug=False)
        assert (result['send'] == 1
                and result['error'] == 0
                and result['debug'] is False)

    @pytest.mark.tier2
    def test_interval_in_virtwho_conf(self):
        """Just a demo

        :title: virt-who: config: test interval option
        :id: f1d39429-62c0-44f0-a6d3-4ffc8dc704b1
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        logger.info("Succeeded to run the 'test_interval_in_virtwho_conf'")

    @pytest.mark.tier3
    def test_oneshot_in_virtwho_conf(self):
        """Just a demo

        :title: virt-who: config: test oneshot option
        :id: 15b45691-7358-4bc8-b49f-f87100bded1b
        :caseimportance: High
        :tags: tier3
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        logger.info("Succeeded to run the 'test_oneshot'")
