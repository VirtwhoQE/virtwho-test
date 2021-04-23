import re
import time

from virtwho import logger, FailException
from virtwho.configure import get_register_handler
from virtwho.settings import config
from virtwho.ssh import SSHConnect


class SubscriptionManager:

    def __init__(self, host, username, password, port=22, register_type='rhsm',
                 org=None, activation_key=None):
        """
        Define the global variables.
        :param host: ip/hostname to run subscription-manager command.
        :param username: account username of the host
        :param password: password to access the host
        :param port: port to access the host
        :param register_type: rhsm or satellite, rhsm as default
        :param org: organization of the entitlement server
        :param activation_key: activation_key of the entitlement server
        """
        self.host = host
        self.register_type = register_type
        self.rhsm_conf = '/etc/rhsm/rhsm.conf'
        self.ssh = SSHConnect(host=host, user=username, pwd=password, port=port)
        self.registe = get_register_handler(register_type)
        self.server = self.registe.server
        self.username = self.registe.username
        self.password = self.registe.password
        self.port = self.registe.port
        self.prefix = self.registe.prefix
        self.org = org or self.registe.default_org
        if 'satellite' in register_type:
            self.activation_key = activation_key or self.registe.activation_key

    def register(self):
        """
        Register host by subscription-manager command
        """
        cmd = f'subscription-manager register ' \
              f'--serverurl={self.server}:{self.port}{self.prefix} ' \
              f'--username={self.username} ' \
              f'--password={self.password} ' \
              f'--org={self.org} '
        if self.activation_key:
            cmd += f'--activationkey={self.activation_key} '
        self.satellite_cert_install()
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and 'The system has been registered' in output:
            logger.info(f'Succeeded to register host')
        else:
            raise FailException(f'Failed to register {self.host}')

    def unregister(self):
        """
        Unregister and clean host by subscription-manager.
        """
        ret, _ = self.ssh.runcmd('subscription-manager unregister;'
                                 'subscription-manager clean')
        if ret == 0:
            logger.info(f'Succeeded to unregister host')
        else:
            raise FailException(f'Failed to unregister {self.host}')

    def satellite_cert_install(self):
        """
        Install certificate when registering to satellite.
        """
        if 'satellite' in self.register_type:
            cmd = f'rpm -ihv http://{self.server}' \
                  f'/pub/katello-ca-consumer-latest.noarch.rpm'
            ret, _ = self.ssh.runcmd(cmd)
            if ret != 0:
                raise FailException(
                    f'Failed to install satellite certification for {self.host}')

    def sku_attach(self, pool=None, quantity=None):
        """
        Attach subscription by Pool ID or --auto.
        :param pool: Pool ID, attach by --auto when pool=None
        :param quantity: subscription number to attach, default is auto.
        :return: tty output.
        """
        cmd = 'subscription-manager attach '
        if pool:
            cmd += f'--pool={pool} '
        if quantity:
            cmd += f'--quantity={quantity}'
        if not pool:
            cmd += f'--auto '
        self.sku_refresh()
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0:
            logger.info(f'Succeeded to attach subscription for {self.host}')
            return output.strip()
        if '--auto' in cmd and 'Unable to find available' in output:
            logger.warning(
                f'Failed to attach subscription by auto for {self.host}.')
            return output.strip()
        if 'Multi-entitlement not supported' in output:
            logger.warning(output)
            return output.strip()
        else:
            raise FailException(f'Failed to attach subscription for {self.host}')

    def sku_unattach(self, pool=None):
        """
        Remove subscription by Pool ID or remove all.
        :param pool: Pool ID, remove all when pool=None.
        """
        cmd = 'subscription-manager remove --all'
        if pool:
            cmd = f'subscription-manager remove --pool={pool}'
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0:
            logger.info(f'Succeeded to remove subscription for {self.host}')
        else:
            raise FailException(f'Failed to remove subscription for {self.host}')

    def sku_attributes(self, sku_name, virtual=False):
        """
        Search and analyze an available subscription by name and type.
        :param sku_name: sku name configured in virtwho.ini - [sku].
        :param virtual: sku type, 'Physical' or 'Virtual'.
        :return: a dict with sku attributes.
        """
        sku_id = self.sku_id(sku_name=sku_name)
        sku_type = self.sku_type(virtual=virtual)
        cmd = f'subscription-manager list --av --all --matches={sku_id} |' \
              f'tail -n +4'
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and "Pool ID:" in output:
            skus = output.strip().split('\n\n')
            for sku in skus:
                pattern_1 = r'System Type:.*%s' % sku_type
                pattern_2 = r'Entitlement Type:.*%s' % sku_type
                if re.search(pattern_1, sku) or re.search(pattern_2, sku):
                    logger.info(f'Succeeded to find {sku_type}:{sku_name} '
                                f'in {self.host}')
                    sku_attr = self.sku_analyzer(sku)
                    return sku_attr
        logger.warning(f'Failed to find {sku_type}:{sku_name}' in {self.host})
        return None

    def sku_consumed(self, pool):
        """
        List and analyze the consumed subscription by Pool ID.
        :param pool: Pool ID for checking.
        :return: a dict with sku attributes.
        """
        self.sku_refresh()
        ret, output = self.ssh.runcmd(f'subscription-manager list --co')
        if ret == 0:
            if (output is None or
                    'No consumed subscription pools were found' in output):
                logger.info(f'No consumed subscription found in {self.host}.')
                return None
            elif "Pool ID:" in output:
                sku_attrs = output.strip().split('\n\n')
                for attr in sku_attrs:
                    sku_attr = self.sku_analyzer(attr)
                    if sku_attr['pool_id'] == pool:
                        logger.info(f'Succeeded to get the consumed '
                                    f'subscription in {self.host}')
                        return sku_attr
        logger.warning('Failed to get consumed subscriptions.')
        return None

    def sku_installed(self):
        """
        List products which are currently installed on the system and
        analyse the result.
        """
        self.sku_refresh()
        ret, output = self.ssh.runcmd(
            'subscription-manager list --installed | tail -n +4')
        if ret == 0 and output.strip() != '':
            install_attr = self.installed_analyzer(output)
            logger.info(
                f'Succeeded to list installed subscription for {self.host}')
            return install_attr
        raise FailException(
            f'Failed to list installed subscription for {self.host}')

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

    def sku_refresh(self):
        """
        Refresh subscription by command 'subscription-manager refresh'.
        """
        for i in range(3):
            ret, output = self.ssh.runcmd('subscription-manager refresh')
            if ret == 0:
                logger.info(f'Succeeded to refresh subscription')
                return True
            logger.warning('Try again to refresh subscription after 180s...')
            time.sleep(180)
        raise FailException(f'Failed to refresh subscription for {self.host}')

    def custom_facts_create(self, key, value):
        """
        Create subscription facts to /etc/rhsm/facts/custom.facts.
        :param key: fact key
        :param value: fact value
        """
        option = f'{{"{key}":"{value}"}}'
        ret, output = self.ssh.runcmd(
            f"echo '{option}' > /etc/rhsm/facts/custom.facts ;"
            f"subscription-manager facts --update")
        if ret == 0 and 'Successfully updated' in output:
            time.sleep(60)
            ret, output = self.ssh.runcmd(
                f"subscription-manager facts --list |grep '{key}:'")
            if ret == 0 and key in output:
                actual_value = output.split(": ")[1].strip()
                if actual_value == value:
                    logger.info(
                        f'Succeeded to create custom facts with for {self.host}')
        else:
            raise FailException(
                f'Failed to create custom facts for {self.host}')

    def custom_facts_remove(self):
        """
        Remove subscription facts.
        """
        ret, output = self.ssh.runcmd('rm -f /etc/rhsm/facts/custom.facts;'
                                      'subscription-manager facts --update')
        time.sleep(60)
        if ret == 0 and 'Successfully updated' in output:
            logger.info(f'Succeeded to remove custom.facts for {self.host}')
        else:
            raise FailException(
                f'Failed to remove custom.facts for {self.host}')

    def sku_type(self, virtual=False):
        """
        Get the sku type for searching.
        :param virtual: 'Virtual' when define True, default is 'Physical'
        :return: 'Physical' or 'Virtual'
        """
        if virtual:
            return 'Virtual'
        return 'Physical'

    def sku_id(self, sku_name):
        """
        Get the sku id by sku name.
        :param sku_name: vdc/vdc_virtual/unlimit/limit/instance
        :return: the sku_id
        """
        if sku_name == 'vdc':
            return config.sku.vdc
        if sku_name == 'vdc_virtual':
            return config.sku.vdc_virtual


class RHSMAPI:
    def __init__(self):
        pass


class SatelliteCLI:
    def __init__(self):
        pass
