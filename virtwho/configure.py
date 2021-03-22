import os
from virtwho.settings import Configure
from virtwho.settings import config
from virtwho.settings import TEMP_DIR
from virtwho.ssh import SSHConnect
from virtwho.logger import getLogger

logger = getLogger(__name__)


class VirtwhoHypervisorConfig:
    """Able to create and manage /etc/virt-who.d/xxx.conf file when
    call this class"""
    def __init__(self, mode='esx', register_type='rhsm'):
        """Create virt-who configuration file with basic options.
         All data come from virtwho.ini file.
        :param mode: The hypervisor mode.
            (esx, xen, hyperv, rhevm, libvirt, kubevirt, local)
        :param register_type: The subscription server. (rhsm, satellite)
        """
        self.mode = mode
        self.register_type = register_type
        self.remote_ssh = virtwho_ssh_connect(self.mode)
        self.local_file = os.path.join(TEMP_DIR, f'{self.mode}.conf')
        self.remote_file = f'/etc/virt-who.d/{self.mode}.conf'
        self.section = f'virtwho-{self.mode}'
        self.cfg = Configure(self.local_file, self.remote_ssh, self.remote_file)
        if self.mode == 'local':
            self.update('type', 'libvirt')
        else:
            if self.register_type == 'rhsm':
                register = config.rhsm
            elif self.register_type == 'satellite':
                register = config.satellite
            if self.mode == 'esx':
                hypervisor = config.vcenter
            elif self.mode == 'xen':
                hypervisor = config.xen
            elif self.mode == 'hyperv':
                hypervisor = config.hyperv
            elif self.mode == 'rhevm':
                hypervisor = config.rhevm
            elif self.mode == 'libvirt':
                hypervisor = config.libvirt
            elif self.mode == 'kubevirt':
                hypervisor = config.kubevirt
            self.update('type', self.mode)
            self.update('hypervisor_id', 'hostname')
            self.update('owner', register.default_org)
            if self.mode == 'kubevirt':
                self.update('kubeconfig', hypervisor.config_file)
            else:
                self.update('server', hypervisor.server)
                self.update('username', hypervisor.username)
                self.update('password', hypervisor.password)

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
        """Remove both the local and remote files"""
        os.remove(self.local_file)
        self.remote_ssh.remove_file(self.remote_file)


class VirtwhoGlobalConfig:
    """Able to manage /etc/virt-who.conf file when call this class"""
    def __init__(self, mode=None):
        """
        :param mode: Hypervisor mode. When mode is local, will manage
            the local libvirt host, othervise will manage the host for
            all other remote modes.
        """
        self.mode = mode
        self.remote_ssh = virtwho_ssh_connect(self.mode)
        self.local_file = os.path.join(TEMP_DIR, 'virt-who.conf')
        self.remote_file = '/etc/virt-who.conf'
        self.save_file = os.path.join(TEMP_DIR, 'virt-who.conf.save')
        if not os.path.exists(self.save_file):
            self.remote_ssh.get_file(self.remote_file, self.save_file)
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
    virtwho = config.virtwho
    if mode == 'local':
        virtwho = config.local
    host = virtwho.host
    username = virtwho.username
    password = virtwho.password
    if mode == 'local' or not virtwho.port:
        return SSHConnect(host, user=username, pwd=password)
    else:
        return SSHConnect(host, user=username, pwd=password,
                          port=int(virtwho.port))
