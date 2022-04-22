"""Test cases Global fields

:casecomponent: virt-who
:testtype: nonfunctional
:caseautomation: Automated
"""
from virtwho import logger


class TestVirtwhoPackageInfo:
    def test_shipped_in_different_arch(self):
        """Test the virt-who package is shipped in all supported arch

        :title: virt-who: base: test package is shipped in arch
        :id: a071e993-1070-4da5-8291-27a091a00d82
        :caseimportance: High
        :tags: package
        :customerscenario: false
        :upstream: no
        :steps:
            1.

        :expectedresults:
            1.
        """
        logger.info("Succeeded to run the 'test_shipped_in_different_arch'")
