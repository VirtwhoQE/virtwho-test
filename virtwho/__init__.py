from virtwho.logger import getLogger
from virtwho.settings import config

logger = getLogger(__name__)

RHEL_COMPOSE = config.job.rhel_compose

HYPERVISOR = config.job.hypervisor

HYPERVISOR_FILE = f'/etc/virt-who.d/{HYPERVISOR}.conf'

DEFAULT_HYPERVISOR_FILE = '/etc/virt-who.d/virtwho-config.conf'

SECTION_NAME = 'virtwho-config'

REGISTER = config.job.register

VIRTWHO_PKG = config.virtwho.package


class FailException(BaseException):
    def __init__(self, error_message):
        logger.error(error_message)
