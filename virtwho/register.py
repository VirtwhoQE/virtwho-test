import json
import time
import requests

from virtwho import logger, FailException
from virtwho.configure import get_register_handler
from virtwho.ssh import SSHConnect


class SubscriptionManager:
    def __init__(
        self,
        host,
        username,
        password,
        port=22,
        register_type="rhsm",
        org=None,
        activation_key=None,
    ):
        """
        Define the global variables.
        :param host: ip/hostname to run subscription-manager command.
        :param username: account username of the host
        :param password: password to access the host
        :param port: port to access the host
        :param register_type: rhsm/satellite, rhsm as default
        :param org: organization of the entitlement server
        :param activation_key: activation_key of the satellite server.
            Will register by activation_key when the value is set.
        """
        self.host = host
        self.register_type = register_type
        self.rhsm_conf = "/etc/rhsm/rhsm.conf"
        self.ssh = SSHConnect(host=host, user=username, pwd=password, port=port)
        register = get_register_handler(register_type)
        self.server = register.server
        self.username = register.username
        self.password = register.password
        self.port = register.port
        self.prefix = register.prefix
        self.org = org or register.default_org
        self.activation_key = activation_key
        if register_type != "satellite":
            self.baseurl = register.baseurl

    def register(self):
        """
        Register host by subscription-manager command
        """
        if not self.is_register():
            self.unregister()
            cmd = (
                f"subscription-manager register "
                f"--serverurl={self.server}:{self.port}{self.prefix} "
                f"--org={self.org} "
            )
            if self.activation_key:
                cmd += f"--activationkey={self.activation_key} "
            else:
                cmd += f"--username={self.username} " f"--password={self.password} "
            if self.register_type == "satellite":
                self.satellite_cert_install()
            else:
                cmd += f"--baseurl={self.baseurl}"
            ret, output = self.ssh.runcmd(cmd)
            if "The system has been registered" in output:
                logger.info(f"Succeeded to register host({self.host})")
                return output
            else:
                raise FailException(f"Failed to register host({self.host})")
        else:
            logger.info(
                f"The host({self.host}) has been registered, "
                f"no need to register again."
            )
            return None

    def unregister(self):
        """
        Unregister and clean host by subscription-manager.
        """
        ret, _ = self.ssh.runcmd(
            "subscription-manager unregister;" "subscription-manager clean"
        )
        if ret == 0:
            # if self.register_type == 'satellite':
            #     self.satellite_cert_uninstall()
            logger.info(f"Succeeded to unregister host")
        else:
            raise FailException(f"Failed to unregister {self.host}.")

    def is_register(self):
        """
        Check if the host has been registered to the correct destination.
        """
        ret, output = self.ssh.runcmd("subscription-manager identity")
        if ret == 0 and self.org in output:
            return True
        return False

    def satellite_cert_install(self):
        """
        Install certificate when registering to satellite.
        """
        self.satellite_cert_uninstall()
        cmd = (
            f"rpm -ihv http://{self.server}"
            f"/pub/katello-ca-consumer-latest.noarch.rpm"
        )
        ret, output = self.ssh.runcmd(cmd)
        if ret != 0 and "is already installed" not in output:
            raise FailException(
                f"Failed to install satellite certification for {self.host}"
            )

    def satellite_cert_uninstall(self):
        """
        Uninstall certificate when after unregistering from satellite.
        """
        ret, output = self.ssh.runcmd("rpm -qa |grep katello-ca-consumer")
        if ret == 0 and "katello-ca-consumer" in output:
            cert_pkg = output.strip()
            ret, _ = self.ssh.runcmd(f"rpm -e {cert_pkg}")
            if ret == 0:
                logger.info("Succeeded to uninstall satellite cert package.")

    def attach(self, pool=None, quantity=None):
        """
        Attach subscription by Pool ID or --auto.
        :param pool: Pool ID, attach by --auto when pool=None
        :param quantity: subscription number to attach, default is auto.
        :return: tty output.
        """
        cmd = "subscription-manager attach "
        if pool:
            cmd += f"--pool={pool} "
        if quantity:
            cmd += f"--quantity={quantity}"
        if not pool:
            cmd += f"--auto "
        self.refresh()
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0:
            logger.info(f"Succeeded to attach subscription for {self.host}")
            return output.strip()
        if "--auto" in cmd and "Unable to find available" in output:
            logger.warning(f"Failed to attach subscription by auto for {self.host}.")
            return output.strip()
        if "Multi-entitlement not supported" in output:
            logger.warning(output)
            return output.strip()
        else:
            raise FailException(f"Failed to attach subscription for {self.host}")

    def unattach(self, pool=None):
        """
        Remove subscription by Pool ID or remove all.
        :param pool: Pool ID, remove all when pool=None.
        """
        cmd = "subscription-manager remove --all"
        if pool:
            cmd = f"subscription-manager remove --pool={pool}"
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0:
            logger.info(f"Succeeded to remove subscription for {self.host}")
        else:
            raise FailException(f"Failed to remove subscription for {self.host}")

    def available(self, sku_id, sku_type="Virtual"):
        """
        Search and analyze an available subscription by name and type.
        :param sku_id: sku id, such as RH00001
        :param sku_type: 'Physical' or 'Virtual'.
        :return: a dict with sku attributes.
        """
        cmd = f"subscription-manager list --av --all --matches={sku_id} |" f"tail -n +4"
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and "Pool ID:" in output:
            skus = output.strip().split("\n\n")
            for sku in skus:
                sku_attr = self.attr_analyzer(sku)
                if "system_type" in sku_attr.keys():
                    sku_attr["sku_type"] = sku_attr["system_type"]
                else:
                    sku_attr["sku_type"] = sku_attr["entitlement_type"]
                if sku_attr["sku_type"] == sku_type:
                    logger.info(
                        f"Succeeded to find {sku_type}:{sku_id} " f"in {self.host}"
                    )
                    if "(Temporary)" in sku_attr["subscription_type"]:
                        sku_attr["temporary"] = True
                    else:
                        sku_attr["temporary"] = False
                    return sku_attr
        logger.warning(f"Failed to find {sku_type}:{sku_id}" in {self.host})
        return None

    def consumed(self, sku_id, sku_type="Virtual"):
        """
        List and analyze the consumed subscription by Pool ID.
        :param sku_id: sku id, such as RH00049.
        :param sku_type: 'Physical' or 'Virtual'.
        :return: a dict with sku attributes.
        """
        self.refresh()
        ret, output = self.ssh.runcmd(f"subscription-manager list --co")
        if ret == 0:
            if output is None or "No consumed subscription pools were found" in output:
                logger.info(f"No consumed subscription found in {self.host}.")
                return None
            elif "Pool ID:" in output:
                skus = output.strip().split("\n\n")
                for sku in skus:
                    sku_attr = self.attr_analyzer(sku)
                    if "system_type" in sku_attr.keys():
                        sku_attr["sku_type"] = sku_attr["system_type"]
                    else:
                        sku_attr["sku_type"] = sku_attr["entitlement_type"]
                    if sku_attr["sku"] == sku_id and sku_attr["sku_type"] == sku_type:
                        logger.info(
                            f"Succeeded to get the consumed "
                            f"subscription in {self.host}"
                        )
                        if "(Temporary)" in sku_attr["subscription_type"]:
                            sku_attr["temporary"] = True
                        else:
                            sku_attr["temporary"] = False
                        # the below commented lines are used in local debug
                        # logger.info(
                        # f'---- sku_data of {sku_id}:\n{sku_attr}\n----'
                        # )
                        return sku_attr
        logger.warning("Failed to get consumed subscriptions.")
        return None

    def installed(self):
        """
        List products which are currently installed on the system and
        analyse the result.
        """
        self.refresh()
        ret, output = self.ssh.runcmd(
            "subscription-manager list --installed | tail -n +4"
        )
        if ret == 0 and output.strip() != "":
            install_attr = self.attr_analyzer(output)
            logger.info(f"Succeeded to list installed subscription for {self.host}")
            return install_attr
        raise FailException(f"Failed to list installed subscription for {self.host}")

    def repo(self, action, repo):
        """
        Enable/disable one or more repos.
        :param action: enable or disable
        :param repo: a string including one or more repos separated
            by comma, such as "repo1, repo2, repo3...".
        """
        repo_list = repo.split(",")
        cmd = "subscription-manager repos "
        for item in repo_list:
            cmd += f'--{action}="{item.strip()}" '
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0:
            logger.info(f"Succeeded to {action} repo: {repo}")
        else:
            raise FailException(f"Failed to {action} repo: {repo}")

    def refresh(self):
        """
        Refresh subscription by command 'subscription-manager refresh'.
        """
        for i in range(3):
            ret, output = self.ssh.runcmd("subscription-manager refresh")
            if ret == 0:
                logger.info(f"Succeeded to refresh subscription")
                return True
            logger.warning("Try again to refresh subscription after 180s...")
            time.sleep(180)
        raise FailException(f"Failed to refresh subscription for {self.host}")

    def attr_analyzer(self, attr):
        """
        Analyze the output attributes to a dict, like the output from
        command "subscription-manager list --in/co/av"
        :param attr: the output including several lines, which lines are
            {string}:{string} format.
        :return: a dict
        """
        attr_data = dict()
        attr = attr.strip().split("\n")
        for line in attr:
            if ":" not in line:
                continue
            line = line.split(":")
            key = line[0].strip().replace(" ", "_").lower()
            value = line[1].strip()
            attr_data[key] = value
        return attr_data

    def facts_create(self, key, value, wait=10):
        """
        Create subscription facts to /etc/rhsm/facts/custom.facts.
        :param key: fact key
        :param value: fact value
        :param wait: wait time after update facts, need 60s for satellite to
            resolve the tasks conflict issue.
        """
        option = f'{{"{key}":"{value}"}}'
        ret, _ = self.ssh.runcmd(f"echo '{option}' > /etc/rhsm/facts/custom.facts")
        if ret == 0:
            ret, output = self.ssh.runcmd("subscription-manager facts --update")
            time.sleep(wait)
            if ret == 0 and "Successfully updated" in output:
                logger.info(f"Succeeded to create custom.facts for {self.host}")
                return True
        raise FailException(f"Failed to create custom facts for {self.host}")

    def facts_remove(self, wait=10):
        """
        Remove subscription facts.
        :param wait: wait time after update facts, need 60s for satellite to
            resolve the tasks conflict issue.
        """
        ret, _ = self.ssh.runcmd("rm -f /etc/rhsm/facts/custom.facts")
        if ret == 0:
            ret, output = self.ssh.runcmd("subscription-manager facts --update")
            for i in range(3):
                time.sleep(wait)
                if ret == 0 and "Successfully updated" in output:
                    logger.info(f"Succeeded to remove custom.facts for {self.host}")
                    return True
        raise FailException(f"Failed to remove custom.facts for {self.host}")

    def pool_id_get(self, sku_id, sku_type="Physical"):
        self.register()
        sku_data = self.available(sku_id, sku_type)
        if sku_data is not None:
            sku_pool = sku_data["pool_id"]
            logger.info(f"Succeeded to get the vdc {sku_type} pool id: " f"{sku_pool}")
            return sku_pool
        logger.error("Failed to get the vdc physical sku pool id")
        return None


class RHSM:
    def __init__(self, rhsm="rhsm"):
        """
        Using rhsm api to check/get/delete consumers,  attach/remove
        subscription, and check the host-to-guest associations.
        :param rhsm: rhsm org rhsm_sw.
        """
        register = get_register_handler(rhsm)
        self.org = register.default_org
        self.api = f"https://{register.server}/subscription"
        self.auth = (register.username, register.password)

    def consumers(self, host_name=None):
        """
        Search consumer host information.
        :param host_name: host name, search all consumers if host_name=None.
        :return: one consumer or all consumers to a list.
        """
        status, consumers = request_get(
            url=f"{self.api}/owners/{self.org}/consumers", auth=self.auth
        )
        if status == 200:
            if host_name:
                for consumer in consumers:
                    if host_name in consumer["name"]:
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
            uuid = consumer["uuid"]
            logger.info(f"Succeeded to get stage consumer uuid: " f"{host_name}:{uuid}")
            return uuid
        raise FailException(f"Failed to get stage consumer uuid for {host_name}")

    def info(self, host_name):
        """
        Get the consumer host information by host name, including the
        detail facts info.
        :param host_name: host name
        :return: output to a dic
        """
        uuid = self.uuid(host_name)
        status, info = request_get(url=f"{self.api}/consumers/{uuid}", auth=self.auth)
        if status == 200:
            logger.info(f"Succeeded to get consumer info for {host_name}")
            return info
        raise FailException(f"Failed to get consumer info for {host_name}")

    def host_delete(self, host_name=None):
        """
        Delete only one consumer or clean all consumers.
        :param host_name: host name, will clean all consumers if host_name=None.
        :return: True or Fail
        """
        consumers = self.consumers()
        if consumers:
            for consumer in consumers:
                uuid = consumer["uuid"]
                if not host_name or (host_name and host_name in consumer["name"]):
                    request_delete(url=f"{self.api}/consumers/{uuid}", auth=self.auth)
            if not self.consumers(host_name=host_name):
                logger.info("Succeeded to delete consumer(s) on stage")
                return True
            raise FailException("Failed to delete consumer(s) on stage")
        logger.info(
            "Succeeded to delete consumer(s) on stage " "because no consumer found"
        )
        return True

    def pool(self, sku_id):
        """
        Get the pool id by sku id
        :param sku_id: sku id
        :return: pool id
        """
        status, pools = request_get(
            url=f"{self.api}/owners/{self.org}/pools", auth=self.auth
        )
        if status == 200 and pools:
            for pool in pools:
                if sku_id in pool["productId"]:
                    pool_id = pool["id"]
                    logger.info(f"Succeeded to get the pool id {sku_id}:{pool_id}")
                    return pool_id
        raise FailException(f"Failed to get pool id for {sku_id}")

    def attach(self, host_name, pool=None):
        """
        Attach subscription for host by auto or pool_id.
        :param host_name: host name
        :param pool: pool id, will attach by auto when pool_id=None
        """
        uuid = self.uuid(host_name)
        if self.entitlements(uuid, pool=pool):
            self.unattach(host_name, pool=pool)
        params = ""
        if pool:
            params = (("pool", pool),)
        request_post(
            url=f"{self.api}/consumers/{uuid}/entitlements",
            params=params,
            auth=self.auth,
        )
        if self.entitlements(uuid, pool=pool):
            logger.info(f"Succeeded to attach pool for {host_name}")
        else:
            raise FailException(f"Failed to attach pool for {host_name}")

    def unattach(self, host_name, pool=None):
        """
        Remove all subscriptions or the specified one for consumer.
        :param host_name: pool id, remove all subscriptions when pool=None
        :param pool: pool id
        """
        uuid = self.uuid(host_name)
        url = f"{self.api}/consumers/{uuid}/entitlements"
        if pool:
            entitlement_id = self.entitlements(uuid, pool)
            url = f"{self.api}/consumers/{uuid}/entitlements/{entitlement_id}"
        request_delete(url=url, auth=self.auth)
        if not self.entitlements(uuid, pool=pool):
            logger.info(f"Succeeded to remove pool(s) for {host_name}")
        else:
            raise FailException(f"Failed to remove pool(s) for {host_name}")

    def entitlements(self, consumer_uuid, pool=None):
        """
        Get entitlement id for each pool or the only one for the defined pool.
        :param consumer_uuid: consumer uuid in rhsm api
        :param pool: pool id, get all entitlement id when pool=None
        :return: entitlement id
        """
        status, entitlements = request_get(
            url=f"{self.api}/consumers/{consumer_uuid}/entitlements", auth=self.auth
        )
        if status == 200:
            entitlement_ids = dict()
            for item in entitlements:
                pool_id = item["pool"]["id"]
                entitlement_ids[pool_id] = item["id"]
            if pool:
                if pool in entitlement_ids.keys():
                    return entitlement_ids[pool]
                return None
            return entitlement_ids
        raise FailException(f"Failed to get entitlement info for {consumer_uuid}")

    def associate(self, host_name, guest_uuid):
        """
        Check the host/hypervisor is associated with guest or not.
        :param host_name: host name
        :param guest_uuid: guest uuid
        :return: True/False
        """
        uuid = self.uuid(host_name)
        status, output = request_get(
            url=f"{self.api}/consumers/{uuid}/guestids", auth=self.auth
        )
        if status == 200 and guest_uuid in str(output):
            logger.info("Hypervisor and Guest are associated on stage web")
            return True
        logger.warning("Hypervisor and Guest are not associated on stage web")
        return False

    def sca(self, sca="disable"):
        """
        Enable/disable simple content access.
        :param sca: enable/disable.
        :return: True or raise fail.
        """
        headers = {"accept": "application/json"}
        data = {"contentAccessMode": "entitlement"}
        if sca == "enable":
            data = {"contentAccessMode": "org_environment"}
        status = request_put(
            url=f"{self.api}/owners/{self.org}",
            auth=self.auth,
            headers=headers,
            json_data=data,
        )
        if status == 200:
            logger.info(f"Succeeded to {sca} SCA for rhsm")
            return True
        raise FailException(f"Failed to {sca} SCA for rhsm")


class Satellite:
    def __init__(self, server=None, org=None, activation_key=None):
        """
        Using hammer command to set satellite, handle organization and
        activation key, attach/remove subscription for host.
        Using api to check the host-to-guest associations.
        :param server: satellite server ip/hostname, use the server configured
            in virtwho.ini as default.
        :param org: organization label, use the default_org configured
            in virtwho.ini as default.
        :param activation_key: activation key name, use the configure
            in virtwho.ini as default.
        """
        register = get_register_handler("satellite")
        self.server = server or register.server
        self.org = org or register.default_org
        self.activation_key = activation_key or register.activation_key
        self.ssh = SSHConnect(
            host=self.server, user=register.ssh_username, pwd=register.ssh_password
        )
        self.hammer = "hammer --output=json"
        self.org_id = self.organization_id()
        self.api = f"https://{self.server}"
        self.auth = (register.username, register.password)

    def organization_id(self, org=None):
        """
        Get the organization id by organization label.
        :param org: organization label, use the org when instantiate
        the class as default
        :return: organization id
        """
        org = org or self.org
        ret, output = self.ssh.runcmd(
            f"{self.hammer} organization info " f'--label "{org}" ' f"--fields Id"
        )
        output = json.loads(output)
        if ret == 0 and output:
            return output["Id"]
        raise FailException(f"Failed to get the organization id for {org}")

    def org_create(self, name, label, description=None):
        """
        Create a new organization.
        :param name: the name of the organization.
        :param label: the label of the organization.
        :param description: the description for the organization.
        :return: True or raise Fail
        """
        description = description or ""
        _, output = self.ssh.runcmd(
            f"hammer organization create "
            f'--name "{name}" '
            f'--label "{label}" '
            f'--description "{description}"'
        )
        if "Organization created" in output:
            logger.info(f"Succeeded to create organization:{name}")
            return True
        if (
            "Name has already been taken" in output
            and "Label has already been taken" in output
        ) or "resource have no errors" in output:
            logger.info(f"The organization:{name} already existed")
            return True
        raise FailException(f"Failed to create organization:{name}")

    def org_delete(self, label):
        """
        Delete an organization by organization label.
        :param label: organization label
        :return: True or raise Fail
        """
        _, output = self.ssh.runcmd(f"hammer organization delete " f'--label "{label}"')
        if "100%" in output:
            logger.info(f"Succeeded to delete organization:{label}")
            return True
        if "organization not found" in output:
            logger.info(f"The organization:{label} does not exist already")
            return True
        raise FailException(f"Failed to delete organization:{label}")

    def host_id(self, host):
        """
        Get the host id by host name or uuid or hwuuid.
        :param host: host name/uuid/hwuuid
        :return: host id or None
        """
        ret, output = self.ssh.runcmd(
            f"{self.hammer} host list "
            f"--organization-id {self.org_id} "
            f"--search {host}"
        )
        output = json.loads(output)
        if ret == 0 and len(output) >= 1:
            for item in output:
                if host in item["Name"]:
                    host_id = item["Id"]
                    logger.info(f"Succeeded to get the host id, {host}:{host_id}")
                    return host_id
        logger.warning(f"Failed to get the host id for {host}")
        return None

    def host_delete(self, host):
        """
        Delete a host by host name or uuid or hwuuid.
        :param host: host name/uuid/hwuuid
        :return: True or raise Fail
        """
        host_id = self.host_id(host)
        if host_id:
            _, _ = self.ssh.runcmd(
                f"hammer host delete "
                f"--organization-id {self.org_id} "
                f"--id {host_id}"
            )
            if self.host_id(host) is None:
                logger.info(f"Succeeded to delete {host} from satellite")
                return True
            raise FailException(f"Failed to Delete {host} from satellite")
        else:
            logger.info(f"Did not find the {host} in satellite," f"no need to delete.")
            return True

    def subscription_id(self, pool):
        """
        Get the subscription id by pool id.
        :param pool: pool id.
        :return: subscription id.
        """
        ret, output = self.ssh.runcmd(
            f"{self.hammer} " f"subscription list " f"--organization-id {self.org_id}"
        )
        output = json.loads(output)
        if ret == 0 and output:
            for item in output:
                if item["Uuid"] == pool:
                    subscription_id = item["Id"]
                    return subscription_id
        raise FailException(f"Failed to get the subscription id for {pool}")

    def attach(self, host, pool=None, quantity=1):
        """
        Attach or auto attach subscription for one host/hypervisor.
        :param host: host name/uuid/hwuuid
        :param pool: pool id, run auto attach when pool=None.
        :param quantity: the subscription quantity to attach.
        :return: True, output or raise Fail.
        """
        host_id = self.host_id(host)
        cmd = f"hammer host subscription auto-attach --host-id {host_id}"
        msg = "Auto attached subscriptions to the host successfully"
        if pool:
            subscription_id = self.subscription_id(pool=pool)
            cmd = (
                f"hammer host subscription attach "
                f"--host-id {host_id} "
                f"--subscription-id {subscription_id} "
                f"--quantity {quantity}"
            )
            msg = "Subscription attached to the host successfully"
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and msg in output:
            logger.info(f"Succeeded to attach subscription for {host}")
            return True
        elif (
            ret != 0
            and "This host's organization is in Simple Content " "Access mode" in output
        ):
            logger.info(
                f"The organizaiton is in SCA mode, no need to " f"attach subscription"
            )
            return output
        raise FailException(f"Failed to attach subscription for {host}")

    def unattach(self, host, pool, quantity=1):
        """
        Remove subscription from one host/hypervisor by pool id.
        :param host: host name/uuid/hwuuid
        :param pool: pool id
        :param quantity: the subscription quantity to remove.
        :return:
        """
        host_id = self.host_id(host)
        subscription_id = self.subscription_id(pool=pool)
        ret, output = self.ssh.runcmd(
            f"hammer host subscription remove "
            f"--host-id {host_id} "
            f"--subscription-id {subscription_id} "
            f"--quantity {quantity}"
        )
        msg = "Subscription removed from the host successfully"
        if ret == 0 and msg in output:
            logger.info(f"Succeeded to remove subscription for {host}")
            return True
        raise FailException(f"Failed to remove subscription for {host}")

    def activation_key_create(
        self, key=None, content_view="Default Organization View", environment="Library"
    ):
        """
        Create one activation key.
        :param key: activation key name.
        :param content_view: 'Default Organization View' as default.
        :param environment: 'Library' as default.
        :return: True or raise Fail.
        """
        key = key or self.activation_key
        _, output = self.ssh.runcmd(
            f"hammer activation-key create "
            f"--organization-id {self.org_id} "
            f"--name {key} "
            f"--lifecycle-environment {environment} "
            f'--content-view "{content_view}"'
        )
        if "Activation key created" in output:
            logger.info(f"Succeeded to create activation key:{key}")
            return True
        if "Name has already been taken" in output:
            logger.info(f"Activation key:{key} already exists")
            return True
        raise FailException(f"Failed to create activation key:{key}")

    def activation_key_delete(self, key=None):
        """
        Delete an activation key by key name.
        :param key: activation key name.
        :return: True or raise Fail.
        """
        key = key or self.activation_key
        _, output = self.ssh.runcmd(
            f"hammer activation-key delete "
            f"--organization-id {self.org_id} "
            f"--name {key}"
        )
        if "Activation key deleted" in output:
            logger.info(f"Succeeded to delete activation key:{key}")
            return True
        if "activation_key not found" in output:
            logger.info(f"Activation key:{key} was not found")
            return True
        raise FailException(f"Failed to delete activation key:{key}")

    def activation_key_update(self, key=None, auto_attach="yes"):
        """
        Update auto attach setting for an activation key.
        :param key: activation key name, default to use the key when
            instantiate the class.
        :param auto_attach: boolean, true/false, yes/no, 1/0.
        :return: True or raise Fail.
        """
        key = key or self.activation_key
        _, output = self.ssh.runcmd(
            f"hammer activation-key update "
            f"--organization-id {self.org_id} "
            f"--name {key} "
            f"--auto-attach {auto_attach}"
        )
        if "Activation key updated" in output:
            logger.info(
                f"Succeeded to update activation key:{key} with "
                f"auto_attach:{auto_attach}"
            )
            return True
        raise FailException(
            f"Failed to update auto-attach for " f"activation key:{key}"
        )

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
        cmd = (
            f"hammer activation-key add-subscription "
            f"--organization-id {self.org_id} "
            f"--name {key} "
            f"--subscription-id {subscription_id}"
        )
        if quantity:
            cmd += f" --quantity {quantity}"
        ret, output = self.ssh.runcmd(cmd)
        if "Subscription added to activation key" in output:
            logger.info(
                f"Succeeded to attach subscription for " f"activation key:{key}"
            )
            return True
        raise FailException(
            f"Failed to attach subscription for " f"activation key:{key}"
        )

    def activation_key_unattach(self, pool, key=None):
        """
        Remove subscription from activation key.
        :param pool: pool id.
        :param key: activation key name, default to use the key when
        instantiate the class.
        :return: True or raise Fail.
        """
        key = key or self.activation_key
        subscription_id = self.subscription_id(pool=pool)
        cmd = (
            f"hammer activation-key remove-subscription "
            f"--organization-id {self.org_id} "
            f"--name {key} "
            f"--subscription-id {subscription_id}"
        )
        ret, output = self.ssh.runcmd(cmd)
        if "Subscription removed from activation key" in output:
            logger.info(
                f"Succeeded to remove subscription for " f"activation key:{key}"
            )
            return True
        raise FailException(
            f"Failed to remove subscription for " f"activation key:{key}"
        )

    def settings(self, name, value):
        """
        Update the settings.
        :param name: such as unregister_delete_host.
        :param value: the value.
        :return: True or raise Fail.
        """
        ret, output = self.ssh.runcmd(
            f"hammer settings set " f"--name={name} " f"--value={value}"
        )
        if ret == 0 and f"Setting [{name}] updated to" in output:
            logger.info(f"Succeeded to set {name}:{value} for satellite")
            return True
        raise FailException(f"Failed to set {name}:{value} for satellite")

    def associate_on_webui(self, hypervisor, guest):
        """
        Check the hypervisor is associated with guest on web.
        :param guest: guest name
        :param hypervisor: hypervisor host name/uuid/hwuuid
        """
        host_id = self.host_id(host=hypervisor)
        guest_id = self.host_id(host=guest)
        if host_id and guest_id:
            # Find the guest in hypervisor page
            ret, output = request_get(
                url=f"{self.api}/api/v2/hosts/{host_id}", auth=self.auth
            )
            if guest.lower() in str(output):
                logger.info("Succeeded to find the associated guest in hypervisor page")

            else:
                logger.warning("Failed to find the associated guest in hypervisor page")
                return False
            # Find the hypervisor in guest page
            ret, output = request_get(
                url=f"{self.api}/api/v2/hosts/{guest_id}", auth=self.auth
            )
            if hypervisor.lower() in str(output):
                logger.info("Succeeded to find the associated hypervisor in guest page")
            else:
                logger.warning("Failed to find the associated hypervisor in guest page")
                return False
            return True

    def subscription_on_webui(self, pool):
        """
        Check the subscription info on webui.
        :param pool: sku pool id
        """
        katello_id = self.katello_id(pool)
        _, output = request_get(
            url=f"{self.api}/katello/api/organizations/{self.org_id}/"
            f"subscriptions/{katello_id}",
            auth=self.auth,
        )
        if output and output["id"]:
            return output
        logger.warning(f"Failed to get the pool subscription info on satellite webui")
        return None

    def katello_id(self, pool):
        """
        Get the pool katello id.
        :param pool: sku pool id
        """
        for i in range(3):
            ret, output = request_get(
                url=f"{self.api}/katello/api/organizations/{self.org_id}/"
                f"subscriptions/?per_page=1000",
                auth=self.auth,
            )
            if output and "results" in output.keys():
                for item in output["results"]:
                    if pool in item["cp_id"]:
                        katello_id = str(item["id"]).strip()
                        logger.info(f"Get the katello_id: {katello_id}")
                        return katello_id
            time.sleep(15)
        logger.warning(f"Failed to get katello id on satellite webui.")
        return None

    def hosts_info_on_webui(self, host):
        """
        Check the host details from satellite webui
        :param host: :param host: host name/uuid/hwuuid
        """
        host_id = self.host_id(host)
        _, output = request_get(
            url=f"{self.api}/api/v2/hosts/{host_id}", auth=self.auth
        )
        if output:
            return output
        logger.warning(f"Failed to get host info for {host} on satellite webui")
        return None

    def sca(self, sca="disable"):
        """
        Enable/disable simple content access.
        :param sca: enable/disable.
        :return: True or raise fail.
        """
        ret, output = self.ssh.runcmd(
            f"hammer simple-content-access {sca} " f"--organization-id {self.org_id}"
        )
        if ret == 0 and "100%" in output:
            logger.info(f"Succeeded to {sca} SCA for satellite")
            return True
        raise FailException(f"Failed to {sca} SCA for satellite")

    def facts_get(self, host_id):
        """
        Get the host facts information by hammer command
        :param host_id:
        :return: host facts information
        """
        ret, output = self.ssh.runcmd(f"{self.hammer} host facts --id {host_id}")
        if ret:
            return False
        else:
            return output


def request_get(url, auth, verify=False):
    """Sends a GET request.
    :param url: API URL
    :param auth: authentication with format (username, password)
    :param verify: a boolean to control whether we verify the server's
        TLS certificate
    :return: response status code and json output.
    """
    res = requests.get(url=url, auth=auth, verify=verify)
    return res.status_code, res.json()


def request_post(url, auth, params, verify=False):
    """Sends a POST request.
    :param url: API URL
    :param auth: authentication with format (username, password)
    :param params: Dictionary, list of tuples or bytes to send
        in the query string
    :param verify: a boolean to control whether we verify the server's
        TLS certificate
    :return: response status code
    """
    res = requests.post(url=url, auth=auth, params=params, verify=verify)
    return res.status_code


def request_put(url, auth, headers, json_data, verify=False):
    """Sends a PUT request.
    :param url: API URL
    :param auth: authentication with format (username, password)
    :param headers: dictionary of HTTP Headers
    :param json_data: json data to send in the body
    :param verify: a boolean to control whether we verify the server's
        TLS certificate
    :return: response status code
    """
    res = requests.put(
        url=url, auth=auth, headers=headers, json=json_data, verify=verify
    )
    return res.status_code


def request_delete(url, auth, verify=False):
    """Sends a DELETE request.
    :param url: API URL
    :param auth: authentication with format (username, password)
    :param verify: a boolean to control whether we verify the server's
        TLS certificate
    :return: response status code
    """
    res = requests.delete(url=url, auth=auth, verify=verify)
    return res.status_code
