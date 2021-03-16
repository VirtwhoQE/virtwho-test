"""
Used to manage virt-who configure file
Add/Delete/Update options for /etc/virt-who.conf, /etc/virt-who.d/xxx.conf
"""
from virtwho.settings import Configure


class VirtwhoHypervisorConfig:
    def __init__(self, mode):
        config = Configure('properties.ini')
        self.remote_ssh = {'host': config.get('virtwho', 'host'),
                           'user': config.get('virtwho', 'username'),
                           'pwd': config.get('virtwho', 'password')}
        self.local_file = f"{mode}.conf"
        self.remote_file = f"/etc/virt-who.d/{mode}.conf"
        self.section = f'virtwho-{mode}'
        self.cfg = Configure(self.local_file, self.remote_ssh, self.remote_file)

    def get(self, option):
        """Read an option from a section"""
        return self.cfg.get(self.section, option)

    def update(self, option, value):
        """Update an option's value."""
        self.cfg.update(self.section, option, value)
        self.cfg.put()

    def delete(self, option):
        """Delete an option"""
        self.cfg.delete(self.section, option)
        self.cfg.put()

    def destroy(self):
        """Delete a file"""
        self.cfg.rm_remote_file()
