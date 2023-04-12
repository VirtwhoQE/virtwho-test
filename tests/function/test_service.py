"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho.configure import hypervisor_create
from virtwho.base import msg_search


@pytest.mark.usefixtures('class_hypervisor')
@pytest.mark.usefixtures('class_virtwho_d_conf_clean')
@pytest.mark.usefixtures('class_globalconf_clean')
class TestVirtwhoService:
    @pytest.mark.tier1
    def test_start_and_stop(self, virtwho):
        """

        :title: virt-who: service: test start and stop
        :id: 42891e5b-5e84-43d0-ba56-7c4f4348bdc4
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. stop then start virt-who service to check the status
            2. stop again the virt-who service to check the status
        :expectedresults:
            1. virt-who is running after start the service
            2. virt-who is dead after stop the service
        """
        _, _ = virtwho.operate_service(action='stop')
        _, _ = virtwho.operate_service(action='start')
        _, output = virtwho.operate_service(action='status')
        assert 'Active: active (running)' in output

        _, _ = virtwho.operate_service(action='stop')
        _, output = virtwho.operate_service(action='status')
        assert 'Active: inactive (dead)' in output

    @pytest.mark.tier1
    def test_restart(self, virtwho):
        """

        :title: virt-who: service: test restart
        :id: 60071821-31a8-49d0-a656-4a27f64ec18a
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. restart virt-who service to check the status
        :expectedresults:
            1. virt-who is running after restart the service
        """
        _, _ = virtwho.operate_service(action='restart')
        _, output = virtwho.operate_service(action='status')
        assert 'Active: active (running)' in output

    @pytest.mark.tier1
    def test_try_restart(self, virtwho):
        """

        :title: virt-who: service: test try-restart
        :id: 5fe64b1b-ca5c-4b6e-bf11-207d8d0b7736
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. try-restart virt-who service to check the status
        :expectedresults:
            1. virt-who is running after try-restart the service
        """
        _, _ = virtwho.operate_service(action='try-restart')
        _, output = virtwho.operate_service(action='status')
        assert 'Active: active (running)' in output

    @pytest.mark.tier1
    def test_force_reload(self, virtwho):
        """

        :title: virt-who: service: test force-reload
        :id: 91e933c8-88fc-44d9-bf07-d349fe18d8a5
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1. force-reload virt-who service to check the status
        :expectedresults:
            1. virt-who is running after force-reload the service
        """
        _, _ = virtwho.operate_service(action='force-reload')
        _, output = virtwho.operate_service(action='status')
        assert 'Active: active (running)' in output

    @pytest.mark.tier1
    def test_virtwho_service_after_host_reregister(self, virtwho, sm_host,
                                                   ssh_host):
        """

        :title: virt-who: service: test virt-who service after host reregister
        :id: 7e7bba4c-cb32-4385-a9b7-1416cd026837
        :caseimportance: High
        :tags: tier1
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
            assert (result['error'] == 0
                    and result['send'] == 1
                    and result['thread'] == 1)

            # unregister and clean together
            sm_host.unregister()
            rhsm_log = virtwho.rhsm_log_get(wait=15)
            thread_num = virtwho.thread_number()
            assert (msg_search(rhsm_log, 'system is not registered')
                    and thread_num == 1)

            # register and then run virt-who
            sm_host.register()
            result = virtwho.run_service()
            assert (result['error'] == 0
                    and result['send'] == 1
                    and result['thread'] == 1)

            # firstly unregister and then clean
            ret_1, _ = ssh_host.runcmd('subscription-manager unregister')
            ret_2, _ = ssh_host.runcmd('subscription-manager clean')
            rhsm_log = virtwho.rhsm_log_get(wait=15)
            thread_num = virtwho.thread_number()
            assert (msg_search(rhsm_log, 'system is not registered')
                    and thread_num == 1)

            # register and then run virt-who
            sm_host.register()
            result = virtwho.run_service()
            assert (result['error'] == 0
                    and result['send'] == 1
                    and result['thread'] == 1)

        finally:
            hypervisor_create(rhsm=True)
