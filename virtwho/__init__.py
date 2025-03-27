from virtwho.logger import getLogger
from virtwho.settings import config
import re
import os


logger = getLogger(__name__)

RHEL_COMPOSE = config.job.rhel_compose or os.environ.get('RHEL_COMPOSE')

RHEL_COMPOSE_PATH = config.job.rhel_compose_path


def version_subversion(compose):
    rhel_regexp = re.compile(r"^RHEL-([\d]+)\.([\d]+)", re.IGNORECASE)
    (rhel_version, rhel_subversion) = map(
        int, rhel_regexp.search(RHEL_COMPOSE).groups()
    )
    return (rhel_version, rhel_subversion)


(RHEL_VERSION, RHEL_SUBVERSION) = version_subversion(RHEL_COMPOSE)

HYPERVISOR = config.job.hypervisor

SYSCONFIG_FILE = "/etc/sysconfig/virt-who"

HYPERVISOR_FILE = f"/etc/virt-who.d/{HYPERVISOR}.conf"

PRINT_JSON_FILE = "/root/print.json"

FAKE_CONFIG_NAME = "fake.conf"

FAKE_CONFIG_FILE = f"/etc/virt-who.d/{FAKE_CONFIG_NAME}"

SECOND_HYPERVISOR_FILE = f"/etc/virt-who.d/{HYPERVISOR}-second.conf"

SECOND_HYPERVISOR_SECTION = f"virtwho-{HYPERVISOR}-second"

REGISTER = config.job.register

VIRTWHO_PKG = config.virtwho.package

VIRTWHO_VERSION = ""
if VIRTWHO_PKG:
    VIRTWHO_VERSION = VIRTWHO_PKG.split("-")[2]

# Backup file for /etc/virt-who.conf
VIRTWHO_CONF_BACKUP = "virt-who.conf.save"

# Backup file for /etc/rhsm/rhsm.conf
RHSM_CONF_BACKUP = "rhsm.conf.save"


class FailException(BaseException):
    def __init__(self, error_message):
        logger.error(error_message)
