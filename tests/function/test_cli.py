from virtwho.runner import Runner
from virtwho.configure import VirtwhoGlobalConfig
from virtwho.logger import getLogger

logger = getLogger(__name__)

hypervisor = 'esx'
register_type = 'satellite'
globalconfig = VirtwhoGlobalConfig(hypervisor)
runner = Runner(hypervisor, register_type)


class TestCli:

    @classmethod
    def setup_class(cls):
        globalconfig.initiate()

    def test_debug_in_cli(self):
        """test the '-d' option in command line
        """

        # run without '-d'
        tty_output = runner.run_virtwho_cli(debug=False)
        assert runner.log_analyzer(tty_output)
        assert runner.msg_search(tty_output, "\\[.*DEBUG\\]") is False

        # run with '-d'
        tty_output = runner.run_virtwho_cli(debug=True)
        assert runner.log_analyzer(tty_output)
        assert runner.msg_search(tty_output, "\\[.*DEBUG\\]") is True

    def test_oneshot_in_cli(self):
        """test the '-o' option in command line
        """

        # run without '-o'
        tty_output = runner.run_virtwho_cli(oneshot=False)
        assert runner.log_analyzer(tty_output)
        assert runner.msg_search(tty_output, "virt-who terminated") is False

        # run with '-o'
        tty_output = runner.run_virtwho_cli(oneshot=True)
        assert runner.log_analyzer(tty_output)
        assert runner.msg_search(tty_output, "virt-who terminated") is True

    def test_interval_in_cli(self):
        """test the '-i ' option in command line
        """

        # run without '-i' to test default interval=3600
        tty_output = runner.run_virtwho_cli(oneshot=False, interval=None)
        assert runner.log_analyzer(tty_output, interval_time=3600)

        # run with '-i 10' and check interval will use default 3600
        tty_output = runner.run_virtwho_cli(oneshot=False, interval=10)
        assert runner.log_analyzer(tty_output, interval_time=3600)

        # run with '-i 60' to test interval=60
        tty_output = runner.run_virtwho_cli(oneshot=False, interval=60, wait=60)
        assert runner.log_analyzer(tty_output, interval_time=60, loop_time=60)

    def test_oneshot_and_interval_in_cli(self):
        pass

    def test_print_in_cli(self):
        pass

    def test_config_in_cli(self):
        pass

    def test_help_in_cli(self):
        pass

    def test_version_in_cli(self):
        pass
