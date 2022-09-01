"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho import HYPERVISOR_FILE


@pytest.mark.usefixtures('globalconf_clean')
@pytest.mark.usefixtures('hypervisor')
class TestCli:
    @pytest.mark.tier1
    def test_debug(self, virtwho):
        """Test the '-d' option in virt-who command line

        :title: virt-who: cli: test option -d
        :id: 9389396f-d4c3-4be2-8aec-a9f7be3d25f1
        :caseimportance: High
        :tags: tier1
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

    @pytest.mark.tier1
    def test_oneshot(self, virtwho):
        """Test the '-o' option in virt-who command line

        :title: virt-who: cli: test option -o
        :id: 6902b844-8b71-490c-abf1-fa6087987666
        :caseimportance: High
        :tags: tier1
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

    @pytest.mark.tier1
    def test_interval(self, virtwho):
        """Test the '-i' option in virt-who command line

        :title: virt-who: cli: test option -i
        :id: e43d9fd0-0f1b-4b25-98f6-c421046e1c47
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. clean all virt-who global configurations
            2. run "#virt-who" without "-i"
            3. run "#virtwho -i 10 -c"
            4. run "#virtwho -i 60 -c"

        :expectedresults:

            1. the default interval=3600 when run without "-i"
            2. the interval=3600 when run with "-i" < 60
            3. the interval uses the setting value when run with "-i" >= 60
        """
        result = virtwho.run_cli(oneshot=False, interval=None)
        assert (result['send'] == 1
                and result['interval'] == 3600)

        result = virtwho.run_cli(oneshot=False, interval=10)
        assert (result['send'] == 1
                and result['interval'] == 3600)

        result = virtwho.run_cli(oneshot=False, interval=60, wait=60)
        assert (result['send'] == 1
                and result['interval'] == 60
                and result['loop'] == 60)

    @pytest.mark.tier1
    def test_print(self, virtwho, hypervisor_data):
        """Test the '-p' option in virt-who command line

        :title: virt-who: cli: test option -p
        :id: 16c01269-f4ab-4fe5-a29e-a3d5dc69a32a
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. clean all virt-who global configurations
            2. run "#virt-who -p -c"
            3. run "#virt-who -p -d -c"

        :expectedresults:

            1. virt-who service is terminated after run with -p
            2. mappings is not reported when run with -p
            3. mappings can be printed out
        """
        guest_id = hypervisor_data['guest_uuid']
        result = virtwho.run_cli(oneshot=False, debug=False, prt=True)
        assert (result['thread'] == 0
                and result['send'] == 0
                and result['debug'] is False
                and guest_id in result['print_json'])

        result = virtwho.run_cli(oneshot=False, debug=True, prt=True)
        assert (result['thread'] == 0
                and result['send'] == 0
                and result['debug'] is True
                and guest_id in result['print_json'])

    @pytest.mark.tier1
    @pytest.mark.notLocal
    def test_config(self, virtwho, ssh_host):
        """Test the '-c' option in virt-who command line

        :title: virt-who: cli: test option -c
        :id: 851a41fd-4fdc-4f8a-ac1b-e185079452fa
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. clean all virt-who global configurations
            2. configure the both /etc/virt-who.d/x.conf and /root/x.conf
            3. run "#virt-who -c /root/x.conf"

        :expectedresults:

            1. virt-who only reports the /root/x.conf
            2. virt-who ignores the files in /etc/virt-who.d/
        """
        msg = "ignoring configuration files in '/etc/virt-who.d/'"
        config_file = '/root/test_cli_config.conf'
        ssh_host.runcmd(f'\\cp -f {HYPERVISOR_FILE} {config_file}')
        result = virtwho.run_cli(config=config_file)
        assert (result['send'] == 1
                and result['error'] == 0
                and msg in result['log'])
