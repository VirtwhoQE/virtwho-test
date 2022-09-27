#!/usr/bin/python
import os
import sys
import argparse
import time

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(os.path.split(rootPath)[0])

from virtwho import logger, FailException
from virtwho.settings import config
from virtwho.ssh import SSHConnect
from virtwho.base import hostname_get, ipaddr_get, host_ping
from utils.properties_update import virtwho_ini_update
from utils.properties_update import virtwho_ini_props_update
from hypervisor.virt.libvirt.libvirtcli import LibvirtCLI
from hypervisor.virt.esx.powercli import PowerCLI
from hypervisor.virt.hyperv.hypervcli import HypervCLI

state_good = 'GOOD'
state_update = 'UPDATED'
state_server_bad = 'BAD (Server Broke)'
state_guest_bad = 'BAD (Guest Broke)'
server_broke = 'Broke'
guest_none = 'None'
guest_paused = 'Paused'
guest_off = 'Off'


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
        client_passwd=config.esx.ssh_password
    )
    try:
        logger.info(f'>>>vCenter: Check if the vCenter server is running well.')
        ret1 = host_ping(host=server)
        if not ret1:
            esx_state, server = (state_server_bad, server_broke)
            logger.error(
                f'The vCenter Server has broken, please repaire it.'
            )

        logger.info(f'>>>vCenter: Check if the esxi host is running well.')
        ret2 = host_ping(host=esx_ip)
        if not ret2:
            esx_state, esx_ip = ('BAD (ESXi Host Down)', 'Broke')
            logger.error(
                f'The esxi host has broken, please repaire it.'
            )

        logger.info(f'>>>vCenter: Check if the windows client is running.')
        ret3 = host_ping(host=client_server)
        if not ret3:
            esx_state, esx_ip = ('BAD (Windows Client Down)', 'Broke')
            logger.error(
                f'The windows Client has broken, please repaire it.'
            )

        if ret1 and ret2 and ret3:
            logger.info(f'>>>vCenter: Check if the rhel guest exists.')
            ret = esx.guest_exist(guest_name)
            if not ret:
                # logger.warning(f'Did not find the rhel guest ({guest_name}), '
                #                f'will deploy a new one.')
                # ret4 = esx.guest_add(
                #     host=esx_ip,
                #     host_ssh_user=config.esx.esx_username,
                #     host_ssh_pwd=config.esx.esx_password,
                #     guest_name=guest_name,
                #     image_path=''
                # )
                esx_state, guest_ip = (state_guest_bad, guest_none)
                logger.error(f'Did not find the rhel guest ({guest_name}), '
                             f'please install one.')
            else:
                logger.info(f'>>>vCenter: Check the rhel guest state.')
                guest_state = esx.guest_search(guest_name)['guest_state']
                if guest_state == 1:
                    logger.info(
                        f'The rhel guest({guest_name}) is running well.')
                if guest_state == 2:
                    logger.warning(f'The rhel guest({guest_name}) is paused, '
                                   f'please resume it.')
                    esx_state, guest_ip = (state_guest_bad, guest_paused)
                if guest_state == 0:
                    logger.warning(f'The rhel guest({guest_name}) was power off, '
                                   f'please start it.')
                    esx_state, guest_ip = (state_guest_bad, guest_off)

                logger.info(f'>>>vCenter: Get all the necessary data.')
                esx_data = esx.guest_search(guest_name, uuid_info=True)
                logger.info(
                    f'=== Succeeded to get the vCenter data\n{esx_data}\n===')
        else:
            guest_ip = guest_none

    finally:
        logger.info(f'>>>vCenter: Update the data of virtwho.ini.')
        esx_dict = {
            'server': server,
            'esx_ip': esx_ip,
            'guest_ip': guest_ip,
        }
        if esx_data:
            compare_dict = {
                'esx_uuid': [config.esx.esx_uuid, esx_data['esx_uuid']],
                'esx_hwuuid': [config.esx.esx_hwuuid, esx_data['esx_hwuuid']],
                'esx_hostname': [config.esx.esx_hostname,
                                 esx_data['esx_hostname']],
                'esx_version': [config.esx.esx_version,
                                esx_data['esx_version']],
                'esx_cpu': [config.esx.esx_cpu, esx_data['esx_cpu']],
                'esx_cluster': [config.esx.esx_cluster,
                                esx_data['esx_cluster']],
                'guest_ip': [config.esx.guest_ip, esx_data['guest_ip']],
                'guest_uuid': [config.esx.guest_uuid, esx_data['guest_uuid']]
            }
            for key, value in compare_dict.items():
                if value[0] != value[1]:
                    logger.info(f'The vCenter {key} changed.')
                    esx_dict[key] = f'{value[1]} (Updated)'
                    esx_state = state_update
        else:
            esx_state = state_guest_bad

        logger.info(f'vCenter: the test result is ({esx_state})')
        virtwho_ini_update('esx', 'state', esx_state)
        for (option, value) in esx_dict.items():
            virtwho_ini_update('esx', option, value)
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
        server=server,
        ssh_user=config.hyperv.username,
        ssh_pwd=config.hyperv.password
    )
    try:
        logger.info(f'>>>Hyperv: Check if the hypervisor is running.')
        if not host_ping(host=server):
            hyperv_state, server, guest_ip = (
                state_server_bad, server_broke, guest_none
            )
            logger.error(f'The hyperv host has broken, please repaire it.')

        else:
            logger.info(f'>>>Hyperv: Check if the rhel guest exists.')
            ret = hyperv.guest_exist(guest_name)
            if not ret:
                # logger.error(f'Did not find the rhel guest ({guest_name}), '
                #              f'will deploy a new one.')
                # ret = hyperv.guest_add(guest_name, guest_path)
                hyperv_state, guest_ip = (state_guest_bad, guest_none)
                logger.error(f'Did not find the rhel guest ({guest_name}), '
                             f'please install one.')
            else:
                logger.info(f'>>>Hyperv: Check the rhel guest state.')
                guest_state = hyperv.guest_info(guest_name)['guest_state']
                if guest_state == 2:
                    logger.info(
                        f'The rhel guest({guest_name}) is running well.')
                if guest_state == 9:
                    logger.warning(f'The rhel guest({guest_name}) is paused, '
                                   f'please resume it.')
                    hyperv_state, guest_ip = (state_guest_bad, guest_paused)
                if guest_state == 3:
                    logger.warning(f'The rhel guest({guest_name}) was power off, '
                                   f'please start it.')
                    hyperv_state, guest_ip = (state_guest_bad, guest_off)

        logger.info(f'>>>Hyperv: Get the hypervisor data.')
        hyperv_data = hyperv.guest_search(guest_name, )
        logger.info(
            f'=== Succeeded to get the hyperv data\n{hyperv_data}\n===')

    finally:
        logger.info(f'>>>Hyperv: Compare and update the data in virtwho.ini.')
        hyperv_dict = {
            'server': server,
            'guest_ip': guest_ip,
        }
        if hyperv_data:
            compare_dict = {
                'uuid': [config.hyperv.uuid,
                         hyperv_data['hyperv_uuid']],
                'hostname': [config.hyperv.hostname,
                             hyperv_data['hyperv_hostname']],
                # 'version': [config.hyperv.version,
                #             hyperv_data['hyperv_version']],
                'cpu': [config.hyperv.cpu,
                        hyperv_data['hyperv_cpu']],
                'guest_ip': [guest_ip,
                             hyperv_data['guest_ip']],
                'guest_uuid': [config.hyperv.guest_uuid,
                               hyperv_data['guest_uuid']]
            }
            for key, value in compare_dict.items():
                if value[0] != value[1]:
                    logger.info(f'The hyperv({key}) changed.')
                    hyperv_dict[key] = f'{value[1]} (Updated)'
                    hyperv_state = state_update
        else:
            hyperv_state = state_guest_bad

        logger.info(f'Hyperv: the test result is ({hyperv_state})')
        virtwho_ini_update('hyperv', 'state', hyperv_state)
        for (option, value) in hyperv_dict.items():
            virtwho_ini_update('hyperv', option, value)
        return hyperv_state


def kubevirt_monitor():
    return 'SKIP'


def ahv_monitor():
    return 'SKIP'


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
        ssh_passwd=config.libvirt.password
    )
    ssh_libvirt = SSHConnect(
        host=server,
        user=config.libvirt.username,
        pwd=config.libvirt.password
    )
    try:
        logger.info(f'>>>Libvirt: Check if the libvirt host is running.')
        libvirt_ip = ipaddr_get(ssh_libvirt)
        if not libvirt_ip:
            libvirt_state, server, guest_ip = (
                state_server_bad, server_broke, guest_none
            )
            logger.error(f'The libvirt host has broken, please repaire it.')
        else:
            logger.info(f'>>>Libvirt: Check if the rhel guest exists.')
            ret = libvirt.guest_exist(guest_name)
            if not ret:
                # logger.error(f'Did not find the rhel guest ({guest_name}), '
                #              f'will deploy a new one.')
                # ret = libvirt.guest_add(args.guest_name)  #not ready
                libvirt_state, guest_ip = (state_guest_bad, guest_none)
                logger.error(f'Did not find the rhel guest ({guest_name}), '
                             f'please install one.')
            else:
                logger.info(f'>>>Libvirt: Check the rhel guest state.')
                guest_state = libvirt.guest_status(guest_name)
                if guest_state == 'running':
                    logger.info(
                        f'The rhel guest({guest_name}) is running well.')
                if guest_state == 'paused':
                    logger.warning(f'The rhel guest({guest_name}) is paused, '
                                   f'please resume it.')
                    libvirt_state, guest_ip = (state_guest_bad, guest_paused)
                if guest_state in ['shut off', 'false']:
                    logger.warning(f'The rhel guest({guest_name}) was down, '
                                   f'please start it.')
                    libvirt_state, guest_ip = (state_guest_bad, guest_off)

                logger.info(f'>>>Libvirt: Get the libvirt env data.')
                libvirt_data = libvirt.guest_search(guest_name)
                logger.info(f'=== Succeeded to get the libvirt data\n'
                            f'{libvirt_data}\n ===')
    finally:
        logger.info(f'>>>Libvirt: Compare and update the data in virtwho.ini.')
        libvirt_dict = {
            'server': server,
            'guest_ip': guest_ip,
        }
        if libvirt_data:
            compare_dict = {
                'uuid': [config.libvirt.uuid, libvirt_data['host_uuid']],
                'hostname': [config.libvirt.hostname,
                             hostname_get(ssh_libvirt)],
                'version': [config.libvirt.version,
                            libvirt_data['host_version']],
                'cpu': [config.libvirt.cpu, libvirt_data['host_cpu']],
                'guest_ip': [guest_ip, libvirt_data['guest_ip']],
                'guest_uuid': [config.libvirt.guest_uuid,
                               libvirt_data['guest_uuid']]
            }
            for key, value in compare_dict.items():
                if value[0] != value[1]:
                    logger.info(f'The libvirt {key} changed.')
                    libvirt_dict[key] = f'{value[1]} (Updated)'
                    libvirt_state = state_update
        else:
            libvirt_state = state_guest_bad

        logger.info(f'Libvirt: the test result is ({libvirt_state})')
        virtwho_ini_update('libvirt', 'state', libvirt_state)
        for (option, value) in libvirt_dict.items():
            virtwho_ini_update('libvirt', option, value)
        return libvirt_state


def rhevm_monitor():
    return 'SKIP'


def xen_monitor():
    return 'SKIP'


def arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')
    # esx
    subparsers.add_parser(
        'esx',
        help='Test the vCenter environment')
    # hyperv
    subparsers.add_parser(
        'hyperv',
        help='Test the Hyper-V environment')
    # kubevirt
    subparsers.add_parser(
        'kubevirt',
        help='Test the Kubevirt environment')
    # ahv
    subparsers.add_parser(
        'ahv',
        help='Test the Nutanix environment')
    # libvirt
    subparsers.add_parser(
        'libvirt',
        help='Test the libvirt environment')
    # rhevm
    subparsers.add_parser(
        'rhevm',
        help='Test the RHEVM environment')
    # xen
    subparsers.add_parser(
        'xen',
        help='Test the Xen environment')
    return parser.parse_args()


if __name__ == "__main__":
    args = arguments_parser()
    if args.command == 'esx':
        esx_monitor()
    if args.command == 'hyperv':
        hyperv_monitor()
    if args.command == 'kubevirt':
        kubevirt_monitor()
    if args.command == 'ahv':
        ahv_monitor()
    if args.command == 'libvirt':
        libvirt_monitor()
    if args.command == 'rhevm':
        rhevm_monitor()
    if args.command == 'xen':
        xen_monitor()


# def hypervisor_state(mode):
#     os.system(
#         f'python {curPath}/virtwho_hypervisor.py {mode}'
#     )
