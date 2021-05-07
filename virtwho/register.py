import time
from virtwho import logger, FailException
from virtwho.configure import get_register_handler
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
        register = get_register_handler(register_type)
        self.server = register.server
        self.username = register.username
        self.password = register.password
        self.port = register.port
        self.prefix = register.prefix
        self.org = org or register.default_org
        self.activation_key = activation_key or register.activation_key

    def register(self):
        """
        Register host by subscription-manager command
        """
        self.unregister()
        cmd = f'subscription-manager register ' \
              f'--serverurl={self.server}:{self.port}{self.prefix} ' \
              f'--org={self.org} '
        if 'satellite' in self.register_type and self.activation_key:
            cmd += f'--activationkey={self.activation_key} '
        else:
            cmd += f'--username={self.username} ' \
                   f'--password={self.password} '
        self.satellite_cert_install()
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and 'The system has been registered' in output:
            logger.info(f'Succeeded to register host')
            return output
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

    def attach(self, pool=None, quantity=None):
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
        self.refresh()
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

    def unattach(self, pool=None):
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

    def available(self, sku_id, virtual=False):
        """
        Search and analyze an available subscription by name and type.
        :param sku_id: sku id, such as RH00001
        :param virtual: sku type, 'Physical' or 'Virtual'.
        :return: a dict with sku attributes.
        """
        sku_type = self.sku_type(virtual=virtual)
        cmd = f'subscription-manager list --av --all --matches={sku_id} |' \
              f'tail -n +4'
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and "Pool ID:" in output:
            skus = output.strip().split('\n\n')
            for sku in skus:
                sku_attr = self.attr_analyzer(sku)
                if 'system_type' in sku_attr.keys():
                    sku_attr['sku_type'] = sku_attr['system_type']
                else:
                    sku_attr['sku_type'] = sku_attr['entitlement_type']
                if sku_attr['sku_type'] == sku_type:
                    logger.info(f'Succeeded to find {sku_type}:{sku_id} '
                                f'in {self.host}')
                    if '(Temporary)' in sku_attr['subscription_type']:
                        sku_attr['temporary'] = True
                    else:
                        sku_attr['temporary'] = False
                    return sku_attr
        logger.warning(f'Failed to find {sku_type}:{sku_id}' in {self.host})
        return None

    def consumed(self, pool):
        """
        List and analyze the consumed subscription by Pool ID.
        :param pool: Pool ID for checking.
        :return: a dict with sku attributes.
        """
        self.refresh()
        ret, output = self.ssh.runcmd(f'subscription-manager list --co')
        if ret == 0:
            if (output is None or
                    'No consumed subscription pools were found' in output):
                logger.info(f'No consumed subscription found in {self.host}.')
                return None
            elif "Pool ID:" in output:
                sku_attrs = output.strip().split('\n\n')
                for attr in sku_attrs:
                    sku_attr = self.attr_analyzer(attr)
                    if sku_attr['pool_id'] == pool:
                        logger.info(f'Succeeded to get the consumed '
                                    f'subscription in {self.host}')
                        if '(Temporary)' in sku_attr['subscription_type']:
                            sku_attr['temporary'] = True
                        else:
                            sku_attr['temporary'] = False
                        return sku_attr
        logger.warning('Failed to get consumed subscriptions.')
        return None

    def installed(self):
        """
        List products which are currently installed on the system and
        analyse the result.
        """
        self.refresh()
        ret, output = self.ssh.runcmd(
            'subscription-manager list --installed | tail -n +4')
        if ret == 0 and output.strip() != '':
            install_attr = self.attr_analyzer(output)
            logger.info(
                f'Succeeded to list installed subscription for {self.host}')
            return install_attr
        raise FailException(
            f'Failed to list installed subscription for {self.host}')

    def refresh(self):
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

    def attr_analyzer(self, attr):
        """
        Analyze the output attributes to a dict, like the output from
        command "subscription-manager list --in/co/av"
        :param attr: the output including several lines, which lines are
            {string}:{string} format.
        :return: a dict
        """
        attr_data = dict()
        attr = attr.strip().split('\n')
        for line in attr:
            if ':' not in line:
                continue
            line = line.split(':')
            key = line[0].strip().replace(' ', '_').lower()
            value = line[1].strip()
            attr_data[key] = value
        return attr_data

    def facts_create(self, key, value):
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

    def facts_remove(self):
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


class RHSMAPI:
    def __init__(self):
        pass


class SatelliteCLI:
    def __init__(self):
        pass
