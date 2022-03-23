"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho import logger


class TestKubevirt:
    @pytest.mark.tier1
    def test_hostname_option(self):
        """Just a demo

        :title: virt-who: kubevirt: test hostname option
        :id: 633ca810-0fc1-4861-a54c-f2b00b98ed59
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

        :title: virt-who: kubevirt: test http option
        :id: cd99fc7e-0d26-4ba3-8aca-a5f6a9c656b0
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
