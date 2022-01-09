#!/usr/bin/python
import os
import random
import argparse

from virtwho import base, logger, FailException
from virtwho.ssh import SSHConnect


def create_rhel_docker_container(args):
    """
    Install rhel by submitting job to beaker with required arguments.
    Please refer to the utils/README for usage.
    :param args:
        rhel_compose: required option, such as RHEL-7.9-20200917.0.
        arch: required option, such as x86_64, s390x, ppc64...
        variant: optional, default using BaseOS for rhel8 and later.
        job_group: optional, associate a group to this job.
        host: optional, define/filter system as hostrequire
        host_type: optional, physical or virtual
        host_require: optional, other hostRequires for job,
            separate multiple options with commas.
    """
    ssh_docker = SSHConnect(
        host=args.docker_server,
        user=args.docker_username,
        pwd=args.docker_password
    )
    # clean docker cache
    ssh_docker.runcmd('docker system prune -f')
    # copy docker files to docker server
    cur_path = os.path.abspath(os.path.dirname(__file__))
    root_path = os.path.split(cur_path)[0]
    local_dir = os.path.join(root_path, 'docker/')
    remote_dir = '/tmp/docker/'
    ssh_docker.runcmd('rm -rf /tmp/docker/;'
                      'rm -rf /tmp/mkimage*;'
                      'rm -f /etc/yum.repos.d/*.repo')
    ssh_docker.runcmd('subscription-manager unregister;'
                      'subscription-manager clean')
    ssh_docker.put_dir(local_dir, remote_dir)
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
    # Create docker image and container
    docker_image_create(ssh_docker, image_name, args.rhel_compose)
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
                f'Succeeded to create docker container ({container_name}), '
                f'the ip is {args.docker_server}:{container_port}'
            )
            return args.docker_server, container_port
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
        required=True,
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
    create_rhel_docker_container(args)
