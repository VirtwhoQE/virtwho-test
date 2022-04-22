"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho import logger


class TestVirtwhoService:
    @pytest.mark.tier1
    def test_restart(self):
        """Just a demo

        :title: VIRT-WHO: test restart
        :id: 6a36dd7c-1fd5-4aa7-9da0-5529053a9eff
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        logger.info("Succeeded to run the 'test_restart'")
