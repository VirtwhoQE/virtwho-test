"""Test cases Global fields

:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho import logger


class TestRhsm:
    @pytest.mark.tier1
    def test_vdc_attach(self):
        """Just a demo

        :title: virt-who: rhsm: test vdc sku attach
        :id: b35d26e4-42da-4b31-b079-5842a146d00b
        :caseimportance: High
        :tags: tier1
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        logger.info("Succeeded to run the 'test_vdc_attach'")

    @pytest.mark.tier2
    def test_vdc_remove(self):
        """Just a demo

        :title: virt-who: rhsm: test vdc sku unattach
        :id: 1c512c2c-51f8-4e95-a34a-e3b2592f2fde
        :caseimportance: High
        :tags: tier2
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        logger.info("Succeeded to run the 'test_vdc_remove'")
