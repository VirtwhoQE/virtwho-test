from virtwho.runner import VirtwhoRunner
from virtwho.configure import VirtwhoGlobalConfig
from virtwho.configure import VirtwhoHypervisorConfig

hypervisor = 'esx'
register_type = 'satellite'
esx = VirtwhoHypervisorConfig('esx', 'satellite')
globalconfig = VirtwhoGlobalConfig(hypervisor)
virtwho = VirtwhoRunner(hypervisor, register_type)


class TestCli:

    @classmethod
    def setup_class(cls):
        globalconfig.initiate()

    def test_debug(self):
        """test the '-d' option in command line
        """

        # run without '-d'
        result = virtwho.run_cli(debug=False)
        assert (result['send'] == 1
                and result['debug'] is False)

        # run with '-d'
        result = virtwho.run_cli(debug=True)
        assert (result['send'] == 1
                and result['debug'] is True)

    def test_oneshot(self):
        """test the '-o' option in command line
        """

        # run without '-o'
        result = virtwho.run_cli(oneshot=False)
        assert (result['send'] == 1
                and result['error'] == 0
                and result['thread'] == 1
                and result['terminate'] == 0
                and result['oneshot'] is False)

        # run with '-o'
        result = virtwho.run_cli(oneshot=True)
        assert (result['send'] == 1
                and result['error'] == 0
                and result['thread'] == 0
                and result['terminate'] == 1
                and result['oneshot'] is True)

    def test_interval(self):
        """test the '-i ' option in command line
        """

        # run without '-i' to test default interval=3600
        result = virtwho.run_cli(oneshot=False, interval=None)
        assert (result['send'] == 1
                and result['interval'] == 3600)

        # run with '-i 10' and check interval will use default 3600
        result = virtwho.run_cli(oneshot=False, interval=10)
        assert (result['send'] == 1
                and result['interval'] == 3600)

        # run with '-i 60' to test interval=60
        result = virtwho.run_cli(oneshot=False, interval=60, wait=60)
        assert (result['send'] == 1
                and result['interval'] == 60
                and result['loop'] == 60)

    def test_print(self):
        guest_id = '42018c62-d744-65bf-0377-9efdac488a57'
        # without debug
        result = virtwho.run_cli(oneshot=False, debug=False, prt=True)
        assert (result['thread'] == 0
                and guest_id in result['print_json'])
        # with debug
        result = virtwho.run_cli(oneshot=False, debug=True, prt=True)
        assert (result['thread'] == 0
                and guest_id in result['print_json'])
