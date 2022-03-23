"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho import logger


class TestEsx:
    @pytest.mark.tier1
    def test_hostname_option(self):
        """Just a demo

        :title: virt-who: esx: test hostname option
        :id: fb1f5dec-89c7-41e7-a15b-52b843f6f590
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

        :title: virt-who: esx: test http option
        :id: 37ee22b4-5105-4693-857d-4003715606ef
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
