from virtwho.runner import Runner
from virtwho.configure import VirtwhoGlobalConfig
from virtwho.logger import getLogger

logger = getLogger(__name__)

hypervisor = 'esx'
register_type = 'satellite'
globalconfig = VirtwhoGlobalConfig(hypervisor)
runner = Runner(hypervisor, register_type)


class TestConfig:

    @classmethod
    def setup_class(cls):
        globalconfig.initiate()

    def teardown(self):
        globalconfig.initiate()

    def test_debug_in_config(self):
        """test the debug option
        """

        # test debug=0, debug=False and debug=
        debug_values = ['0', 'False', '']
        for value in debug_values:
            globalconfig.update('global', 'debug', f'{value}')
            tty_output = runner.run_virtwho_cli(debug=False)
            assert runner.log_analyzer(tty_output)
            assert runner.msg_search(tty_output, "\\[.*DEBUG\\]") is False

        # test debut=1, debug=True, and debug=true
        debug_values = ['1', 'True', 'true']
        for value in debug_values:
            globalconfig.update('global', 'debug', f'{value}')
            tty_output = runner.run_virtwho_cli(debug=False)
            assert runner.log_analyzer(tty_output)
            assert runner.msg_search(tty_output, "\\[.*DEBUG\\]") is True

    def test_oneshot_in_cconfig(self):
        """test the oneshot function
        """
        # test oneshot=0, oneshot=False and oneshot=
        oneshot_values = ['0', 'False', '']
        for value in oneshot_values:
            globalconfig.update('global', 'oneshot', f'{value}')
            tty_output = runner.run_virtwho_cli(oneshot=False)
            assert runner.log_analyzer(tty_output)
            assert runner.msg_search(tty_output, "virt-who terminated") is False

        # test oneshot=1, oneshot=True and oneshot=true
        oneshot_values = ['1', 'True', 'true']
        for value in oneshot_values:
            globalconfig.update('global', 'oneshot', f'{value}')
            tty_output = runner.run_virtwho_cli(oneshot=False)
            assert runner.log_analyzer(tty_output)
            assert runner.msg_search(tty_output, "virt-who terminated") is True

    def test_interval_in_config(self):
        """test the interval functions
        """

        # test interval=
        globalconfig.update('global', 'interval', '')
        tty_output = runner.run_virtwho_cli(oneshot=False, interval=None)
        assert runner.log_analyzer(tty_output, interval_time=3600)

        # test interval=10
        globalconfig.update('global', 'interval', '10')
        tty_output = runner.run_virtwho_cli(oneshot=False, interval=None)
        assert runner.log_analyzer(tty_output, interval_time=3600)

        # test interval=60
        globalconfig.update('global', 'interval', '60')
        tty_output = runner.run_virtwho_cli(oneshot=False, interval=None)
        assert runner.log_analyzer(tty_output, interval_time=60, loop_time=60)
