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


@pytest.mark.usefixtures("function_virtwho_d_conf_clean")
@pytest.mark.usefixtures("class_debug_true")
@pytest.mark.usefixtures("class_globalconf_clean")
class TestMultiHypervisors:
    def test_multi_hypervisors_report_together(self, virtwho):
        """Test virt-who can report multi hypervisors together

        :title: virt-who: multiHypervisors: test multi hypervisors report together
        :id: 9fb6694e-7535-4d9f-9ac0-75e6cbe3066d
        :caseimportance: High
        :tags: hypervisor,multiHypervisor
        :customerscenario: false
        :upstream: no
        :steps:
            1. Create the virt-who config files for the multi hypervisors list
            2. Run the virt-who service

        :expectedresults:
            1. Succeed to run the virt-who, no error messages in the rhsm.log
        """
        for mode in config.job.multi_hypervisors.strip('[').strip(']').split(','):
            hypervisor_create(mode)
        result = virtwho.run_service()
        assert result["error"] == 0 and result["send"] == 1 and result["thread"] == 1
