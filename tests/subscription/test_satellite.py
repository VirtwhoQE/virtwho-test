"""Test cases Global fields
:casecomponent: virt-who
:testtype: functional
:caseautomation: Automated
"""
import pytest
from virtwho import logger


class TestSatellite:
    @pytest.mark.tier1
    def test_vdc_attach(self):
        """Just a demo
        :title: virt-who: satellite: test vdc sku attach
        :id: cd0e8694-4180-4b21-b9ed-9fe06005f066
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
        :title: virt-who: satellite: test vdc sku unattach
        :id: b5564039-fe25-4295-9911-abd77c2f14b7
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