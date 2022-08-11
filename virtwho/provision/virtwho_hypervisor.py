#!/usr/bin/python
import os
import sys
import argparse

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(os.path.split(rootPath)[0])

from virtwho import logger, FailException
from virtwho.settings import config
from hypervisor.virt.libvirt.libvirtcli import LibvirtCLI
from virtwho.ssh import SSHConnect
from virtwho.base import hostname_get
from utils.properties_update import virtwho_ini_props_update


def libvirt_test(args):
    """
    """
    logger.info(f'+++ Start to test the Libvirt Environment +++')
    status = 'GOOD'
    server = config.libvirt.server
    username = config.libvirt.username
    password = config.libvirt.password
    uuid = config.libvirt.uuid
    hostname = config.libvirt.hostname
    version = config.libvirt.version
    cpu = config.libvirt.cpu
    guest_ip = config.libvirt.guest_ip
    guest_uuid = config.libvirt.guest_uuid
    guest_name = config.libvirt.guest_name
    data = {}
    libvirt = LibvirtCLI(
        server=server,
        ssh_user=username,
        ssh_passwd=password
    )
    ssh_libvirt = SSHConnect(
        host=server,
        user=username,
        pwd=password
    )
    try:
        logger.info(f'>>>Libvirt: Check if the libvirt host is running.')
        ret = os.system(f'ping -c 2 -w 5 {server}')
        if ret != 0:
            status, server, guest_ip, guest_uuid = \
                'BAD (Server Down)', 'Down', 'None', 'None'
            raise FailException(
                f'The libvirt host has broken, please repaire it.'
            )

        logger.info(f'>>>Libvirt: Check the rhel guest exist or not.')
        ret = libvirt.guest_exist(guest_name)
        if not ret:
            logger.warning(f'Did not find the rhel guest ({guest_name}), '
                           f'will deploy a new one.')
            # libvirt.guest_add(args.guest_name)

        logger.info(f'>>>Libvirt: Check the rhel guest status.')
        guest_status = libvirt.guest_status(guest_name)
        if guest_status == 'running':
            logger.info(f'The rhel guest({guest_name}) is running well.')
        if guest_status == 'paused':
            logger.info(f'The rhel guest({guest_name}) is paused, '
                        f'will resume it.')
            ret = libvirt.guest_resume(guest_name)
            if ret is False:
                status, guest_ip, guest_uuid = \
                    'BAD (Guest Broke)', 'None', 'None'
                raise FailException(f'Failed to resume the rhel guest'
                                    f'({guest_name}) from paused status.')
        if guest_status in ['shut off', 'false']:
            logger.info(f'The rhel guest({guest_name}) was down, '
                        f'will start it.')
            ret = libvirt.guest_start(guest_name)
            if ret is False:
                status, guest_ip, guest_uuid = \
                    'BAD (Guest Broke)', 'None', 'None'
                raise FailException(f'Failed to start the rhel guest'
                                    f'({guest_name}) from shut off status.')

        logger.info(f'>>>Libvirt: Get the hypervisor and guest data.')
        data = libvirt.guest_search(guest_name)
        logger.info(f'=== Succeeded to get the libvirt data\n{data}\n===')

    finally:
        logger.info(f'>>>Libvirt: Compare and update the data.')
        libvirt_dict = {
            'status': status,
            'server': server,
            'guest_ip': guest_ip,
        }
        if data:
            compare_dict = {
                'uuid': [uuid, data['host_uuid']],
                'hostname': [hostname, hostname_get(ssh_libvirt)],
                'version': [version, data['host_version']],
                'cpu': [cpu, data['host_cpu']],
                'guest_ip': [guest_ip, data['guest_ip']],
                'guest_uuid': [guest_uuid, data['guest_uuid']]
            }
            for key, value in compare_dict.items():
                if value[0] != value[1]:
                    logger.info(f'The libvirt {key} changed.')
                    libvirt_dict['status'] = 'UPDATED'
                    libvirt_dict[key] = f'{value[1]} (Updated)'
        for (args.option, args.value) in libvirt_dict.items():
            args.section = 'libvirt'
            virtwho_ini_props_update(args)


def arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')
    # libvirt
    subparsers.add_parser(
        'libvirt',
        help='Test the libvirt environment')

    # esx
    return parser.parse_args()


if __name__ == "__main__":
    args = arguments_parser()
    if args.command == 'libvirt':
        libvirt_test(args)
