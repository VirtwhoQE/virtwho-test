import json
import requests

from json.decoder import JSONDecodeError
from virtwho import logger, FailException
from virtwho.configure import get_register_handler
from virtwho.ssh import SSHConnect
import re


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
                cmd += f"--username={self.username} --password={self.password} "
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
                f"The host({self.host}) has been registered, no need to register again."
            )
            return None

    def unregister(self):
        """
        Unregister and clean host by subscription-manager.
        """
        ret, _ = self.ssh.runcmd(
            "subscription-manager unregister; subscription-manager clean"
        )
        if ret == 0:
            # if self.register_type == 'satellite':
            #     self.satellite_cert_uninstall()
            logger.info("Succeeded to unregister host")
        else:
            raise FailException(f"Failed to unregister {self.host}.")

    def is_register(self):
        """
        Check if the host has been registered to the correct destination.
        """
        ret, output = self.ssh.runcmd("subscription-manager identity")
        if ret == 0 and self.org in output:
            if self.register_type == "satellite":
                _, output = self.ssh.runcmd(f"cat {self.rhsm_conf}", log_print=False)
                if f"hostname = {self.server}" not in output:
                    logger.warning(
                        f"The ({self.host}) is not registering in the testing Satellite"
                    )
                    return False
            return True
        return False

    def satellite_cert_install(self):
        """
        Install certificate when registering to satellite.
        """
        self.satellite_cert_uninstall()
        cmd = f"rpm -ihv http://{self.server}/pub/katello-ca-consumer-latest.noarch.rpm"
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

    def identity(self):
        """
        subscription-manager identity
        ... returns dict
        aka
        {'system identity': '29dadce5-0d6b-44ed-bf35-71e1943e4129',
         'name': 'kvm-06.redhat.com',
         'org name': '18939614',
         'org ID': '18939614'}
        """
        cmd = "subscription-manager identity"
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0:
            lines = [line.strip() for line in output.split("\n")]
            pairs = [re.split(r"[\ \t]*:[\ \t]*", line) for line in lines if line]
            return dict(pairs)
        return dict()


class RHSM:
    def __init__(self, rhsm="rhsm"):
        """
        Using rhsm api to check/get/delete consumers,
        and check the host-to-guest associations.
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
            logger.info(f"Succeeded to get stage consumer uuid: {host_name}:{uuid}")
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
            "Succeeded to delete consumer(s) on stage because no consumer found"
        )
        return True

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

    def sca(self, sca="enable"):
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
        Using hammer command to set satellite, handle organization and activation key.
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
        try:
            # import ipdb; ipdb.set_trace()
            self.org_id = self.organization_id()
        except FailException:  # retry by creating org first
            self.org_create(name=self.org, label=self.org)
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
            f'{self.hammer} organization info --label "{org}" --fields Id'
        )
        try:
            output = json.loads(output)
        except JSONDecodeError:
            raise FailException(f"Failed to get the organization id for {org}")

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
        _, output = self.ssh.runcmd(f'hammer organization delete --label "{label}"')
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
            f"{self.hammer} host list --organization-id {self.org_id} --search {host}"
        )
        output = json.loads(output)
        if ret == 0 and len(output) >= 1:
            for item in output:
                if host in item["Name"] or host.lower() in item["Name"]:
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
            self.ssh.runcmd(
                f"hammer host delete --organization-id {self.org_id} --id {host_id}"
            )
            if self.host_id(host) is None:
                logger.info(f"Succeeded to delete {host} from satellite")
                return True
            raise FailException(f"Failed to Delete {host} from satellite")
        else:
            logger.info(f"Did not find the {host} in satellite,no need to delete.")
            return True

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
            f"hammer activation-key delete --organization-id {self.org_id} --name {key}"
        )
        if "Activation key deleted" in output:
            logger.info(f"Succeeded to delete activation key:{key}")
            return True
        if "activation_key not found" in output:
            logger.info(f"Activation key:{key} was not found")
            return True
        raise FailException(f"Failed to delete activation key:{key}")

    def settings(self, name, value):
        """
        Update the settings.
        :param name: such as unregister_delete_host.
        :param value: the value.
        :return: True or raise Fail.
        """
        ret, output = self.ssh.runcmd(
            f"hammer settings set --name={name} --value={value}"
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

    def sca(self, org=None, sca="enable"):
        """
        Enable/disable simple content access.
        :param org: org lable, default use the Default_Organization.
        :param sca: enable/disable.
        :return: True or raise fail.
        """
        org = org or self.org
        org_id = self.organization_id(org=org)
        ret, output = self.ssh.runcmd(
            f"hammer simple-content-access {sca} --organization-id {org_id}"
        )
        if ret == 0 and "100%" in output:
            logger.info(f"Succeeded to {sca} SCA for satellite:{org}")
            return True
        raise FailException(f"Failed to {sca} SCA for satellite:{org}")

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
    logger.info(f"Making request: GET {url}")
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
    logger.info(f"Making request: POST {url}")
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
    logger.info(f"Making request: PUT {url}")
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
    logger.info(f"Making request: DELETE {url}")
    return res.status_code
