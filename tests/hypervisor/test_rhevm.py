"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho import logger


class TestRhevm:
    @pytest.mark.tier1
    def test_hostname_option(self):
        """Just a demo

        :title: virt-who: rhevm: test hostname option
        :id: 3faa0d5a-77e9-4931-9793-8f0eb352e83c
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        logger.info("Succeeded to run the 'test_hostname_option'")

    @pytest.mark.tier2
    def test_http_option(self):
        """Just a demo

        :title: virt-who: rhevm: test http option
        :id: e56e6f64-63aa-4ffa-af2d-245552d120e8
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        logger.info("Succeeded to run the 'test_http_option'")
