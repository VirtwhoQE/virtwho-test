"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
from virtwho import logger


class TestMultiHypervisors:
    def test_multi_hypervisors_report_together(self):
        """Test virt-who can report multi hypervisors together

        :title: virt-who: base: test multi hypervisors report together
        :id: 9fb6694e-7535-4d9f-9ac0-75e6cbe3066d
        :caseimportance: High
        :tags: multiHypervisor
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        logger.info("Succeeded to run the 'test_multi_hypervisors_report'")
