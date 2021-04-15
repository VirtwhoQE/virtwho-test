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
        log = runner.run_virtwho_cli(debug=False)
        assert (log["send_number"] == 1 and log["debug"] is False)

        # run with '-d'
        log = runner.run_virtwho_cli(debug=True, oneshot=False)
        assert (log["send_number"] == 1 and log["debug"] is True)

    def test_oneshot_in_cli(self):
        """test the '-o' option in command line
        """

        # run without '-o'
        log = runner.run_virtwho_cli(oneshot=False)
        assert (log["send_number"] == 1 and log["oneshot"] is False)

        # run with '-o'
        log = runner.run_virtwho_cli(oneshot=True)
        assert (log["send_number"] == 1 and log["oneshot"] is True)

    def test_interval_in_cli(self):
        """test the '-i ' option in command line
        """

        # run without '-i' to test default interval=3600
        log = runner.run_virtwho_cli(oneshot=False, interval=None)
        assert (log["send_number"] == 1 and log["interval_time"] == 3600)

        # run with '-i 10' and check interval will use default 3600
        log = runner.run_virtwho_cli(oneshot=False, interval=10)
        assert (log["send_number"] == 1 and log["interval_time"] == 3600)

        # run with '-i 60' to test interval=60
        log = runner.run_virtwho_cli(oneshot=False, interval=60, wait=60)
        assert (log["send_number"] == 1
                and log["interval_time"] == 60
                and log["loop_time"] == 60)
