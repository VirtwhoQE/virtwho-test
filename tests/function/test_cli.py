"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""
import threading
import time
import pytest

from virtwho import HYPERVISOR, RHEL_COMPOSE
from virtwho import HYPERVISOR_FILE, config, logger
from virtwho.base import encrypt_password


@pytest.mark.usefixtures("function_host_register_for_local_mode")
@pytest.mark.usefixtures("class_globalconf_clean")
@pytest.mark.usefixtures("class_hypervisor")
class TestCli:
    @pytest.mark.tier1
    @pytest.mark.fipsEnable
    @pytest.mark.gating
    def test_debug(self, virtwho):
        """Test the '-d' option in virt-who command line

        :title: virt-who: cli: test option -d
        :id: 9389396f-d4c3-4be2-8aec-a9f7be3d25f1
        :caseimportance: High
        :tags: function,cli,tier1
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
        assert result["send"] == 1 and result["error"] == 0 and result["debug"] is False

        result = virtwho.run_cli(debug=True)
        assert result["send"] == 1 and result["error"] == 0 and result["debug"] is True

    @pytest.mark.tier1
    @pytest.mark.fipsEnable
    @pytest.mark.gating
    def test_oneshot(self, virtwho):
        """Test the '-o' option in virt-who command line

        :title: virt-who: cli: test option -o
        :id: 6902b844-8b71-490c-abf1-fa6087987666
        :caseimportance: High
        :tags: function,cli,tier1
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
        assert (
            result["send"] == 1
            and result["error"] == 0
            and result["thread"] == 1
            and result["terminate"] == 0
            and result["oneshot"] is False
        )

        # BZ1448821: No log notice for hyperv rhevm and kubevirt for oneshot function.
        if HYPERVISOR not in ["rhevm", "hyperv", "kubevirt"]:
            assert result["oneshot"] is False

        result = virtwho.run_cli(oneshot=True, wait=10)
        assert (
            result["send"] == 1
            and result["error"] == 0
            and result["thread"] == 0
            and result["terminate"] == 1
        )

        # BZ1448821: No log notice for hyperv rhevm and kubevirt for oneshot function.
        if HYPERVISOR not in ["rhevm", "hyperv", "kubevirt"]:
            assert result["oneshot"] is True

    @pytest.mark.tier1
    @pytest.mark.fipsEnable
    @pytest.mark.gating
    def test_interval(self, virtwho):
        """Test the '-i' option in virt-who command line

        :title: virt-who: cli: test option -i
        :id: e43d9fd0-0f1b-4b25-98f6-c421046e1c47
        :caseimportance: High
        :tags: function,cli,tier1
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
        assert result["send"] == 1 and result["interval"] == 3600

        result = virtwho.run_cli(oneshot=False, interval=10)
        assert result["send"] == 1 and result["interval"] == 3600

        result = virtwho.run_cli(oneshot=False, interval=60, wait=60)
        assert result["send"] == 1 and result["interval"] == 60
        # Nutanix bug bz1996923 won't fix
        if HYPERVISOR == "ahv" and "RHEL-8" in RHEL_COMPOSE:
            rhsm_log = virtwho.rhsm_log_get()
            assert "No data to send, waiting for next interval" in rhsm_log
        else:
            assert result["loop"] in [60, 61, 62, 63]

    @pytest.mark.tier1
    def test_print(self, virtwho, hypervisor_data):
        """Test the '-p' option in virt-who command line

        :title: virt-who: cli: test option -p
        :id: 16c01269-f4ab-4fe5-a29e-a3d5dc69a32a
        :caseimportance: High
        :tags: function,cli,tier1
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
        guest_id = hypervisor_data["guest_uuid"]
        result = virtwho.run_cli(oneshot=False, debug=False, prt=True)
        assert (
            result["thread"] == 0
            and result["send"] == 0
            and result["debug"] is False
            and guest_id in result["print_json"]
        )

        result = virtwho.run_cli(oneshot=False, debug=True, prt=True)
        assert (
            result["thread"] == 0
            and result["send"] == 0
            and result["debug"] is True
            and guest_id in result["print_json"]
        )

    @pytest.mark.tier1
    @pytest.mark.notLocal
    def test_config(self, virtwho, ssh_host):
        """Test the '-c' option in virt-who command line

        :title: virt-who: cli: test option -c
        :id: 851a41fd-4fdc-4f8a-ac1b-e185079452fa
        :caseimportance: High
        :tags: function,cli,tier1
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
        config_file = "/root/test_cli_config.conf"
        ssh_host.runcmd(f"\\cp -f {HYPERVISOR_FILE} {config_file}")
        result = virtwho.run_cli(config=config_file)
        assert result["send"] == 1 and result["error"] == 0 and msg in result["log"]

    @pytest.mark.tier1
    def test_kill_virtwho_in_terminal_side(self, virtwho, ssh_host):
        """Test virt-who cli can be killed in terminal side by 'kill -2'

        :title: virt-who: cli: test kill virt-who in terminal
        :id: 9ed38e14-87dc-45b5-8656-b7933f6c72f2
        :caseimportance: High
        :tags: function,cli,tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. start a thread to run virt-who by cli
            2. kill the virt-who by 'kill 2'

        :expectedresults:

            1. virt-who cli can be killed normally in terminal side
        """
        t1 = threading.Thread(target=virtwho.run_cli(oneshot=False))
        t1.start()
        time.sleep(15)
        assert virtwho.thread_number() == 1

        # kill virt-who by 'kill -2'
        ssh_host.runcmd(
            "ps -ef |"
            "grep virt-who -i |"
            "grep -v grep |"
            "awk '{print $2}' |"
            "xargs -I {} kill -2 {}"
        )
        time.sleep(15)
        if HYPERVISOR == "ahv":
            logger.info("=== AHV: failed with RHEL-12395 ===")
        assert virtwho.thread_number() == 0

    @pytest.mark.tier1
    def test_run_virtwho_cli_when_the_service_is_running(self, virtwho, ssh_host):
        """Test virt-who cli cannot be run when a service is already running

        :title: virt-who: cli: test run virt-who cli when the service is running
        :id: 8921e482-ddf7-4f6d-882e-582fa0745b31
        :caseimportance: High
        :tags: function,cli,tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. start virt-who service
            2. try to run virt-who by cli

        :expectedresults:

            1. virt-who cli cannot be run when a service is already running
        """
        virtwho.operate_service(action="restart", wait=5)

        _, output = ssh_host.runcmd("virt-who")
        assert "already running" in output

    @pytest.mark.tier1
    def test_virtwho_encrypted_password(self, ssh_host):
        """

        :title: virt-who: cli: encrypted password with/without option
        :id: 694300a4-7d18-4f1b-bebb-5697751147f5
        :caseimportance: High
        :tags: function,cli,tier1
        :customerscenario: false
        :upstream: no
        :steps:

            1. encrypt virt-who host password by inputting password in
                interactive mode
            2. encrypt virt-who host password with -p option
            3. encrypt virt-who host password with --password option
            4. encrypt a special password: ad\"min

        :expectedresults:

            1. get the same encrypted password with the three methods.
            2. get the same encrypted password for ad\"min and '"ad\"min"'
        """
        password = config.virtwho.password
        encrypt_1 = encrypt_password(ssh_host, password)
        encrypt_2 = encrypt_password(ssh_host, password, option="-p")
        encrypt_3 = encrypt_password(ssh_host, password, option="--password")
        assert encrypt_1 == encrypt_2 == encrypt_3

        encrypt_1 = encrypt_password(ssh_host, r"ad\"min")
        encrypt_2 = encrypt_password(ssh_host, r"ad\"min", option="-p")
        encrypt_3 = encrypt_password(ssh_host, r'"ad\"min"', option="-p")
        encrypt_4 = encrypt_password(ssh_host, r"ad\"min", option="--password")
        encrypt_5 = encrypt_password(ssh_host, r'"ad\"min"', option="--password")
        assert encrypt_1 == encrypt_2 == encrypt_3 == encrypt_4 == encrypt_5
