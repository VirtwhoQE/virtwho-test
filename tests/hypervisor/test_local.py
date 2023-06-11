"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""
import pytest
from virtwho import logger


class TestLocal:
    @pytest.mark.tier1
    def test_hostname_option(self):
        """Just a demo

        :title: virt-who: local: test hostname option
        :id: 33cc5ba0-c529-481b-8cfa-8613adbe23ee
        :caseimportance: High
        :tags: hypervisor,local,tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1.demo
        :expectedresults:
            1.demo
        """
        logger.info("Succeeded to run the 'test_hostname_option'")

    @pytest.mark.tier2
    def test_http_option(self):
        """Just a demo

        :title: virt-who: local: test http option
        :id: a66787b3-1a5f-4b6f-9c09-0873d6490de3
        :caseimportance: High
        :tags: hypervisor,local,tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1. demo
        :expectedresults:
            1. demo
        """
        logger.info("Succeeded to run the 'test_http_option'")
