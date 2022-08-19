#!/usr/bin/python
import os
import sys
import argparse

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(os.path.split(rootPath)[0])

from virtwho import logger, FailException
from virtwho.settings import config
from virtwho.ssh import SSHConnect
from virtwho.base import hostname_get
from utils.properties_update import virtwho_ini_props_update
from hypervisor.virt.libvirt.libvirtcli import LibvirtCLI
from hypervisor.virt.esx.powercli import PowerCLI

status_good = 'GOOD'
status_update = 'UPDATED'
status_server_bad = 'BAD (Server Broke)'
status_guest_bad = 'BAD (Guest Broke)'
server_broke = 'Broke'
guest_none = 'None'
guest_paused = 'Paused'
guest_off = 'Off'


def esx_check(args):
    """
    """
    esx_status = status_good
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
        logger.info(f'>>>vCenter: Check if the vCenter server is running.')
        ret1 = os.system(f'ping -c 2 -w 5 {server}')
        if ret1 != 0:
            esx_status, server = (status_server_bad, server_broke)
            logger.error(
                f'The vCenter Server has broken, please repaire it.'
            )

        logger.info(f'>>>vCenter: Check if the esxi host is running.')
        ret2 = os.system(f'ping -c 2 -w 5 {esx_ip}')
        if ret2 != 0:
            esx_status, esx_ip = ('BAD (ESXi Host Down)', 'Broke')
            logger.error(
                f'The esxi host has broken, please repaire it.'
            )

        logger.info(f'>>>vCenter: Check if the windows client is running.')
        ret3 = os.system(f'ping -c 2 -w 5 {client_server}')
        if ret3 != 0:
            esx_status, esx_ip = ('BAD (Windows Client Down)', 'Broke')
            logger.error(
                f'The windows Client has broken, please repaire it.'
            )

        if ret1 == 0 and ret2 == 0 and ret3 == 0:
            logger.info(f'>>>vCenter: Check if the rhel guest exists.')
            ret4 = esx.guest_exist(guest_name)
            if not ret4:
                logger.warning(f'Did not find the rhel guest ({guest_name}), '
                               f'will deploy a new one.')
                ret4 = esx.guest_add(
                    host=esx_ip,
                    host_ssh_user=config.esx.esx_username,
                    host_ssh_pwd=config.esx.esx_password,
                    guest_name=guest_name,
                    image_path=''
                )

            if ret4:
                logger.info(f'>>>vCenter: Check the rhel guest state.')
                guest_state = esx.guest_search(guest_name)['guest_state']
                if guest_state == 1:
                    logger.info(
                        f'The rhel guest({guest_name}) is running well.')
                if guest_state == 2:
                    logger.info(f'The rhel guest({guest_name}) is paused, '
                                f'will resume it.')
                    ret = esx.guest_resume(guest_name)
                    if ret is False:
                        esx_status, guest_ip = (status_guest_bad, guest_paused)
                        logger.error(f'Failed to resume the rhel guest'
                                     f'({guest_name}) from paused status.')
                if guest_state == 0:
                    logger.info(f'The rhel guest({guest_name}) was power off, '
                                f'will start it.')
                    ret = esx.guest_start(guest_name)
                    if ret is False:
                        esx_status, guest_ip = (status_guest_bad, guest_off)
                        logger.error(f'Failed to start the rhel guest'
                                     f'({guest_name}) from power off status.')

                logger.info(f'>>>vCenter: Get all the necessary data.')
                esx_data = esx.guest_search(guest_name, uuid_info=True)
                logger.info(
                    f'=== Succeeded to get the vCenter data\n{esx_data}\n===')
            else:
                esx_status, guest_ip = (status_guest_bad, guest_none)
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
                    esx_status = status_update
        args.section, args.option, args.value = (
            'hypervisors_status', 'esx', esx_status
        )
        virtwho_ini_props_update(args)
        for (args.option, args.value) in esx_dict.items():
            args.section = 'esx'
            virtwho_ini_props_update(args)


def hyperv_check(args):
    pass


def kubevirt_check(args):
    pass


def ahv_check(args):
    pass


def libvirt_check(args):
    """
    """
    libvirt_status = status_good
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
        ret1 = os.system(f'ping -c 2 -w 5 {server}')
        if ret1 != 0:
            libvirt_status, server, guest_ip = (
                status_server_bad, server_broke, guest_none
            )
            logger.error(f'The libvirt host has broken, please repaire it.')

        else:
            logger.info(f'>>>Libvirt: Check if the rhel guest exists.')
            ret2 = libvirt.guest_exist(guest_name)
            if not ret2:
                logger.error(f'Did not find the rhel guest ({guest_name}), '
                             f'will deploy a new one.')
                # ret = libvirt.guest_add(args.guest_name)  #not ready
                ret2 = True

            if ret2:
                logger.info(f'>>>Libvirt: Check the rhel guest state.')
                guest_state = libvirt.guest_status(guest_name)
                if guest_state == 'running':
                    logger.info(
                        f'The rhel guest({guest_name}) is running well.')
                if guest_state == 'paused':
                    logger.info(f'The rhel guest({guest_name}) is paused, '
                                f'will resume it.')
                    ret = libvirt.guest_resume(guest_name)
                    if ret is False:
                        libvirt_status, guest_ip = (
                            status_guest_bad, guest_paused
                        )
                        logger.error(f'Failed to resume the rhel guest'
                                     f'({guest_name}) from paused status.')
                if guest_state in ['shut off', 'false']:
                    logger.info(f'The rhel guest({guest_name}) was down, '
                                f'will start it.')
                    ret = libvirt.guest_start(guest_name)
                    if ret is False:
                        libvirt_status, guest_ip = (status_guest_bad, guest_off)
                        logger.error(f'Failed to start the rhel guest'
                                     f'({guest_name}) from shut off status.')

                logger.info(f'>>>Libvirt: Get the libvirt env data.')
                libvirt_data = libvirt.guest_search(guest_name)
                logger.info(
                    f'=== Succeeded to get the libvirt data\n{libvirt_data}\n===')
            else:
                libvirt_status, guest_ip = (status_guest_bad, guest_none)

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
                    libvirt_status = status_update
        args.section, args.option, args.value = (
            'hypervisors_status', 'libvirt', libvirt_status
        )
        virtwho_ini_props_update(args)
        for (args.option, args.value) in libvirt_dict.items():
            args.section = 'libvirt'
            virtwho_ini_props_update(args)


def rhevm_check(args):
    pass


def xen_check(args):
    pass


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
        esx_check(args)
    if args.command == 'hyperv':
        hyperv_check(args)
    if args.command == 'kubevirt':
        kubevirt_check(args)
    if args.command == 'ahv':
        ahv_check(args)
    if args.command == 'libvirt':
        libvirt_check(args)
    if args.command == 'rhevm':
        rhevm_check(args)
    if args.command == 'xen':
        xen_check(args)
