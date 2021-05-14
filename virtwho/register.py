import json
import time
from virtwho import logger, FailException
from virtwho.settings import config
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
        if 'satellite' in self.register_type:
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

    def available(self, sku_id, sku_type='Virtual'):
        """
        Search and analyze an available subscription by name and type.
        :param sku_id: sku id, such as RH00001
        :param sku_type: 'Physical' or 'Virtual'.
        :return: a dict with sku attributes.
        """
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


class RHSMAPI:

    def __init__(self, host, username, password, port=22):
        """
        Using rhsm api to check/get/delete consumers,  attach/remove
        subscription, and check the host-to-guest associations.
        :param host: ip/hostname to run curl command.
        :param username: account username of the host
        :param password: password to access the host
        :param port: port to access the host
        """
        self.ssh = SSHConnect(host=host, user=username, pwd=password, port=port)
        self.server = config.rhsm.server
        self.username = config.rhsm.username
        self.password = config.rhsm.password
        self.org = config.rhsm.default_org
        self.api = f'https://{self.server}/subscription'
        self.curl_base = f'curl -s -k -u {self.username}:{self.password}'

    def consumers(self, host_name=None):
        """
        Search consumer host information.
        :param host_name: host name, search all consumers if host_name=None.
        :return: one consumer or all consumers to a list.
        """
        cmd = f'{self.curl_base} {self.api}/owners/{self.org}/consumers'
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and output:
            consumers = json.loads(output.strip())
            if host_name:
                for consumer in consumers:
                    if host_name in consumer['name'].strip():
                        return consumer
            else:
                return consumers
        return None

    def uuid(self, host_name):
        """
        Get the consumer uuid by host name
        :param host_name: host name
        :return: consumer uuid or None
        """
        consumer = self.consumers(host_name)
        if consumer:
            uuid = consumer['uuid'].strip()
            logger.info(f'Succeeded to get stage consumer uuid: '
                        f'{host_name}:{uuid}')
            return uuid
        raise FailException(
            f'Failed to get stage consumer uuid for {host_name}')

    def get(self, host_name):
        """
        Get the consumer host information by host name, including the
        detail facts info.
        :param host_name: host name
        :return: output to a dic
        """
        uuid = self.uuid(host_name)
        cmd = f'{self.curl_base} -X GET {self.api}/consumers/{uuid}'
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and output:
            output = json.loads(output.strip())
            logger.info(f'Succeeded to get host display name: '
                        f'{output["name"]}')
            return output
        raise FailException(f'Failed to get {host_name} information on stage')

    def delete(self, host_name=None):
        """
        Delete only one consumer or clean all consumers.
        :param host_name: host name, will clean all consumers if host_name=None.
        :return: True
        """
        consumers = self.consumers()
        if consumers:
            for consumer in consumers:
                uuid = consumer['uuid'].strip()
                if not host_name or \
                        (host_name and host_name in consumer['name'].strip()):
                    self.ssh.runcmd(f'{self.curl_base} -X DELETE '
                                    f'{self.api}/consumers/{uuid}')
            if not self.consumers(host_name=host_name):
                logger.info('Succeeded to delete consumer on stage')
                return True
            raise FailException('Failed to delete consumer on stage')
        logger.info('No consumers found on stage')
        return True

    def pool(self, sku_id):
        """
        Get the pool id by sku id
        :param sku_id: sku id
        :return: pool id
        """
        ret, output = self.ssh.runcmd(f'{self.curl_base} -X GET '
                                      f'{self.api}/owners/{self.org}/pools')
        if ret == 0 and output:
            pools = json.loads(output.strip())
            for pool in pools:
                if sku_id in pool['productId']:
                    return pool['id'].strip()
        raise FailException(f'Failed to get pool id for {sku_id}')

    def attach(self, host_name, pool=None):
        """
        Attach subscription for host by auto or pool_id.
        :param host_name: host name
        :param pool: pool id, will attach by auto when pool_id=None
        """
        if self.entitlements(host_name, pool=pool):
            self.unattach(host_name)
        uuid = self.uuid(host_name)
        cmd = f'{self.curl_base} -X POST ' \
              f'{self.api}/consumers/{uuid}/entitlements'
        if pool:
            cmd = f'{self.curl_base} -X POST ' \
                  f'{self.api}/consumers/{uuid}/entitlements?pool={pool}'
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and self.entitlements(host_name, pool=pool):
            logger.info(f'Succeeded to attach pool for {host_name}')
        else:
            raise FailException(f'Failed to attach pool for {host_name}')

    def unattach(self, host_name, pool=None):
        """
        Remove subscription for consumer.
        :param host_name: host name
        :param pool: pool id, remove all subscriptions when pool=None
        """
        uuid = self.uuid(host_name)
        cmd = f'{self.curl_base} -X DELETE ' \
              f'{self.api}/consumers/{uuid}/entitlements'
        if pool:
            entitlement_id = self.entitlement_id(host_name=host_name, pool=pool)
            cmd = f'{self.curl_base} -X DELETE ' \
                  f'{self.api}/consumers/{uuid}/entitlements/{entitlement_id}'
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and not self.entitlements(host_name, pool=pool):
            logger.info(f'Succeeded to remove pool for {host_name}')
        else:
            raise FailException(f'Failed to remove pool for {host_name}')

    def entitlements(self, host_name, pool=None):
        """
        Check the entitlement/subscribe status.
        :param host_name: host name
        :param pool: pool id for searching
        :return: output/None
        """
        uuid = self.uuid(host_name)
        cmd = f'{self.curl_base} -X GET ' \
              f'{self.api}/consumers/{uuid}/entitlements'
        _, output = self.ssh.runcmd(cmd)
        if (pool and pool in output) or (not pool and 'pool' in output):
            return output
        return None

    def entitlement_id(self, host_name, pool):
        """
        Get the entitlement id, one pool may have several entitlement ids.
        :param host_name: host name
        :param pool: pool id
        :return: entitlement id
        """
        entitlements = self.entitlements(host_name=host_name)
        if entitlements:
            entitlements = json.loads(entitlements.strip())
            for item in entitlements:
                if pool in item['pool']['id']:
                    return item['id']
        raise FailException(
            f'Failed to get the entitlement id for {pool} on {host_name}')

    def associate(self, host_name, guest_uuid):
        """
        Check the host/hypervisor is associated with guest or not.
        :param host_name: host name
        :param guest_uuid: guest uuid
        :return: True/False
        """
        uuid = self.uuid(host_name)
        cmd = f'{self.curl_base} {self.api}/consumers/{uuid}/guestids'
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and guest_uuid in output:
            logger.info("Hypervisor and Guest are associated on stage web")
            return True
        logger.warning("Hypervisor and Guest are not associated on stage web")
        return False


class SatelliteCLI:
    def __init__(self):
        pass
