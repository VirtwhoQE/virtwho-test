from betelgeuse import default_config

TESTCASE_CUSTOM_FIELDS = default_config.TESTCASE_CUSTOM_FIELDS + (
    "casecomponent",
    "subsystemteam",
    "reference",
)

DEFAULT_COMPONENT_VALUE = "virt-who"
DEFAULT_POOLTEAM_VALUE = "rhel-sst-csi-client-tools"
DEFAULT_REFERENCE_VALUE = ""
