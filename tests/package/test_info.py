"""Test cases Global fields

:casecomponent: virt-who
:testtype: nonfunctional
:subtype1: documentation
:caseautomation: Automated
:subsystemteam: sst_subscription_virtwho
:caselevel: Component
"""

import os
import re
import pytest

from virtwho import base, RHEL_COMPOSE, RHEL_COMPOSE_PATH, VIRTWHO_PKG, VIRTWHO_VERSION
from virtwho.settings import DOCS_DIR, TEMP_DIR


@pytest.mark.usefixtures("class_globalconf_clean")
@pytest.mark.usefixtures("class_hypervisor")
@pytest.mark.usefixtures("class_virtwho_d_conf_clean")
class TestVirtwhoPackageInfo:
    @pytest.mark.tier1
    def test_shipped_in_supported_arch(self):
        """Test the virt-who package is shipped in all supported arch

        :title: virt-who: package: test package is shipped in arch
        :id: f273943a-595f-4995-9e7c-fd266253642f
        :caseimportance: High
        :tags: package,tier1
        :customerscenario: false
        :steps:
            1. test virt-who package is shipped with x86_64 arch
            2. test virt-who package is shipped with ppc64le arch
            3. test virt-who package is shipped with aarch64 arch
            4. test virt-who package is shipped with s390x arch

        :expectedresults:
            1. virt-who package are shipped in each supported arch
        """
        _, repo_extra = base.rhel_compose_url(RHEL_COMPOSE, RHEL_COMPOSE_PATH)
        base_url = repo_extra.split("/x86_64/")[0]
        archs = ["x86_64", "ppc64le", "aarch64", "s390x"]
        for arch in archs:
            pkg_url = f"{base_url}/{arch}/os/Packages/{VIRTWHO_PKG}.rpm"
            assert base.url_validation(pkg_url)

    @pytest.mark.tier1
    def test_version(self, ssh_host):
        """Check the virt-who version by command #virt-who --version

        :title: virt-who: package: test #virt-who --version
        :id: 4b207364-ba7f-4ef6-a336-66025a95b182
        :caseimportance: High
        :tags: package,tier1
        :customerscenario: false
        :steps:
            1. run #virt-who --version

        :expectedresults:
            1. the result format should be `virt-who 1.31.23-1`
        """
        version = re.split("virt-who-|.el", VIRTWHO_PKG)[1]
        # RHEL-50649/RHEL-50650 won't fix
        if VIRTWHO_VERSION >= "1.31.28":
            version = re.split("virt-who-|.noarch", VIRTWHO_PKG)[1]
        _, output = ssh_host.runcmd("virt-who --version")
        output = output.split(" ")
        assert output[0].strip() == "virt-who" and output[1].strip() == version

    @pytest.mark.tier1
    def test_man_page(self, ssh_host):
        """Test the changes of virt-who man page

        :title: virt-who: package: test man page
        :id: ba708ea8-0658-4abf-8dbd-739956e9b945
        :caseimportance: High
        :tags: package,tier1
        :customerscenario: false
        :steps:
            1. run "#man virt-who"
            2. compare man page with the previous version

        :expectedresults:
            1. man page can be list successfully
            2. no changes by comparing with the previous build
        """
        man_page_remote = "/root/man_page"
        man_page_local = os.path.join(TEMP_DIR, "virtwho_man_page")
        man_page_compare = os.path.join(DOCS_DIR, "virtwho_man_page_rhel_9")
        if "RHEL-10" in RHEL_COMPOSE:
            man_page_compare = os.path.join(DOCS_DIR, "virtwho_man_page_rhel_10")
        ssh_host.runcmd(f"man virt-who > {man_page_remote}")
        ssh_host.get_file(man_page_remote, man_page_local)
        assert base.local_files_compare(man_page_local, man_page_compare)

    @pytest.mark.tier1
    def test_help_page(self, virtwho, ssh_host):
        """Test the changes of virt-who help page

        :title: virt-who: package: test help page
        :id: d5a8e2d3-1626-4fdc-a5c6-db52c266b96d
        :caseimportance: High
        :tags: package,tier1
        :customerscenario: false
        :steps:
            1. run "#virt-who -h"
            2. compare help page with the previous version

        :expectedresults:
            1. help page can be list successfully
            2. no changes by comparing with the previous build
        """
        help_page_remote = "/root/help_page"
        help_page_local = os.path.join(TEMP_DIR, "virtwho_help_page")
        help_page_compare = os.path.join(DOCS_DIR, "virtwho_help_page_rhel_9")
        if "RHEL-10" in RHEL_COMPOSE:
            help_page_compare = os.path.join(DOCS_DIR, "virtwho_help_page_rhel_10")
        ssh_host.runcmd(f"virt-who --help > {help_page_remote}")
        ssh_host.get_file(help_page_remote, help_page_local)
        assert base.local_files_compare(help_page_local, help_page_compare)

    @pytest.mark.tier1
    def test_package_info(self, ssh_host):
        """Test the virt-who package detail info by #rpm -qi virt-who

        :title: virt-who: package: test virt-who package information
        :id: 51beaf61-f01d-4edd-870e-8682c18d07bb
        :caseimportance: High
        :tags: package,tier1
        :customerscenario: false
        :steps:
            1. run "#rpm -qi virt-who"
            2. check each value

        :expectedresults:
            1. all values match the expectation
        """
        pkg_info = base.package_info_analyzer(ssh_host, "virt-who")
        virtwho_license = "GPLv2+ and LGPLv3+"
        group = "System Environment/Base"
        if VIRTWHO_VERSION >= "1.31.28":
            virtwho_license = "GPL-2.0-or-later AND LGPL-3.0-or-later"
            group = "Unspecified"

        # Expected values for long strings
        expected_packager = "Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>"
        expected_summary = "Agent for reporting virtual guest IDs to subscription-manager"

        assert (
            pkg_info["Name"] == "virt-who"
            and pkg_info["Version"] in VIRTWHO_PKG
            and pkg_info["Release"] in VIRTWHO_PKG
            and pkg_info["Architecture"] == "noarch"
            and pkg_info["Install Date"]
            and pkg_info["Group"] == group
            and pkg_info["Size"]
            and pkg_info["License"] == virtwho_license
            and "RSA/SHA256" in pkg_info["Signature"]
            and "Key ID" in pkg_info["Signature"]
            and pkg_info["Source RPM"] == VIRTWHO_PKG.split("noarch")[0] + "src.rpm"
            and pkg_info["Build Date"]
            and pkg_info["Build Host"]
            and pkg_info["Packager"] == expected_packager
            and pkg_info["Vendor"] == "Red Hat, Inc."
            and pkg_info["URL"] == "https://github.com/candlepin/virt-who"
            and pkg_info["Summary"] == expected_summary
        )

    @pytest.mark.tier1
    def test_package_info_with_User_Agent_header(self, ssh_host, virtwho):
        """

        :title: virt-who: package: test virt-who package information with user agent header
        :id: 9ec0e56e-e643-4c7d-b622-2d34915e407b
        :caseimportance: High
        :tags: package,tier1
        :customerscenario: false
        :steps:
            1. export the SUBMAN_DEBUG_PRINT_REQUEST=1 and
                SUBMAN_DEBUG_PRINT_REQUEST_HEADER=1
            2. run virt-who service to check rhsm log

        :expectedresults:
            1. the virt-who package info is printed to log.
        """
        virtwho.stop()
        _, output = ssh_host.runcmd(
            "export SUBMAN_DEBUG_PRINT_REQUEST=1;"
            "export SUBMAN_DEBUG_PRINT_REQUEST_HEADER=1;"
            "virt-who -o",
            if_stdout=True,
        )
        pkg = base.package_check(ssh_host, "virt-who")[9:18]
        assert f"virt-who/{pkg}" in output
