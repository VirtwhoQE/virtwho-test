# """Test cases Global fields
#
# :SubsystemTeam: sst_subscription_virtwho
# :TestType: Functional
# :CaseLevel: Function
# :CaseAutomation: Automated
# """
# import pytest
# from virtwho import logger
#
#
# @pytest.mark.usefixtures('globalconf_clean')
# @pytest.mark.usefixtures('hypervisor_create')
# class TestCli:
#     def test_debug(self, virtwho, sm_host):
#         result = virtwho.run_cli(debug=True)
#         assert (result['send'] == 1
#                 and result['error'] == 0
#                 and result['debug'] is True)
#
#     def test_sm_host(self, sm_host):
#         sm_host.register()
#
#     def test_sm_guest(self, sm_guest):
#         sm_guest.register()
#
#     def test_rhsm(self, rhsm):
#         pool = rhsm.pool(sku_id='RH00002')
#         logger.info(f'===={pool}====')
