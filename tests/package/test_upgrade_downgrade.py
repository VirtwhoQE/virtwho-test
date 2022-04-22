"""Test cases Global fields

:casecomponent: virt-who
:testtype: nonfunctional
:caseautomation: Automated
"""
import pytest
from virtwho import logger


class TestUpgradeDowngrade:
    @pytest.mark.tier1
    def test_upgrade_downgrade_by_yum(self):
        """Just a demo

        :title: VIRT-WHO: test upgrade and downgrade by yum
        :id: 64c09d15-3050-4d73-8d9e-296836c4ac58
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        logger.info("Succeeded to run the 'test_upgrade_downgrade_by_yum'")
