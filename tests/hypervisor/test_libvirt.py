"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho import logger


class TestLibvirt:
    @pytest.mark.tier1
    def test_hostname_option(self):
        """Just a demo

        :title: virt-who: libvirt: test hostname option
        :id: c752e1e3-af9e-4d2a-aefe-3c7c21f7d58b
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

        :title: virt-who: libvirt: test http option
        :id: 16c7556f-e329-495a-b311-2305c5b2164d
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
