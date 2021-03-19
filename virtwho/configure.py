from virtwho.settings import Configure
from virtwho.settings import config
from virtwho.ssh import SSHConnect
from virtwho.logger import getLogger

logger = getLogger(__name__)


class VirtwhoHypervisorConfig:
    """Able to create and manage /etc/virt-who.d/xxx.conf file when
    call this class"""
    def __init__(self, mode, register):
        """Create virt-who configuration file with basic options.
         All data come from virtwho.ini file.
        :param mode: The hypervisor mode.
            (esx, xen, hyperv, rhevm, libvirt, kubevirt, local)
        :param register: The subscription server. (rhsm, satellite)
        """
        self.remote_ssh = virtwho_ssh_connect(mode)
        self.local_file = f'/root/{mode}.conf'
        self.remote_file = f'/etc/virt-who.d/{mode}.conf'
        self.section = f'virtwho-{mode}'
        self.cfg = Configure(self.local_file, self.remote_ssh, self.remote_file)
        if mode == 'local':
            logger.info("Don't need to configure for local mode")
        else:
            self.update('type', mode)
            if mode == 'esx':
                self.update('server', config.vcenter.server)
                self.update('username', config.vcenter.username)
                self.update('password', config.vcenter.password)
            elif mode == 'xen':
                self.update('server', config.xen.server)
                self.update('username', config.xen.username)
                self.update('password', config.xen.password)
            elif mode == 'hyperv':
                self.update('server', config.hyperv.server)
                self.update('username', config.hyperv.username)
                self.update('password', config.hyperv.password)
            elif mode == 'rhevm':
                self.update('server', config.rhevm.server)
                self.update('username', config.rhevm.username)
                self.update('password', config.rhevm.password)
            elif mode == 'libvirt':
                self.update('server', config.libvirt.server)
                self.update('username', config.libvirt.username)
                self.update('password', config.libvirt.password)
            elif mode == 'kubevirt':
                self.update('kubeconfig', config.mode.config_file)
            if register == "rhsm":
                self.update('owner', config.rhsm.default_org)
            elif register == 'satellite':
                self.update('owner', config.satellite.default_org)
            self.update('hypervisor_id', 'hostname')

    def update(self, option, value):
        """Add or update an option
        :param option: Option will be added if not exist.
        :param value: Value to update for the option.
        """
        self.cfg.update(self.section, option, value)

    def delete(self, option):
        """Delete an option
        :param option: Option to remove.
        """
        self.cfg.delete(self.section, option)

    def destroy(self):
        """Remove the /etc/virt-who.d/{mode}.conf file"""
        self.remote_ssh.remove_file(self.remote_file)


class VirtwhoGlobalConfig:
    """Able to manage /etc/virt-who.conf file when call this class"""
    def __init__(self, mode=None):
        """
        :param mode: Hypervisor mode. When mode is local, will manage
            the local libvirt host, othervise will manage the host for
            all other remote modes.
        """
        self.remote_ssh = virtwho_ssh_connect(mode)
        self.local_file = '/root/virt-who.conf'
        self.remote_file = '/etc/virt-who.conf'
        self.cfg = Configure(self.local_file, self.remote_ssh, self.remote_file)

    def update(self, section, option, value):
        """Add section, add option or update option
        :param section: Section will be added if not exist.
        :param option: Option will be added if not exist.
        :param value: Value to update for the option.
        """
        self.cfg.update(section, option, value)

    def delete(self, section, option=None):
        """Remove a section or option
        :param section: Section will be removed when no option provided.
        :param option: Option to remove.
        """
        self.cfg.delete(section, option)


def virtwho_ssh_connect(mode=None):
    """Define the ssh connection of virt-who host, get data from
    virtwho.ini file.
    :param mode: The test hypervisor mode.
    """
    if mode == 'local':
        host = config.local.host
        username = config.local.username
        password = config.local.password
    else:
        host = config.virtwho.host
        username = config.virtwho.username
        password = config.virtwho.password
    return SSHConnect(host, user=username, pwd=password)
