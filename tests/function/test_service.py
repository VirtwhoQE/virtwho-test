"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""

import pytest
from virtwho.settings import config
from virtwho.configure import hypervisor_create
from virtwho.base import msg_search, ssh_access_no_password, expect_run
from virtwho import HYPERVISOR, REGISTER, logger
from virtwho.ssh import SSHConnect


@pytest.mark.usefixtures("function_host_register_for_local_mode")
@pytest.mark.usefixtures("class_hypervisor")
@pytest.mark.usefixtures("class_virtwho_d_conf_clean")
@pytest.mark.usefixtures("class_globalconf_clean")
@pytest.mark.usefixtures("class_hypervisor")
@pytest.mark.usefixtures("class_virtwho_d_conf_clean")
class TestVirtwhoService:
    @pytest.mark.tier1
    @pytest.mark.gating
    @pytest.mark.fedoraSmoke
    def test_virtwho_service_start_and_stop(self, virtwho):
        """

        :title: virt-who: service: test start and stop virt-who service
        :id: 42891e5b-5e84-43d0-ba56-7c4f4348bdc4
        :caseimportance: High
        :tags: function,service,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. stop then start virt-who service to check the status
            2. stop again the virt-who service to check the status
        :expectedresults:
            1. virt-who is running after start the service
            2. virt-who is dead after stop the service
        """
        virtwho.operate_service(action="stop")
        virtwho.operate_service(action="start")
        _, output = virtwho.operate_service(action="status")
        assert output is "running"

        virtwho.operate_service(action="stop")
        _, output = virtwho.operate_service(action="status")
        if HYPERVISOR == "ahv":
            logger.info("=== AHV: failed with RHEL-12393 ===")
        assert output is "dead"

    @pytest.mark.tier1
    def test_virtwho_service_restart(self, virtwho):
        """

        :title: virt-who: service: test restart virt-who service
        :id: 60071821-31a8-49d0-a656-4a27f64ec18a
        :caseimportance: High
        :tags: function,service,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. restart virt-who service to check the status
        :expectedresults:
            1. virt-who is running after restart the service
        """
        virtwho.operate_service(action="restart")
        _, output = virtwho.operate_service(action="status")
        assert output is "running"

    @pytest.mark.tier1
    def test_virtwho_service_try_restart(self, virtwho):
        """

        :title: virt-who: service: test try-restart virt-who service
        :id: 5fe64b1b-ca5c-4b6e-bf11-207d8d0b7736
        :caseimportance: High
        :tags: function,service,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. try-restart virt-who service to check the status
        :expectedresults:
            1. virt-who is running after try-restart the service
        """
        virtwho.operate_service(action="try-restart")
        _, output = virtwho.operate_service(action="status")
        assert output is "running"

    @pytest.mark.tier1
    def test_virtwho_service_force_reload(self, virtwho):
        """

        :title: virt-who: service: test force-reload virt-who service
        :id: 91e933c8-88fc-44d9-bf07-d349fe18d8a5
        :caseimportance: High
        :tags: function,service,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. force-reload virt-who service to check the status
        :expectedresults:
            1. virt-who is running after force-reload the service
        """
        virtwho.operate_service(action="force-reload")
        _, output = virtwho.operate_service(action="status")
        assert output is "running"

    @pytest.mark.tier1
    @pytest.mark.fipsEnable
    def test_virtwho_service_control_by_ssh_connect(self, virtwho, ssh_guest, ssh_host):
        """

        :title: virt-who: service: test virt-who service control by ssh connect
        :id: 486e180d-691b-4c89-af66-b93d4dd84b8c
        :caseimportance: High
        :tags: function,service,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. configure a remote rhel host accessing the virt-who host by ssh
                without password
            2. in the remote host, try to stop the virt-who service by command
                'ssh [server_ip] -p [server_port] "systemctl stop virt-who"'
            3. in the remote host, try to start the virt-who service by command
                'ssh [server_ip] -p [server_port] "systemctl start virt-who"'
            4. in the remote host, try to stop the virt-who service again by
                'ssh [server_ip] -p [server_port] "systemctl stop virt-who"'
        :expectedresults:
            1. we can control the virt-who service in a remote host by
                ssh login.
        """
        server = config.virtwho.server
        port = config.virtwho.port
        ssh_access_no_password(ssh_guest, ssh_host, server, port)
        virtwho.kill_pid('virt-who')
        # stop
        ssh_guest.runcmd(
            f"ssh -o StrictHostKeyChecking=no {server} -p {port} 'systemctl stop virt-who'"
        )
        _, status = virtwho.operate_service(action="status")
        if HYPERVISOR == "ahv":
            logger.info("=== AHV: failed with RHEL-12393 ===")
        assert status == "dead"

        # start
        ssh_guest.runcmd(
            f"ssh -o StrictHostKeyChecking=no {server} -p {port} 'systemctl restart virt-who'"
        )
        _, status = virtwho.operate_service(action="status")
        assert status == "running"

        # stop
        ssh_guest.runcmd(
            f"ssh -o StrictHostKeyChecking=no {server} -p {port} 'systemctl stop virt-who'"
        )
        _, status = virtwho.operate_service(action="status")
        assert status == "dead"

    @pytest.mark.tier1
    def test_virtwho_and_rhsmcertd_servce(self, virtwho, ssh_host):
        """

        :title: virt-who: service: test virt-who and rhsmcertd service
        :id: ab28679b-f505-47fb-a7ae-760d2cec7045
        :caseimportance: High
        :tags: function,service,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. restart virt-who service, check virt-who status and thread
            2. restart rhsmcertd service , check virt-who status and thread
            3. restart virt-who service again , check virt-who run without error
        :expectedresults:
            1. restarting the rhsmcertd service will not impact virt-who service
        """
        virtwho.operate_service(action="restart")
        _, output = virtwho.operate_service(action="status")
        assert output == "running" and virtwho.thread_number() == 1

        ret, _ = ssh_host.runcmd(f"systemctl restart rhsmcertd")
        assert ret == 0
        _, output = virtwho.operate_service(action="status")
        assert output == "running" and virtwho.thread_number() == 1

        result = virtwho.run_service()
        assert result["send"] == 1 and result["error"] == 0 and result["thread"] == 1

    @pytest.mark.tier1
    def test_virtwho_ignore_swp_file(self, virtwho, ssh_host):
        """

        :title: virt-who: service: test virt-who service ignores /etc/virt-who.d/xx.swp file
        :id: 85d390dd-5b9c-4428-85d9-ef28568faae8
        :caseimportance: High
        :tags: function,service,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. create an available /etc/virt-who.d/mode.conf file
            2. create a bad /etc/virt-who.d/*.swp file
            3. restart virt-who service to check log
        :expectedresults:
            1. virt-who service ignores the /etc/virt-who.d/*.swp file
        """
        swp_config_file = "/etc/virt-who.d/.test.conf.swp"
        swp = hypervisor_create(
            mode=HYPERVISOR,
            register_type=REGISTER,
            config_name=swp_config_file,
            section="test-swp",
        )

        try:
            swp.update("type", "test")
            ssh_host.runcmd(f"cat /etc/virt-who.d/.test.conf.swp")
            result = virtwho.run_service()
            assert result["send"] == 1 and result["error"] == 0

        finally:
            ssh_host.runcmd(f"rm -rf {swp_config_file}")

    @pytest.mark.tier2
    def test_virtwho_non_root_user(self, virtwho, ssh_host):
        """

        :title: virt-who: service: test virt-who in non_root user
        :id: fa260cd0-0f1b-4238-84c6-271a175add94
        :caseimportance: High
        :tags: function,service,tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. create a new non_root user account for virt-who host
            2. start virt-who service by the new account
        :expectedresults:
            1. virt-who service can start and report normally by the non_root
                account.
        """
        host = config.virtwho.server
        username_new = "tester"
        password = config.virtwho.password
        ssh_host.runcmd(f"useradd {username_new}")
        cmd = rf'echo -e "{username_new}:{password}" | chpasswd'
        ssh_host.runcmd(cmd)

        ssh_new = SSHConnect(host=host, user=username_new, pwd=password)
        virtwho.stop()
        virtwho.log_clean()
        expect_run(
            ssh=ssh_new, cmd="systemctl start virt-who", attrs=[f"Password:|{password}"]
        )
        rhsm_log = virtwho.rhsm_log_get()
        result = virtwho.analyzer(rhsm_log)
        assert result["send"] == 1 and result["error"] == 0 and result["thread"] == 1

    @pytest.mark.tier1
    def test_virtwho_service_after_host_reregister(self, virtwho, sm_host, ssh_host):
        """

        :title: virt-who: service: test virt-who service after host reregister
        :id: 7e7bba4c-cb32-4385-a9b7-1416cd026837
        :caseimportance: High
        :tags: function,service,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. start virt-who service with virt-who host registered.
            2. unregister and clean virt-who host together to check rhsm log
            3. register the virt-who host again and restart virt-who service to
                check log.
            4. firstly unregister, then clean the host to check rhsm log
            5. register the virt-who host again and restart virt-who service to
                check log.
        :expectedresults:
            1. after unregister and clean virt-who host when virt-who service
                is running, virt-who will fail to report with error, but
                virt-who thread is not killed.
            2. after register virt-who host again, virt-who can report
                successfully.
        """
        try:
            hypervisor_create(rhsm=False)

            sm_host.register()
            result = virtwho.run_service()
            assert (
                result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
            )

            # unregister and clean together
            sm_host.unregister()
            rhsm_log = virtwho.rhsm_log_get(wait=15)
            thread_num = virtwho.thread_number()
            assert thread_num == 1
            if HYPERVISOR == "ahv":
                logger.info("=== AHV: failed with RHEL-5887 ===")
            assert msg_search(rhsm_log, "system is not registered")

            # register and then run virt-who
            sm_host.register()
            result = virtwho.run_service()
            assert (
                result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
            )

            # firstly unregister and then clean
            ret_1, _ = ssh_host.runcmd("subscription-manager unregister")
            ret_2, _ = ssh_host.runcmd("subscription-manager clean")
            rhsm_log = virtwho.rhsm_log_get(wait=15)
            thread_num = virtwho.thread_number()
            assert msg_search(rhsm_log, "system is not registered") and thread_num == 1

            # register and then run virt-who
            sm_host.register()
            result = virtwho.run_service()
            assert (
                result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
            )

        finally:
            hypervisor_create(rhsm=True)
