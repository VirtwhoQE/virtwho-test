from virtwho.logger import getLogger
from virtwho.settings import config

logger = getLogger(__name__)

RHEL_COMPOSE = config.job.rhel_compose

HYPERVISOR = config.job.hypervisor

HYPERVISOR_FILE = f'/etc/virt-who.d/{HYPERVISOR}.conf'

PRINT_JSON_FILE = '/root/print.json'

SECOND_HYPERVISOR_FILE = f'/etc/virt-who.d/{HYPERVISOR}-second.conf'

SECOND_HYPERVISOR_SECTION = f'virtwho-{HYPERVISOR}-second'

REGISTER = config.job.register

VIRTWHO_PKG = config.virtwho.package
# Backup file for /etc/virt-who.conf
VIRTWHO_CONF_BACKUP = 'virt-who.conf.save'
# Backup file for /etc/rhsm/rhsm.conf
RHSM_CONF_BACKUP = 'rhsm.conf.save'


class FailException(BaseException):
    def __init__(self, error_message):
        logger.error(error_message)
