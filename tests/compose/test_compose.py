"""Test class for for rhel compose trigger

"""

import pytest
from virt_who.base import Base, os
from tests.cases.cases import hypervisor_data, register_data, case_level


class TestVirtWhoRhelCompose:
    def test_run(self, hypervisor_data, register_data, case_level):
        """
        :cases: like "test_1 or test_2 or test_3"
        :m_tier: marks for case level, like "tier1 or tier2"
        :m_register: marks for register server, like "rhsmOnly" or "satelliteOnly"
        """
        hypervisor = hypervisor_data["type"]
        register_server = register_data["type"]
        case_path = "/root/workspace/virtwho-test/tests/compose/hypervisors/{}.yml".format(hypervisor)
        cases = Base.case_get(case_path)
        code_path = "/root/workspace/virtwho-test/tests/cases/cases.py"
        base_cmd = 'pytest -sv {} -k "{}"'.format(code_path, cases)

        m_tier = ' or '.join(i for i in case_level)
        dic = {'satellite': 'not rhsmOnly',
               'rhsm':      'not satelliteOnly'}
        m_register = dic[register_server]

        cmd = base_cmd + ' -m ' + '"{}"'.format(m_tier) + ' -m ' + '"{}"'.format(m_register)
        print(cmd)
        os.system(cmd)

    # @pytest.mark.parametrize('args', cases)
    # def test_run(self, args, case_level, register_server):
    #     """Run case one by one
    #     :
    #     """
    #     code_path = "/root/workspace/virtwho-test/tests/cases/cases.py"
    #     base_cmd = 'pytest -sv {} -k "{}"'.format(code_path, args)
    #     tier_marks = ''
    #     if case_level == 'tier1':
    #         tier_marks = 'tier1'
    #     elif case_level == 'tier2':
    #         tier_marks = 'tier1'
    #     else:
    #         tier_marks = 'tier1 or tier2'
    #
    #     if register_server == "satellite":
    #         server_marks = 'not rhsmOnly'
    #     else:
    #         server_marks = 'not satelliteOnly'
    #
    #     cmd = base_cmd + ' -m ' + '"{}"'.format(tier_marks) + ' -m ' + '"{}"'.format(server_marks)
    #     print(cmd)
    #     os.system(cmd)
