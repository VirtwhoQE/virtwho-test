"""Test cases Global fields

:casecomponent: virt-who
:testtype: nonfunctional
:caseautomation: Automated
"""
import pytest
from virtwho import logger


class TestInstallUninstall:
    @pytest.mark.tier1
    def test_install_uninstall_by_yum(self):
        """Just a demo

        :title: VIRT-WHO: test install uninstall by yum
        :id: d2b53819-e876-4595-8407-549eb8ef1bdb
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        logger.info("Succeeded to run the 'test_install_uninstall'")
