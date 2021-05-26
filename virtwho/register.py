import json
import time
import requests

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
        self.org = config.rhsm.default_org
        self.api = f'https://{config.rhsm.server}/subscription'
        self.auth = (config.rhsm.username, config.rhsm.password)

    def consumers(self, host_name=None):
        """
        Search consumer host information.
        :param host_name: host name, search all consumers if host_name=None.
        :return: one consumer or all consumers to a list.
        """
        res = requests.get(url=f'{self.api}/owners/{self.org}/consumers',
                           auth=self.auth, verify=False)
        if res.status_code == 200:
            consumers = res.json()
            if host_name:
                for consumer in consumers:
                    if host_name in consumer['name']:
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
            uuid = consumer['uuid']
            logger.info(f'Succeeded to get stage consumer uuid: '
                        f'{host_name}:{uuid}')
            return uuid
        raise FailException(
            f'Failed to get stage consumer uuid for {host_name}')

    def info(self, host_name):
        """
        Get the consumer host information by host name, including the
        detail facts info.
        :param host_name: host name
        :return: output to a dic
        """
        uuid = self.uuid(host_name)
        res = requests.get(url=f'{self.api}/consumers/{uuid}',
                           auth=self.auth, verify=False)
        if res.status_code == 200:
            logger.info(f'Succeeded to get consumer info for {host_name}')
            return res.json()
        raise FailException(f'Failed to get consumer info for {host_name}')

    def delete(self, host_name=None):
        """
        Delete only one consumer or clean all consumers.
        :param host_name: host name, will clean all consumers if host_name=None.
        :return: True or Fail
        """
        consumers = self.consumers()
        if consumers:
            for consumer in consumers:
                uuid = consumer['uuid']
                if (
                        not host_name
                        or
                        (host_name and host_name in consumer['name'])
                ):
                    requests.delete(url=f'{self.api}/consumers/{uuid}',
                                    auth=self.auth, verify=False)
            if not self.consumers(host_name=host_name):
                logger.info('Succeeded to delete consumer(s) on stage')
                return True
            raise FailException('Failed to delete consumer(s) on stage')
        logger.info('Succeeded to delete consumer(s) on stage '
                    'because no consumer found')
        return True

    def pool(self, sku_id):
        """
        Get the pool id by sku id
        :param sku_id: sku id
        :return: pool id
        """
        res = requests.get(url=f'{self.api}/owners/{self.org}/pools',
                           auth=self.auth, verify=False)
        if res.status_code == 200 and res.json():
            for item in res.json():
                if sku_id in item['productId']:
                    return item['id']
        raise FailException(f'Failed to get pool id for {sku_id}')

    def attach(self, host_name, pool=None):
        """
        Attach subscription for host by auto or pool_id.
        :param host_name: host name
        :param pool: pool id, will attach by auto when pool_id=None
        """
        uuid = self.uuid(host_name)
        if self.entitlements(host_name, pool=pool):
            self.unattach(host_name, pool=pool)
        params = ''
        if pool:
            params = (('pool', pool),)
        requests.post(url=f'{self.api}/consumers/{uuid}/entitlements',
                      params=params, auth=self.auth, verify=False)
        if self.entitlements(host_name, pool=pool):
            logger.info(f'Succeeded to attach pool for {host_name}')
        else:
            raise FailException(f'Failed to attach pool for {host_name}')

    def unattach(self, host_name, pool=None):
        """
        Remove all subscriptions or the specified one for consumer.
        :param host_name: pool id, remove all subscriptions when pool=None
        :param pool: pool id
        """
        uuid = self.uuid(host_name)
        url = f'{self.api}/consumers/{uuid}/entitlements'
        if pool:
            entitlement_id = self.entitlements(host_name=host_name, pool=pool)
            url = f'{self.api}/consumers/{uuid}/entitlements/{entitlement_id}'
        requests.delete(url=url, auth=self.auth, verify=False)
        if not self.entitlements(host_name, pool=pool):
            logger.info(f'Succeeded to remove pool(s) for {host_name}')
        else:
            raise FailException(f'Failed to remove pool(s) for {host_name}')

    def entitlements(self, host_name, pool=None):
        """
        Get entitlement id for each pool or the only one for the defined pool.
        :param host_name: host name
        :param pool: pool id, get all entitlement id when pool=None
        :return: entitlement id
        """
        uuid = self.uuid(host_name)
        res = requests.get(url=f'{self.api}/consumers/{uuid}/entitlements',
                           auth=self.auth, verify=False)
        if res.status_code == 200:
            entitlement_ids = dict()
            for item in res.json():
                pool_id = item['pool']['id']
                entitlement_ids[pool_id] = item['id']
            if pool:
                if pool in entitlement_ids.keys():
                    return entitlement_ids[pool]
                return None
            return entitlement_ids
        raise FailException(
            f'Failed to get entitlement info for {host_name}')

    def associate(self, host_name, guest_uuid):
        """
        Check the host/hypervisor is associated with guest or not.
        :param host_name: host name
        :param guest_uuid: guest uuid
        :return: True/False
        """
        uuid = self.uuid(host_name)
        res = requests.get(url=f'{self.api}/consumers/{uuid}/guestids',
                           auth=self.auth, verify=False)
        if res.status_code == 200 and guest_uuid in res.text:
            logger.info("Hypervisor and Guest are associated on stage web")
            return True
        logger.warning("Hypervisor and Guest are not associated on stage web")
        return False


class SatelliteCLI:

    def __init__(self, org=None, activation_key=None):
        """
        Using hammer command to set satellite, handle organization and
        activation key, attach/remove subscription for host, and check
        the host-to-guest associations.
        :param org: organization label, use the default_org configured
            in virtwho.ini as default.
        :param activation_key: activation key name, use the configure
            in virtwho.ini as default.
        """
        register = get_register_handler('satellite')
        self.org = org or register.default_org
        self.activation_key = activation_key or register.activation_key
        self.ssh = SSHConnect(host=register.server,
                              user=register.ssh_username,
                              pwd=register.ssh_password)
        self.org_id = self.org_id()

    def org_id(self, org=None):
        """
        Get the organization id by organization label.
        :param org: organization label, use the org when instantiate
        the class as default
        :return: organization id
        """
        org = org or self.org
        ret, output = self.ssh.runcmd(f'hammer organization info '
                                      f'--label "{org}" '
                                      f'--fields Id')
        if ret == 0 and 'Id' in output:
            org_id = output.split(':')[1].strip()
            return org_id
        raise FailException(f'Failed to get the organization id for {org}')

    def org_create(self, name, label, description=None):
        """
        Create a new organization.
        :param name: the name of the organization.
        :param label: the label of the organization.
        :param description: the description for the organization.
        :return: True or raise Fail
        """
        description = description or ''
        _, output = self.ssh.runcmd(f'hammer organization create '
                                    f'--name "{name}" '
                                    f'--label "{label}" '
                                    f'--description "{description}"')
        if 'Organization created' in output:
            logger.info(f'Succeeded to create organization:{name}')
            return True
        if (
                'Name has already been taken' in output
                and
                'Label has already been taken' in output
        ):
            logger.info(f'The organization:{name} already existed')
            return True
        raise FailException(f'Failed to create organization:{name}')

    def org_delete(self, label):
        """
        Delete an organization by organization label.
        :param label: organization label
        :return: True or raise Fail
        """
        _, output = self.ssh.runcmd(f'hammer organization delete '
                                    f'--label "{label}"')
        if '100%' in output:
            logger.info(f'Succeeded to delete organization:{label}')
            return True
        if 'organization not found' in output:
            logger.info(f'The organization:{label} does not exist already')
            return True
        raise FailException(f'Failed to delete organization:{label}')

    def host_id(self, host_name, host_uuid=None, host_hwuuid=None):
        """
        Get the host id by host name or uuid or hwuuid.
        :param host_name: host name as a required option.
        :param host_uuid: host uuid as an optional option.
        :param host_hwuuid: host hwuuid as an optional option for
            only esx and rhvm modes.
        :return: host id
        """
        host_list = [host_name.lower()]
        if host_uuid:
            host_list.append(host_uuid.lower())
        if host_hwuuid:
            host_list.append(host_hwuuid.lower())
        for host in host_list:
            ret, output = self.ssh.runcmd(f'hammer host list '
                                          f'--organization-id {self.org_id} '
                                          f'--search {host} '
                                          f'--fields Id')
            if ret == 0 and len(output.split('\n')) == 6:
                host_id = output.split('\n')[3].strip()
                logger.info(f'Succeeded to get the host id, {host_name}:{id}')
                return host_id
        logger.warning(f'Failed to get the host id for {host_name}')
        return None

    def host_delete(self, host_name, host_uuid, host_hwuuid=None):
        """
        Delete a host by host name or uuid or hwuuid.
        :param host_name: host name as a required option.
        :param host_uuid: host uuid as an optional option.
        :param host_hwuuid: host hwuuid as an optional option for
            only esx and rhvm modes.
        :return: True or raise Fail
        """
        host_id = self.host_id(host_name=host_name,
                               host_uuid=host_uuid,
                               host_hwuuid=host_hwuuid)
        _, output = self.ssh.runcmd(f'hammer host delete '
                                    f'--organization-id {self.org} '
                                    f'--id {host_id}')
        if (
                ('Host deleted' in output or 'host not found' in output)
                and
                not self.host_id(host_name=host_name,
                                 host_uuid=host_uuid,
                                 host_hwuuid=host_hwuuid)
        ):
            logger.info(f'Succeeded to delete {host_name} from satellite')
            return True
        raise FailException(f'Failed to Delete {host_name} from satellite')

    def subscription_id(self, pool):
        """
        Get the subscription id by pool id.
        :param pool: pool id.
        :return: subscription id.
        """
        cmd = f'hammer subscription list --organization-id {self.org_id}'
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0:
            subscription_list = output.split('\n')
            for item in subscription_list:
                if pool in item:
                    subscription_id = item.split('|')[0].strip()
                    return subscription_id
        raise FailException(f'Failed to get the subscription id for {pool}')

    def attach(self, host_name, host_uuid=None, host_hwuuid=None, pool=None, quantity=1):
        """
        Attach or auto attach subscription for one host.
        :param host_name: host name as a required option.
        :param host_uuid: host uuid as an optional option.
        :param host_hwuuid: host hwuuid as an optional option for
            only esx and rhvm modes.
        :param pool: pool id, run auto attach when pool=None.
        :param quantity: the subscription quantity to attach.
        :return: True or raise Fail.
        """
        host_id = self.host_id(host_name=host_name,
                               host_uuid=host_uuid,
                               host_hwuuid=host_hwuuid)
        cmd = f'hammer host subscription auto-attach --host-id {host_id}'
        msg = 'Auto attached subscriptions to the host successfully'
        if pool:
            subscription_id = self.subscription_id(pool=pool)
            cmd = f'hammer host subscription attach ' \
                  f'--host-id {host_id} ' \
                  f'--subscription-id {subscription_id} ' \
                  f'--quantity {quantity}'
            msg = 'Subscription attached to the host successfully'
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and msg in output:
            logger.info(f'Succeeded to attach subscription for {host_name}')
            return True
        raise FailException(f'Failed to attach subscription for {host_name}')

    def unattach(self, pool, host_name, host_uuid=None, host_hwuuid=None, quantity=1):
        """
        Remove subscription from one host by pool id.
        :param pool: pool id
        :param host_name: host name as a required option.
        :param host_uuid: host uuid as an optional option.
        :param host_hwuuid: host hwuuid as an optional option for
            only esx and rhvm modes.
        :param quantity: the subscription quantity to remove.
        :return:
        """
        host_id = self.host_id(host_name=host_name,
                               host_uuid=host_uuid,
                               host_hwuuid=host_hwuuid)
        subscription_id = self.subscription_id(pool=pool)
        ret, output = self.ssh.runcmd(f'hammer host subscription remove '
                                      f'--host-id {host_id} '
                                      f'--subscription-id {subscription_id} '
                                      f'--quantity {quantity}')
        msg = 'Subscription removed from the host successfully'
        if ret == 0 and msg in output:
            logger.info(f'Succeeded to remove subscription for {host_name}')
            return True
        raise FailException(f'Failed to remove subscription for {host_name}')

    def activation_key_create(self,
                              key=None,
                              content_view='Default Organization View',
                              environment='Library'):
        """
        Create one activation key.
        :param key: activation key name.
        :param content_view: 'Default Organization View' as default.
        :param environment: 'Library' as default.
        :return: True or raise Fail.
        """
        key = key or self.activation_key
        _, output = self.ssh.runcmd(f'hammer activation-key create '
                                    f'--organization-id {self.org_id} '
                                    f'--name {key} '
                                    f'--lifecycle-environment {environment} '
                                    f'--content-view "{content_view}"')
        if 'Activation key created' in output:
            logger.info(f'Succeeded to create activation key:{key}')
            return True
        if 'Name has already been taken' in output:
            logger.info(f'Activation key:{key} already exists')
            return True
        raise FailException(f'Failed to create activation key:{key}')

    def activation_key_delete(self, key=None):
        """
        Delete an activation key by key name.
        :param key: activation key name.
        :return: True or raise Fail.
        """
        key = key or self.activation_key
        _, output = self.ssh.runcmd(f'hammer activation-key delete '
                                    f'--organization-id {self.org_id} '
                                    f'--name {key}')
        if 'Activation key deleted' in output:
            logger.info(f'Succeeded to delete activation key:{key}')
            return True
        if 'activation_key not found' in output:
            logger.info(f'Activation key:{key} was not found')
            return True
        raise FailException(f'Failed to delete activation key:{key}')

    def activation_key_update(self, key=None, auto_attach='yes'):
        """
        Update auto attach setting for an activation key.
        :param key: activation key name, default to use the key when
            instantiate the class.
        :param auto_attach: boolean, true/false, yes/no, 1/0.
        :return: True or raise Fail.
        """
        key = key or self.activation_key
        _, output = self.ssh.runcmd(f'hammer activation-key update '
                                    f'--organization-id {self.org_id} '
                                    f'--name {key} '
                                    f'--auto-attach {auto_attach}')
        if 'Activation key updated' in output:
            logger.info(f'Succeeded to update activation key:{key} with '
                        f'auto_attach:{auto_attach}')
            return True
        raise FailException(f'Failed to update auto-attach for '
                            f'activation key:{key}')

    def activation_key_attach(self, pool, quantity=None, key=None):
        """
        Add subscription for activation key.
        :param pool: pool id.
        :param quantity: the subscription quantity to add.
        :param key: activation key name, default to use the key when
        instantiate the class.
        :return: True or raise Fail.
        """
        key = key or self.activation_key
        subscription_id = self.subscription_id(pool=pool)
        cmd = f'hammer activation-key add-subscription ' \
              f'--organization-id {self.org_id} ' \
              f'--name {key} ' \
              f'--subscription-id {subscription_id}'
        if quantity:
            cmd += f' --quantity {quantity}'
        ret, output = self.ssh.runcmd(cmd)
        if 'Subscription added to activation key' in output:
            logger.info(f'Succeeded to attach subscription for '
                        f'activation key:{key}')
            return True
        raise FailException(f'Failed to attach subscription for '
                            f'activation key:{key}')

    def activation_key_unattach(self, pool, key=None):
        """
        Remove subscription from activation key.
        :param pool: pool id.
        :param key: activation key name, default to use the key when
        instantiate the class.
        :return:
        """
        key = key or self.activation_key
        subscription_id = self.subscription_id(pool=pool)
        cmd = f'hammer activation-key remove-subscription ' \
              f'--organization-id {self.org_id} ' \
              f'--name {key} ' \
              f'--subscription-id {subscription_id}'
        ret, output = self.ssh.runcmd(cmd)
        if 'Subscription removed from activation key' in output:
            logger.info(f'Succeeded to remove subscription for '
                        f'activation key:{key}')
            return True
        raise FailException(f'Failed to remove subscription for '
                            f'activation key:{key}')

    def settings(self, name, value):
        """
        Update the settings.
        :param name: such as unregister_delete_host.
        :param value: the value.
        :return: True or raise Fail.
        """
        ret, output = self.ssh.runcmd(f'hammer settings set '
                                      f'--name={name} '
                                      f'--value={value}')
        if ret == 0 and f'Setting [{name}] updated to' in output:
            logger.info(f'Succeeded to set {name}:{value} for satellite')
            return True
        raise FailException(f'Failed to set {name}:{value} for satellite')

