import re
import time

from virtwho import logger, FailException
from virtwho.configure import virtwho_ssh_connect
from virtwho.configure import guest_ssh_connect
from virtwho.configure import get_register_handler
from virtwho.settings import config


class SubscriptionManager:
    """"""

    def __init__(self, mode, register_type):
        """
        Define the global variables.
        :param mode: the hypervisor mode.
            (esx, xen, hyperv, rhevm, libvirt, kubevirt, local)
        :param register_type: the subscription server. (rhsm, satellite)
        """
        self.mode = mode
        self.register_type = register_type
        self.ssh_virtwho = virtwho_ssh_connect(self.mode)
        self.ssh_guest = guest_ssh_connect(self.mode)
        self.rhsm_conf = '/etc/rhsm/rhsm.conf'
        self.rhsm_conf_backup = '/backup/rhsm.conf'

        self.register_section = get_register_handler(register_type)
        self.server = self.register_section.server
        self.username = self.register_section.username
        self.password = self.register_section.password
        self.port = self.register_section.port
        self.prefix = self.register_section.prefix
        self.default_org = self.register_section.default_org
        if self.register_type == 'satellite':
            self.secondary_org = self.register_section.secondary_org
            self.activation_key = self.register_section.activation_key

    def register(self, second_org=False, activ_key=False, guest=False):
        """
        Register for virt-who host or guest by subscription-manager.
        :param second_org: extra org defined only for satellite, use
            default org as default.
        :param activ_key: activation_key
        :param guest: register for guest when define True, virt-who host
            as default.
        :return: True or raise fail.
        """
        cmd = self.register_command(second_org=second_org,
                                    activ_key=activ_key)
        ssh = self.ssh(guest=guest)
        self.rhsm_conf_set(guest=guest)
        self.satellite_cert_install(guest=guest)
        host = self.host(guest=guest)
        for i in range(3):
            self.unregister(guest=guest)
            ret, output = ssh.runcmd(cmd)
            if ret == 0 and 'The system has been registered' in output:
                logger.info(f'Succeeded to register {host}')
                return True
            elif "certificate verify failed" in output:
                cmd = "sed -i -e 's|^insecure.*|insecure = 1|g' " \
                      "/etc/rhsm/rhsm.conf"
                _, _ = ssh.runcmd(cmd)
        raise FailException(f'Failed to register {host}')

    def unregister(self, guest=False):
        """
        Uregister for virt-who host or guest by subscription-manager.
        :param guest: unregister for guest when define True, virt-who
            host as default.
        :return: True of raise fail.
        """
        ssh = self.ssh(guest=guest)
        host = self.host(guest=guest)
        for i in range(3):
            _, _ = ssh.runcmd('subscription-manager unregister')
            ret, output = ssh.runcmd('subscription-manager clean')
            if ret == 0:
                logger.info(f'Succeeded to unregister {host}')
                return True
            logger.warning(
                f'Failed to unregister {host}, try again after 180s.')
            time.sleep(180)
        raise FailException(f'Failed to unregister {host}')

    def register_command(self, second_org=False, activ_key=False):
        """
        Define subscription-manager command for registering based on the
        configured parameters.
        :param second_org: extra org defined only for satellite, use
            default org as default.
        :param activ_key: activation_key
        :return: command string
        """
        org = self.default_org
        if self.register_type == 'satellite':
            if second_org:
                org = self.secondary_org
            if activ_key:
                ack = self.activation_key
                cmd = f'subscription-manager register ' \
                      f'--org="{org}" ' \
                      f'--activationkey="{ack}"'
                return cmd
        cmd = f'subscription-manager register ' \
              f'--username={self.username} ' \
              f'--password={self.password} ' \
              f'--org={org}'
        return cmd

    def rhsm_conf_set(self, guest=False):
        """
        Configure the /etc/rhsm/rhsm.conf before registering.
        :param guest: configure for guest when guest=True, default is
            virt-who host.
        :return: None
        """
        ssh = self.ssh(guest=guest)
        _, _ = ssh.runcmd(f'rm -f {self.rhsm_conf};'
                          f'cp {self.rhsm_conf_backup} {self.rhsm_conf}')
        if self.register_type == 'rhsm':
            cmd = "sed -i -e 's|^hostname.*|hostname = {0}|g' " \
                  "/etc/rhsm/rhsm.conf".format(self.server)
            _, _ = ssh.runcmd(cmd)

    def satellite_cert_install(self, guest=False):
        """
        Install certificate when registering to satellite.
        :param guest: install cert for guest when guest=True, default is
            virt-who host.
        :return:
        """
        if 'satellite' in self.register_type:
            ssh = self.ssh(guest=guest)
            host = self.host(guest=guest)
            cmd = f'rpm -ihv http://{self.server}' \
                  f'/pub/katello-ca-consumer-latest.noarch.rpm'
            ret, _ = ssh.runcmd(cmd)
            if ret != 0:
                raise FailException(
                    f'Failed to install satellite certification for {host}')

    def sku_attach(self, pool=None, quantity=None, guest=False):
        """
        Attach subscription by Pool ID or --auto.
        :param pool: Pool ID, attach by --auto when pool=None
        :param quantity: subscription number to attach, default is auto.
        :param guest: attach for guest when guest=True, default is
            virt-who host.
        :return: tty output.
        """
        ssh = self.ssh(guest=guest)
        host = self.host(guest=guest)
        cmd = 'subscription-manager attach'
        if pool:
            cmd = f'{cmd} --pool={pool}'
        if quantity:
            cmd = f'{cmd} --quantity={quantity}'
        if not pool:
            cmd = f'{cmd} --auto'
        for i in range(3):
            self.sku_refresh(guest=guest)
            ret, output = ssh.runcmd(cmd)
            if ret == 0:
                logger.info(f'Succeeded to attach subscription for {host}')
                return output.strip()
            if "--auto" in cmd and "Unable to find available" in output:
                logger.warning(
                    f'Failed to attach subscription by auto for {host}.')
                return output.strip()
            if "Multi-entitlement not supported" in output:
                logger.warning(output)
                return output.strip()
            logger.warning('Try again to attach subscription after 180s')
            time.sleep(180)
        raise FailException(f'Failed to attach subscription for {host}')

    def sku_unattach(self, pool=None, guest=False):
        """
        Remove subscription by Pool ID or remove all.
        :param pool: Pool ID, remove all when pool=None.
        :param guest: unattach for guest when guest=True, default is
            virt-who host.
        :return: tty output
        """
        ssh = self.ssh(guest=guest)
        host = self.host(guest=guest)
        cmd = 'subscription-manager remove --all'
        if pool:
            cmd = f'subscription-manager remove --pool={pool}'
        for i in range(3):
            ret, output = ssh.runcmd(cmd)
            if ret == 0:
                logger.info(f'Succeeded to remove subscription for {host}')
                return output.strip()
            logger.warning('Try again to remove subscription after 180s ...')
            time.sleep(180)
        raise FailException(f'Failed to remove subscription for {host}')

    def sku_attributes(self, sku_name, virtual=False, guest=False):
        """
        Search and analyze an available subscription by sku name and type.
        :param sku_name: vdc/vdc_virtual/unlimit/limit/instance
        :param virtual: sku type, 'Virtual' when virtual=True, default
            is 'Physical'.
        :param guest: check on guest when guest=True, default is
            virt-who host.
        :return: a dict with sku attributes.
        """
        sku_id = self.sku_id(sku_name=sku_name)
        sku_type = self.sku_type(virtual=virtual)
        ssh = self.ssh(guest=guest)
        host = self.host(guest=guest)
        for i in range(3):
            cmd = f'subscription-manager list --av --all --matches={sku_id} |' \
                  f'tail -n +4'
            ret, output = ssh.runcmd(cmd)
            if ret == 0 and "Pool ID:" in output:
                skus = output.strip().split('\n\n')
                for sku in skus:
                    pattern_1 = r"System Type:.*%s" % sku_type
                    pattern_2 = r"Entitlement Type:.*%s" % sku_type
                    if re.search(pattern_1, sku) or re.search(pattern_2, sku):
                        logger.info(f'Succeeded to find {sku_type}:{sku_name} '
                                    f'in {host}')
                        sku_attr = self.sku_analyzer(sku)
                        return sku_attr
            logger.warning(
                f'Try again to search subscription after 180s...')
            time.sleep(180)
        logger.warning(f'Failed to find {sku_type}:{sku_name}' in {host})
        return None

    def sku_consumed(self, pool, guest=False):
        """
        List and analyze the consumed subscription by Pool ID.
        :param pool: Pool ID for checking.
        :param guest: check on guest when guest=True, default is
            virt-who host.
        :return: a dict with sku attributes.
        """
        ssh = self.ssh(guest=guest)
        host = self.host(guest=guest)
        for i in range(3):
            self.sku_refresh(guest=guest)
            ret, output = ssh.runcmd(f'subscription-manager list --co')
            if ret == 0:
                if (output is None or
                        'No consumed subscription pools were found' in output):
                    logger.info(f'No consumed subscription found in {host}.')
                    return None
                elif "Pool ID:" in output:
                    sku_attrs = output.strip().split('\n\n')
                    for attr in sku_attrs:
                        sku_attr = self.sku_analyzer(attr)
                        if sku_attr['pool_id'] == pool:
                            logger.info(f'Succeeded to get the consumed '
                                        f'subscription in {host}')
                            return sku_attr
            logger.warning(
                f'Try again to get consumed subscriptions after 180s...')
            time.sleep(180)
        logger.warning('Failed to get consumed subscriptions.')
        return None

    def sku_installed(self, guest=False):
        """
        List and analyze the installed status.
        :param guest: check for guest when guest=True, default is
            virt-who host.
        :return:
        """
        ssh = self.ssh(guest=guest)
        host = self.host(guest=guest)
        for i in range(3):
            self.sku_refresh(guest=guest)
            ret, output = ssh.runcmd(
                'subscription-manager list --installed | tail -n +4')
            if ret == 0 and output.strip() != '':
                install_attr = self.installed_analyzer(output)
                logger.info(
                    f'Succeeded to list installed subscription in {host}')
                return install_attr
            logger.warning(
                'Try again to list installed subscription after 180s...')
            time.sleep(180)
        raise FailException(f'Failed to list installed subscription in {host}')

    def installed_analyzer(self, attr):
        """
        Analyze the installed attributes to a dict.
        :param attr: output get from --installed
        :return: a dict with all installed attibutes.
        """
        install_attr = dict()
        attr = attr.strip().split('\n')
        for line in attr:
            if re.match(r"^Product Name:", line):
                product_name = line.split(':')[1].strip()
                install_attr['product_name'] = product_name
            if re.match(r"^Product ID:", line):
                product_id = line.split(':')[1].strip()
                install_attr['product_id'] = product_id
            if re.match(r"^Version:", line):
                version = line.split(':')[1].strip()
                install_attr['version'] = version
            if re.match(r"^Arch:", line):
                arch = line.split(':')[1].strip()
                install_attr['arch'] = arch
            if re.match(r"^Status:", line):
                status = line.split(':')[1].strip()
                install_attr['status'] = status
            if re.match(r"^Status Details:", line):
                status_details = line.split(':')[1].strip()
                install_attr['status_details'] = status_details
            if re.match(r"^Starts:", line):
                starts = line.split(':')[1].strip()
                install_attr['starts'] = starts
            if re.match(r"^Ends:", line):
                ends = line.split(':')[1].strip()
                install_attr['ends'] = ends
        return install_attr

    def sku_analyzer(self, attr):
        """
        Analyze the sku attributes to a dict.
        :param attr: output get from --av or --co
        :return: a dict including all sku attributes.
        """
        sku_attr = dict()
        attr = attr.strip().split("\n")
        for line in attr:
            if re.match(r"^Subscription Name:", line):
                sku_attr['sku_name'] = line.split(':')[1].strip()
            if re.match(r"^SKU:", line):
                sku_attr['sku_id'] = line.split(':')[1].strip()
            if re.match(r"^Contract:", line):
                sku_attr['contract_id'] = line.split(':')[1].strip()
            if re.match(r"^Pool ID:", line):
                sku_attr['pool_id'] = line.split(':')[1].strip()
            if re.match(r"^Available:", line):
                sku_attr['available'] = line.split(':')[1].strip()
            if re.match(r"^Suggested:", line):
                sku_attr['suggested'] = line.split(':')[1].strip()
            if re.match(r"^Service Level:", line):
                sku_attr['service_level'] = line.split(':')[1].strip()
            if re.match(r"^Service Type:", line):
                sku_attr['service_type'] = line.split(':')[1].strip()
            if re.match(r"^Subscription Type:", line):
                sku_attr['sub_type'] = line.split(':')[1].strip()
                if 'Temporary' in sku_attr['sub_type']:
                    sku_attr['temporary'] = True
                else:
                    sku_attr['temporary'] = False
            if re.match(r"^Ends:", line):
                sku_attr['ends'] = line.split(':')[1].strip()
            if (re.match(r"^System Type:", line)
                    or re.match(r"^Entitlement Type:", line)):
                sku_attr['sku_type'] = line.split(':')[1].strip()
        return sku_attr

    def sku_refresh(self, guest=False):
        """
        Refresh subscription by command 'subscription-manager refresh'.
        :param guest: refresh for guest when define True, default is
            virt-who host.
        :return: True or raise fail.
        """
        ssh = self.ssh(guest=guest)
        host = self.host(guest=guest)
        for i in range(3):
            ret, output = ssh.runcmd('subscription-manager refresh')
            if ret == 0:
                logger.info(f'Succeeded to refresh subscription for {host}')
                return True
            logger.warning('Try again to refresh subscription after 180s...')
            time.sleep(180)
        raise FailException(f'Failed to refresh subscription for {host}')

    def custom_facts_create(self, key, value, guest=False):
        """
        Create subscription facts to /etc/rhsm/facts/custom.facts.
        :param key: fact key
        :param value: fact value
        :param guest: create facts for guest when define True, default
            is virt-who host.
        :return: True or raise fail.
        """
        ssh = self.ssh(guest=guest)
        host = self.host(guest=guest)
        option = f'{{"{key}":"{value}"}}'
        _, _ = ssh.runcmd(f"echo '{option}' > /etc/rhsm/facts/custom.facts")
        for i in range(3):
            _, _ = ssh.runcmd('subscription-manager facts --update')
            # time sleep for task conflicts
            time.sleep(60)
            ret, output = ssh.runcmd(
                f"subscription-manager facts --list |grep '{key}:'")
            if ret == 0 and key in output:
                actual_value = output.split(": ")[1].strip()
                if actual_value == value:
                    logger.info(
                        f'Succeeded to create custom facts with '
                        f'{key}:{value} for {host}')
                    return True
        raise FailException(f'Failed to create custom facts for {host}')

    def custom_facts_remove(self, guest=False):
        """
        Remove subscription facts.
        :param guest: do for guest when define True, default is virt-who host.
        :return: True or raise fail.
        """
        ssh = self.ssh(guest=guest)
        host = self.host(guest=guest)
        _, _ = ssh.runcmd('rm -f /etc/rhsm/facts/custom.facts')
        for i in range(3):
            ret, output = ssh.runcmd('subscription-manager facts --update')
            time.sleep(60)
            if ret == 0 and 'Successfully updated' in output:
                logger.info(f'Succeeded to remove custom.facts for {host}')
                return True
            logger.warning('Try again to remove custom.facts after 60s...')
            time.sleep(60)
        raise FailException(f'Failed to remove custom.facts for {host}')

    def ssh(self, guest=False):
        """
        Select which host to connect, virt-who host or guest.
        :param guest: connect the guest when guest=True, default is
            virt-who host.
        :return: ssh
        """
        ssh = self.ssh_virtwho
        if guest:
            ssh = self.ssh_guest
        return ssh

    def host(self, guest=False):
        """
        Mark the host with "virt-who" or "guest" for logger distinguish.
        :param guest: mark 'guest host' when guest=True, default is
            'virt-who host'.
        :return: the mark to host
        """
        host = 'virt-who host'
        if guest:
            host = 'guest host'
        return host

    def sku_id(self, sku_name):
        """
        Get the sku id by sku name.
        :param sku_name: vdc/vdc_virtual/unlimit/limit/instance
        :return: RH00001/RH00049/RH00060/RH00204/RH00003
        """
        if sku_name == 'vdc':
            return config.sku.vdc
        if sku_name == 'vdc_virtual':
            return config.sku.vdc_virtual
        if sku_name == 'unlimit':
            return config.sku.unlimit
        if sku_name == 'limit':
            return config.sku.limit
        if sku_name == 'instance':
            return config.sku.instance

    def sku_type(self, virtual=False):
        """
        Get the sku type for searching.
        :param virtual: 'Virtual' when define True, default is 'Physical'
        :return: 'Physical' or 'Virtual'
        """
        if virtual:
            return 'Virtual'
        return 'Physical'


class RHSMAPI:
    def __init__(self):
        pass


class SatelliteCLI:
    def __init__(self):
        pass
