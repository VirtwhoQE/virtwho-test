import os
import re
import argparse
import sys

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(os.path.split(rootPath)[0])

from virtwho import logger
from virtwho.settings import config
from virtwho.ssh import SSHConnect
from virtwho.base import hostname_get, host_ping, ssh_connect
from virtwho.base import rhel_host_uuid_get
from utils.properties_update import virtwho_ini_update
from hypervisor.virt.libvirt.libvirtcli import LibvirtCLI
from hypervisor.virt.esx.powercli import PowerCLI
from hypervisor.virt.hyperv.hypervcli import HypervCLI
from hypervisor.virt.kubevirt.kubevirtapi import KubevirtApi
from hypervisor.virt.ahv.ahvapi import AHVApi

state_good = "GOOD"
state_update = "UPDATED"
state_server_bad = "BAD (Server Broke)"
state_guest_bad = "BAD (Guest Broke)"
server_broke = "Broke"
guest_none = "None"
guest_down = "Down"


def esx_monitor():
    """
    Check the vCenter state, including the vCenter server testing, the
    ESXi host testing and the rhel guest state testing. At last it will
    update the test result to the virtwho.ini file.
    """
    esx_state = state_good
    esx_data = {}
    server = config.esx.server
    client_server = config.esx.ssh_ip
    esx_ip = config.esx.esx_ip
    guest_ip = config.esx.guest_ip
    guest_name = config.esx.guest_name
    esx = PowerCLI(
        server=server,
        admin_user=config.esx.username,
        admin_passwd=config.esx.password,
        client_server=client_server,
        client_user=config.esx.ssh_username,
        client_passwd=config.esx.ssh_password,
    )
    ssh_esx = SSHConnect(
        host=esx_ip,
        user=config.esx.esx_username,
        pwd=config.esx.esx_password,
    )
    try:
        logger.info(f">>>vCenter: Check if the vCenter server is running well.")
        ret1 = host_ping(host=server)
        if not ret1:
            esx_state, server = (state_server_bad, server_broke)
            logger.error(f"The vCenter Server has broken, please repaire it.")

        logger.info(f">>>vCenter: Check if the esxi host is running well.")
        ret2 = host_ping(host=esx_ip)
        if not ret2:
            esx_ip = "Broke"
            logger.error(f"The esxi host has broken, please repaire it.")

        logger.info(f">>>vCenter: Check if the windows client is running well.")
        ret3 = host_ping(host=client_server)
        if not ret3:
            client_server = "Broke"
            logger.error(f"The windows Client has broken, please repaire it.")

        if ret1 and ret2 and ret3:
            logger.info(f">>>vCenter: Get the Hypervisor data.")
            esx_data = esx.guest_search(guest_name, uuid_info=True)
            esx_data["esx_hostname"] = hostname_get(ssh_esx)
            logger.info(f"=== vCenter Data:\n{esx_data}\n===")

            logger.info(f">>>vCenter: Check if the rhel guest is running.")
            if not esx_data["guest_name"]:
                esx_state, guest_ip = (state_guest_bad, guest_none)
                logger.error(
                    f"Did not find the rhel guest({guest_name}), "
                    f"please install one."
                )
            else:
                if esx_data["guest_state"] == 1 and host_ping(
                    host=esx_data["guest_ip"]
                ):
                    logger.info(f"The rhel guest({guest_name}) is running well.")
                    ssh_guest = SSHConnect(
                        host=esx_data["guest_ip"],
                        user=config.esx.guest_username,
                        pwd=config.esx.guest_password,
                    )
                    esx_data["guest_uuid"] = rhel_host_uuid_get(ssh_guest)
                else:
                    esx_state, guest_ip = (state_guest_bad, guest_down)
                    logger.error(
                        f"The rhel guest({guest_name}) is down, please repair it."
                    )

    finally:
        logger.info(f">>>vCenter: Update the data of virtwho.ini.")
        esx_dict = {
            "server": server,
            "esx_ip": esx_ip,
            "ssh_ip": client_server,
            "guest_ip": guest_ip,
        }
        if esx_data:
            compare_dict = {
                "esx_ip": [config.esx.esx_ip, esx_data["esx_ip"]],
                "esx_uuid": [config.esx.esx_uuid, esx_data["esx_uuid"]],
                "esx_hwuuid": [config.esx.esx_hwuuid, esx_data["esx_hwuuid"]],
                "esx_hostname": [config.esx.esx_hostname, esx_data["esx_hostname"]],
                "esx_version": [config.esx.esx_version, esx_data["esx_version"]],
                "esx_cpu": [config.esx.esx_cpu, esx_data["esx_cpu"]],
                "esx_cluster": [config.esx.esx_cluster, esx_data["esx_cluster"]],
                "guest_ip": [config.esx.guest_ip, esx_data["guest_ip"]],
                "guest_uuid": [config.esx.guest_uuid, esx_data["guest_uuid"]],
            }
            for key, value in compare_dict.items():
                if value[0] != value[1]:
                    logger.info(f"The vCenter:({key}) changed.")
                    esx_dict[key] = f"{value[1]} (Updated)"
                    esx_state = state_update
        else:
            esx_state = state_server_bad

        logger.info(f">>>vCenter: the test result is ({esx_state})")
        virtwho_ini_update("esx", "state", esx_state)
        for option, value in esx_dict.items():
            virtwho_ini_update("esx", option, value)
        return esx_state


def hyperv_monitor():
    """
    Check the Hyperv state, including the Hyperv server testing and the
    the rhel guest state testing. At last it will update the test result
    to the virtwho.ini file.
    """
    hyperv_state = state_good
    hyperv_data = {}
    server = config.hyperv.server
    guest_ip = config.hyperv.guest_ip
    guest_name = config.hyperv.guest_name
    hyperv = HypervCLI(
        server=server, ssh_user=config.hyperv.username, ssh_pwd=config.hyperv.password
    )
    try:
        logger.info(f">>>Hyperv: Check if the hypervisor is running.")
        if not host_ping(host=server):
            hyperv_state, server, guest_ip = (
                state_server_bad,
                server_broke,
                guest_none,
            )
            logger.error(f"The hyperv host has broken, please repaire it.")

        else:
            logger.info(f">>>Hyperv: Get the hypervisor data.")
            hyperv_data = hyperv.guest_search(guest_name)
            uuid = hyperv_data["hyperv_uuid"]
            hyperv_data["hyperv_uuid"] = uuid[6:8] + uuid[4:6] + uuid[2:4] + uuid[0:2] + "-" + uuid[11:13] + uuid[9:11] + "-" + uuid[16:18] + uuid[14:16] + uuid[18:]
            logger.info(f"=== Hyperv Data:\n{hyperv_data}\n===")

            logger.info(f">>>Hyperv: Check if the rhel guest if running.")
            if not hyperv_data["guest_name"]:
                hyperv_state, guest_ip = (state_guest_bad, guest_none)
                logger.error(
                    f"Did not find the rhel guest ({guest_name}), "
                    f"please install one."
                )
            else:
                if (hyperv_data["guest_state"] == 2
                        and host_ping(host=hyperv_data["guest_ip"])):
                    logger.info(f"The rhel guest({guest_name}) is running well.")
                    ssh_guest = SSHConnect(
                        host=hyperv_data["guest_ip"],
                        user=config.esx.guest_username,
                        pwd=config.esx.guest_password,
                    )
                    hyperv_data["guest_uuid"] = rhel_host_uuid_get(ssh_guest).upper()
                else:
                    hyperv_state, guest_ip = (state_guest_bad, guest_down)
                    logger.warning(
                        f"The rhel guest({guest_name}) is down, please repair it."
                    )

    finally:
        logger.info(f">>>Hyperv: Compare and update the data in virtwho.ini.")
        hyperv_dict = {
            "server": server,
            "guest_ip": guest_ip,
        }
        if hyperv_data:
            compare_dict = {
                "uuid": [config.hyperv.uuid, hyperv_data["hyperv_uuid"]],
                "hostname": [config.hyperv.hostname, hyperv_data["hyperv_hostname"]],
                # 'version': [config.hyperv.version,
                #             hyperv_data['hyperv_version']],
                "cpu": [config.hyperv.cpu, hyperv_data["hyperv_cpu"]],
                "guest_ip": [guest_ip, hyperv_data["guest_ip"]],
                "guest_uuid": [config.hyperv.guest_uuid, hyperv_data["guest_uuid"]],
            }
            for key, value in compare_dict.items():
                if value[0] != value[1]:
                    logger.info(f"The hyperv({key}) changed.")
                    hyperv_dict[key] = f"{value[1]} (Updated)"
                    hyperv_state = state_update
        else:
            hyperv_state = state_server_bad

        logger.info(f"Hyperv: the test result is ({hyperv_state})")
        virtwho_ini_update("hyperv", "state", hyperv_state)
        for option, value in hyperv_dict.items():
            virtwho_ini_update("hyperv", option, value)
        return hyperv_state


def kubevirt_monitor():
    """
    Check the Kubevirt state, including the Kubevirt server testing and the
    the rhel guest state testing. At last it will update the test result
    to the virtwho.ini file.
    """
    kubevirt_state = state_good
    kubevirt_data = {}
    kubevirt_data_sw = {}

    guest_name = config.kubevirt.guest_name
    guest_ip = config.kubevirt.guest_ip
    guest_name_sw = config.kubevirt.guest_name_sw
    guest_ip_sw = config.kubevirt.guest_ip_sw

    endpoint = config.kubevirt.endpoint
    server = re.findall(r"https://(.+?):6443", endpoint)[0]
    kubevirt = KubevirtApi(endpoint, config.kubevirt.token)
    try:
        logger.info(f">>>Kubevirt: Check if the hypervisor is running.")
        if not host_ping(host=server):
            kubevirt_state, endpoint = (state_server_bad, server_broke)
            logger.error(f"The kubevirt host has broken, please repaire it.")

        else:
            logger.info(f">>>Kubevirt: Test the guest {guest_name}.")
            kubevirt_data = kubevirt.guest_search(
                guest_name, config.kubevirt.guest_port
            )
            logger.info(f"=== Kubevirt data of {guest_name}:\n{kubevirt_data}\n===")
            if not kubevirt_data:
                kubevirt_state, guest_ip = (state_guest_bad, guest_none)
                logger.error(
                    f"Did not find the guest({guest_name}), please install one."
                )
            else:
                ssh_guest = SSHConnect(
                    host=kubevirt_data["hostname"],
                    user=config.kubevirt.guest_username,
                    pwd=config.kubevirt.guest_password,
                    port=config.kubevirt.guest_port,
                )
                if ssh_connect(ssh_guest):
                    logger.info(f"The guest({guest_name}) is running well.")
                else:
                    kubevirt_state, guest_ip = (state_guest_bad, guest_down)
                    logger.warning(
                        f"The guest({guest_name}) is unavailable, please repair it."
                    )

            if guest_name_sw:
                logger.info(f">>>Kubevirt: Test the guest {guest_name_sw}.")
                kubevirt_data_sw = kubevirt.guest_search(
                    guest_name_sw, config.kubevirt.guest_port_sw
                )
                logger.info(
                    f"=== Kubevirt data of {guest_name_sw}:\n{kubevirt_data_sw}\n==="
                )
                if not kubevirt_data_sw:
                    kubevirt_state, guest_ip_sw = (state_guest_bad, guest_none)
                    logger.error(
                        f"Did not find the guest({guest_name_sw}), please install one."
                    )
                else:
                    ssh_guest_sw = SSHConnect(
                        host=kubevirt_data_sw["hostname"],
                        user=config.kubevirt.guest_username_sw,
                        pwd=config.kubevirt.guest_password_sw,
                        port=config.kubevirt.guest_port_sw,
                    )
                    if ssh_connect(ssh_guest_sw):
                        logger.info(f"The guest({guest_name_sw}) is running well.")
                    else:
                        kubevirt_state, guest_ip_sw = (state_guest_bad, guest_down)
                        logger.warning(
                            f"The guest({guest_name}) is unavailable, please repair it."
                        )

    finally:
        logger.info(f">>>Kubevirt: Compare and update the data in virtwho.ini.")
        kubevirt_dict = {
            "endpoint": endpoint,
            "guest_ip": guest_ip,
        }
        compare_dict = {}
        if kubevirt_data:
            compare_dict.update(
                {
                    "uuid": [config.kubevirt.uuid, kubevirt_data["uuid"]],
                    "hostname": [config.kubevirt.hostname, kubevirt_data["hostname"]],
                    "version": [config.kubevirt.version, kubevirt_data["version"]],
                    "cpu": [config.kubevirt.cpu, kubevirt_data["cpu"]],
                    "guest_ip": [config.kubevirt.guest_ip, kubevirt_data["hostname"]],
                    "guest_uuid": [
                        config.kubevirt.guest_uuid,
                        kubevirt_data["guest_uuid"],
                    ],
                }
            )
        if guest_name_sw:
            kubevirt_dict["guest_ip_sw"] = guest_ip_sw
            if kubevirt_data_sw:
                compare_dict.update(
                    {
                        "uuid_sw": [config.kubevirt.uuid_sw, kubevirt_data_sw["uuid"]],
                        "hostname_sw": [
                            config.kubevirt.hostname_sw,
                            kubevirt_data_sw["hostname"],
                        ],
                        "version_sw": [
                            config.kubevirt.version_sw,
                            kubevirt_data_sw["version"],
                        ],
                        "cpu_sw": [config.kubevirt.cpu_sw, kubevirt_data_sw["cpu"]],
                        "guest_ip_sw": [
                            config.kubevirt.guest_ip_sw,
                            kubevirt_data_sw["hostname"],
                        ],
                        "guest_uuid_sw": [
                            config.kubevirt.guest_uuid_sw,
                            kubevirt_data_sw["guest_uuid"],
                        ],
                    }
                )
            for key, value in compare_dict.items():
                if value[0] != value[1]:
                    logger.info(f"The kubevirt({key}) changed.")
                    kubevirt_dict[key] = f"{value[1]} (Updated)"
                    if "BAD" not in kubevirt_state:
                        kubevirt_state = state_update
                    if "BAD" in kubevirt_state and state_update not in kubevirt_state:
                        kubevirt_state = f"Part {kubevirt_state}, part {state_update}"

        if not kubevirt_data and not kubevirt_data_sw:
            kubevirt_state = state_server_bad

        logger.info(f"Kubevirt: the test result is ({kubevirt_state})")
        virtwho_ini_update("kubevirt", "state", kubevirt_state)
        for option, value in kubevirt_dict.items():
            virtwho_ini_update("kubevirt", option, value)
        return kubevirt_state


def ahv_monitor():
    """
    Check the Nutanix state, including the Nutanix server testing and the
    the rhel guest state testing. At last it will update the test result
    to the virtwho.ini file.
    """
    ahv_state = state_good
    ahv_data = {}
    ahv_data_sw = {}
    server = config.ahv.server

    guest_name = config.ahv.guest_name
    guest_ip = config.ahv.guest_ip
    guest_name_sw = config.ahv.guest_name_sw
    guest_ip_sw = config.ahv.guest_ip_sw

    ahv = AHVApi(
        server=server, username=config.ahv.username, password=config.ahv.password
    )

    try:
        logger.info(f">>>Nutanix: Check if the hypervisor is running well.")
        if not host_ping(host=server):
            ahv_state, server = (state_server_bad, server_broke)
            logger.error(f"The Nutanix host has broken, please repaire it.")

        else:
            logger.info(f">>>Nutanix: Test the guest {guest_name}.")
            ahv_data = ahv.guest_search(guest_name)
            logger.info(f"===Nutanix data of {guest_name}:\n{ahv_data}\n===")
            if not ahv_data:
                ahv_state, guest_ip = (state_guest_bad, guest_none)
                logger.error(
                    f"Did not find the guest({guest_name}), please install one."
                )
            else:
                ssh_guest = SSHConnect(
                    host=ahv_data["guest_ip"],
                    user=config.ahv.guest_username,
                    pwd=config.ahv.guest_password,
                )
                if ssh_connect(ssh_guest):
                    logger.info(f"The guest{guest_name} is running well.")
                else:
                    ahv_state, guest_ip = (state_guest_bad, guest_down)
                    logger.warning(
                        f"The guest({guest_name}) is down, please repair it."
                    )
            if guest_name_sw:
                ahv_data_sw = ahv.guest_search(guest_name_sw)
                logger.info(f"===Nutanix data of {guest_name_sw}:\n{ahv_data_sw}\n===")
                if not ahv_data_sw:
                    ahv_state, guest_ip_sw = (state_guest_bad, guest_none)
                    logger.error(
                        f"Did not find the guest({guest_name_sw}), please install one."
                    )
                else:
                    ssh_guest_sw = SSHConnect(
                        host=ahv_data_sw["guest_ip"],
                        user=config.ahv.guest_username_sw,
                        pwd=config.ahv.guest_password_sw,
                    )
                    if ssh_connect(ssh_guest_sw):
                        logger.info(f"The guest{guest_name_sw} is running well.")
                    else:
                        ahv_state, guest_ip_sw = (state_guest_bad, guest_down)
                        logger.warning(
                            f"The guest({guest_name_sw}) is down, please repair it."
                        )

    finally:
        logger.info(f">>>Nutanix: Compare and update the data in virtwho.ini.")
        ahv_dict = {
            "server": server,
            "guest_ip": guest_ip,
        }
        compare_dict = {}
        if ahv_data:
            compare_dict.update(
                {
                    "uuid": [config.ahv.uuid, ahv_data["uuid"]],
                    "hostname": [config.ahv.hostname, ahv_data["hostname"]],
                    "version": [config.ahv.version, ahv_data["version"]],
                    "cpu": [config.ahv.cpu, ahv_data["cpu"]],
                    "cluster": [config.ahv.cluster, ahv_data["cluster"]],
                    "guest_ip": [config.ahv.guest_ip, ahv_data["guest_ip"]],
                    "guest_uuid": [config.ahv.guest_uuid, ahv_data["guest_uuid"]],
                }
            )
        if guest_name_sw:
            ahv_dict["guest_ip_sw"] = guest_ip_sw
            if ahv_data_sw:
                compare_dict.update(
                    {
                        "guest_ip_sw": [
                            config.ahv.guest_ip_sw,
                            ahv_data_sw["guest_ip"],
                        ],
                        "guest_uuid_sw": [
                            config.ahv.guest_uuid_sw,
                            ahv_data_sw["guest_uuid"],
                        ],
                    }
                )
        for key, value in compare_dict.items():
            if value[0] != value[1]:
                logger.info(f"The Nutanix({key}) changed.")
                ahv_dict[key] = f"{value[1]} (Updated)"
                if "BAD" not in ahv_state:
                    ahv_state = state_update
                if "BAD" in ahv_state and state_update not in ahv_state:
                    ahv_state = f"Part {ahv_state}, part {state_update}"

        if not ahv_data and not ahv_data_sw:
            ahv_state = state_server_bad

        logger.info(f"Nutanix: the test result is ({ahv_state})")
        virtwho_ini_update("ahv", "state", ahv_state)
        for option, value in ahv_dict.items():
            virtwho_ini_update("ahv", option, value)
        return ahv_state


def libvirt_monitor():
    """
    Check the Libvirt state, including the Libvirt server testing and the
    the rhel guest state testing. At last it will update the test result
    to the virtwho.ini file.
    """
    libvirt_state = state_good
    libvirt_data = {}
    server = config.libvirt.server
    guest_ip = config.libvirt.guest_ip
    guest_name = config.libvirt.guest_name
    libvirt = LibvirtCLI(
        server=server,
        ssh_user=config.libvirt.username,
        ssh_passwd=config.libvirt.password,
    )
    ssh_libvirt = SSHConnect(
        host=server, user=config.libvirt.username, pwd=config.libvirt.password
    )
    try:
        logger.info(f">>>Libvirt: Check if the libvirt host is running.")
        if not host_ping(host=server):
            libvirt_state, server, guest_ip = (
                state_server_bad,
                server_broke,
                guest_none,
            )
            logger.error(f"The libvirt host has broken, please repaire it.")
        else:
            logger.info(f">>>Libvirt: Get the hypervisor env data.")
            libvirt_data = libvirt.guest_search(guest_name)
            logger.info(f"=== Libvirt Data\n{libvirt_data}\n ===")

            logger.info(f">>>Libvirt: Check if the rhel guest is running.")
            if not libvirt.guest_exist(guest_name):
                libvirt_state, guest_ip = (state_guest_bad, guest_none)
                logger.error(
                    f"Did not find the rhel guest ({guest_name}), "
                    f"please install one."
                )
            else:
                if libvirt_data["guest_state"] == "running" and host_ping(
                    host=libvirt_data["guest_ip"]
                ):
                    logger.info(f"The rhel guest({guest_name}) is running well.")
                else:
                    libvirt_state, guest_ip = (state_guest_bad, guest_down)
                    logger.error(
                        f"The rhel guest({guest_name}) is down, please repair it."
                    )
    finally:
        logger.info(f">>>Libvirt: Compare and update the data in virtwho.ini.")
        libvirt_dict = {
            "server": server,
            "guest_ip": guest_ip,
        }
        if libvirt_data:
            compare_dict = {
                "uuid": [config.libvirt.uuid, libvirt_data["host_uuid"]],
                "hostname": [config.libvirt.hostname, hostname_get(ssh_libvirt)],
                "version": [config.libvirt.version, libvirt_data["host_version"]],
                "cpu": [config.libvirt.cpu, libvirt_data["host_cpu"]],
                "guest_ip": [guest_ip, libvirt_data["guest_ip"]],
                "guest_uuid": [config.libvirt.guest_uuid, libvirt_data["guest_uuid"]],
            }
            for key, value in compare_dict.items():
                if value[0] != value[1]:
                    logger.info(f"The libvirt {key} changed.")
                    libvirt_dict[key] = f"{value[1]} (Updated)"
                    libvirt_state = state_update
        else:
            libvirt_state = state_server_bad

        logger.info(f"Libvirt: the test result is ({libvirt_state})")
        virtwho_ini_update("libvirt", "state", libvirt_state)
        for option, value in libvirt_dict.items():
            virtwho_ini_update("libvirt", option, value)
        return libvirt_state


def rhevm_monitor():
    return "SKIP"


def xen_monitor():
    return "SKIP"


def arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    # esx
    subparsers.add_parser("esx", help="Test the vCenter environment")
    # hyperv
    subparsers.add_parser("hyperv", help="Test the Hyper-V environment")
    # kubevirt
    subparsers.add_parser("kubevirt", help="Test the Kubevirt environment")
    # ahv
    subparsers.add_parser("ahv", help="Test the Nutanix environment")
    # libvirt
    subparsers.add_parser("libvirt", help="Test the libvirt environment")
    # rhevm
    subparsers.add_parser("rhevm", help="Test the RHEVM environment")
    # xen
    subparsers.add_parser("xen", help="Test the Xen environment")
    return parser.parse_args()


if __name__ == "__main__":
    args = arguments_parser()
    if args.command == "esx":
        esx_monitor()
    if args.command == "hyperv":
        hyperv_monitor()
    if args.command == "kubevirt":
        kubevirt_monitor()
    if args.command == "ahv":
        ahv_monitor()
    if args.command == "libvirt":
        libvirt_monitor()
    if args.command == "rhevm":
        rhevm_monitor()
    if args.command == "xen":
        xen_monitor()
