"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest


@pytest.mark.usefixtures('globalconf_clean')
@pytest.mark.usefixtures('hypervisor_create')
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
