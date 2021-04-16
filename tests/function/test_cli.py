from virtwho.runner import Runner
from virtwho.configure import VirtwhoGlobalConfig

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
        result = runner.run_virtwho_cli(debug=False)
        assert (result["send_number"] == 1
                and result["debug"] is False)

        # run with '-d'
        result = runner.run_virtwho_cli(debug=True, oneshot=False)
        assert (result["send_number"] == 1
                and result["debug"] is True)

    def test_oneshot_in_cli(self):
        """test the '-o' option in command line
        """

        # run without '-o'
        result = runner.run_virtwho_cli(oneshot=False)
        assert (result["send_number"] == 1
                and result["error_number"] == 0
                and result["thread_number"] == 1
                and result["oneshot"] is False)

        # run with '-o'
        result = runner.run_virtwho_cli(oneshot=True)
        assert (result["send_number"] == 1
                and result["error_number"] == 0
                and result["thread_number"] == 0
                and result["oneshot"] is True)

    def test_interval_in_cli(self):
        """test the '-i ' option in command line
        """

        # run without '-i' to test default interval=3600
        result = runner.run_virtwho_cli(oneshot=False, interval=None)
        assert (result["send_number"] == 1
                and result["interval_time"] == 3600)

        # run with '-i 10' and check interval will use default 3600
        result = runner.run_virtwho_cli(oneshot=False, interval=10)
        assert (result["send_number"] == 1
                and result["interval_time"] == 3600)

        # run with '-i 60' to test interval=60
        result = runner.run_virtwho_cli(oneshot=False, interval=60, wait=60)
        assert (result["send_number"] == 1
                and result["interval_time"] == 60
                and result["loop_time"] == 60)

    def test_print_in_cli(self):
        guest_id = "42018c62-d744-65bf-0377-9efdac488a57"
        # without debug
        result = runner.run_virtwho_cli(oneshot=False, debug=False, prt=True)
        assert (result["thread_number"] == 0
                and guest_id in result["print_json"]
                )
        # with debug
        result = runner.run_virtwho_cli(oneshot=False, debug=True, prt=True)
        assert (result["thread_number"] == 0
                and guest_id in result["print_json"])
