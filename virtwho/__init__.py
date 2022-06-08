from virtwho.logger import getLogger
from virtwho.settings import config

logger = getLogger(__name__)

RHEL_COMPOSE = config.job.register

HYPERVISOR = config.job.hypervisor

HYPERVISOR_FILE = f'/etc/virt-who.d/{HYPERVISOR}.conf'

REGISTER = config.job.register


class FailException(BaseException):
    def __init__(self, error_message):
        logger.error(error_message)
