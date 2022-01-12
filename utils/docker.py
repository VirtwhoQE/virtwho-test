#!/usr/bin/python
import os
import random
import argparse
import sys

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from virtwho import base, logger, FailException
from virtwho.ssh import SSHConnect


def create_rhel_container_by_docker(args):
    """
    Create rhel docker container
    """
    ssh_docker = SSHConnect(
        host=args.docker_server,
        user=args.docker_username,
        pwd=args.docker_password
    )

    # clean docker cache
    ssh_docker.runcmd('docker system prune -f')

    # Check if the container name already exists
    image_name = args.rhel_compose.lower()
    container_port = (args.container_port
                      or
                      docker_container_port(ssh_docker))
    container_name = (args.container_name
                      or
                      docker_container_name(image_name, container_port))
    if docker_container_exist(ssh_docker, container_name):
        logger.warning(f'The docker container {container_name} already exists')
        return

    # copy docker files to docker server
    ssh_docker.runcmd('rm -rf /tmp/docker/;'
                      'rm -rf /tmp/mkimage*;'
                      'rm -f /etc/yum.repos.d/*.repo')
    local_dir = os.path.join(curPath, 'docker/')
    remote_dir = '/tmp/docker/'
    ssh_docker.put_dir(local_dir, remote_dir)

    # Create docker image
    ssh_docker.runcmd('subscription-manager unregister;'
                      'subscription-manager clean')
    docker_image_create(ssh_docker, image_name, args.rhel_compose)

    # Create docker container
    if docker_container_create(ssh_docker, image_name, container_name,
                               container_port, args.container_username,
                               args.container_password):
        ssh_container = SSHConnect(
            host=args.docker_server,
            user=args.container_username,
            pwd=args.container_password,
            port=container_port
        )
        if base.ssh_connect(ssh_container):
            logger.info(
                f'Succeeded to create docker container {container_name} '
                f'({args.docker_server}:{container_port})'
            )
            return f'{args.docker_server}:{container_port}'
    raise FailException(f'Failed to create docker container {container_name}.')


def docker_image_create(ssh, image_name, compose_id):
    if not docker_image_exist(ssh, image_name):
        repo_file = '/tmp/docker/compose.repo'
        base.rhel_compose_repo(ssh, compose_id, repo_file)
        ret, _ = ssh.runcmd(
            f'sh /tmp/docker/mk_image.sh -y {repo_file} {image_name}'
        )
        if ret != 0:
            raise FailException(f'Failed to create docker image {image_name}')


def docker_image_exist(ssh, image_name):
    ret, _ = ssh.runcmd(f'docker images | grep {image_name}')
    if ret == 0:
        return True
    return False


def docker_container_exist(ssh, keyword):
    keyword = str(keyword)
    ret, output = ssh.runcmd(f"docker ps -a | grep '{keyword}'")
    if ret == 0 and keyword in output:
        return True
    return False


def docker_container_port(ssh):
    port = random.randint(53220, 60000)
    while docker_container_exist(ssh, port):
        port = random.randint(53220, 60000)
    return str(port)


def docker_container_name(image_name, container_port):
    name = (image_name.replace('.', '-')
            + '-'
            + container_port)
    return name


def docker_container_create(ssh, image_name, container_name, container_port,
                            container_username, container_password):
    ssh.runcmd(
        f'sh /tmp/docker/mk_container.sh '
        f'-i {image_name} '
        f'-c {container_name} '
        f'-o {container_port} '
        f'-u {container_username} '
        f'-p {container_password}'
    )
    if docker_container_exist(ssh, container_name):
        return True
    return False


def docker_arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--rhel-compose',
        required=True,
        help='Such as: RHEL-7.9-20200917.0, RHEL-8.0-20181005.1')
    parser.add_argument(
        '--docker-server',
        required=True,
        help='')
    parser.add_argument(
        '--docker-username',
        required=True,
        help='')
    parser.add_argument(
        '--docker-password',
        required=True,
        help='')
    parser.add_argument(
        '--container-name',
        required=False,
        default=None,
        help='')
    parser.add_argument(
        '--container-port',
        required=False,
        default=None,
        help='')
    parser.add_argument(
        '--container-username',
        required=False,
        default='root',
        help='')
    parser.add_argument(
        '--container-password',
        required=True,
        help='')
    return parser.parse_args()


if __name__ == "__main__":
    args = docker_arguments_parser()
    create_rhel_container_by_docker(args)
