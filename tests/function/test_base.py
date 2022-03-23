"""Test cases Global fields

:casecomponent: virt-who
:testtype: nonfunctional
:caseautomation: Automated
"""
import pytest
from virtwho import logger


class TestVirtwhoPackage:
    @pytest.mark.packageInfo
    def test_shipped_in_different_arch(self):
        """Test the virt-who package is shipped in all supported arch

        :title: virt-who: base: test package is shipped in arch
        :id: a071e993-1070-4da5-8291-27a091a00d82
        :caseimportance: High
        :tags: packageInfo
        :customerscenario: false
        :upstream: no
        :steps:
            1.

        :expectedresults:
            1.
        """
        logger.info("Succeeded to run the 'test_shipped_in_different_arch'")


class TestMultiHypervisors:
    @pytest.mark.multiHypervisor
    def test_multi_hypervisors_report(self):
        """Test virt-who can report multi hypervisors together

        :title: virt-who: base: test multi hypervisors report together
        :id: 9fb6694e-7535-4d9f-9ac0-75e6cbe3066d
        :caseimportance: High
        :tags: multiHypervisor
        :customerscenario: false
        :upstream: no
        :steps:
            1.
        :expectedresults:
            1.
        """
        logger.info("Succeeded to run the 'test_multi_hypervisors_report'")
