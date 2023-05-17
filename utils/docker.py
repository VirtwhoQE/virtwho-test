import os
import random
import argparse
import sys
sys.path.append(".")

from virtwho import logger, FailException
from virtwho.base import rhel_compose_repo
from virtwho.ssh import SSHConnect


def create_rhel_container_by_docker(args):
    """
    Create rhel docker container
    """
    ssh_docker = SSHConnect(
        host=args.docker_server, user=args.docker_username, pwd=args.docker_password
    )

    # clean docker cache
    ssh_docker.runcmd("docker system prune -f")

    # Check if the container name already exists
    image_name = args.rhel_compose.lower()
    container_port = args.container_port or docker_container_port(ssh_docker)
    container_name = args.container_name or docker_container_name(
        image_name, container_port
    )
    if docker_container_exist(ssh_docker, container_name):
        logger.warning(f"The docker container {container_name} already exists")
        return

    # copy docker files to docker server
    ssh_docker.runcmd(
        "rm -rf /tmp/docker/;" "rm -rf /tmp/mkimage*;" "rm -f /etc/yum.repos.d/*.repo"
    )
    local_dir = os.path.join(curPath, "docker/")
    remote_dir = "/tmp/docker/"
    ssh_docker.put_dir(local_dir, remote_dir)

    # Create docker image and container
    docker_image_create(ssh_docker, image_name, args.rhel_compose)
    docker_container_create(
        ssh_docker,
        image_name,
        container_name,
        container_port,
        args.container_username,
        args.container_password,
    )
    logger.info(
        f"Succeeded to create docker container:{container_name}, "
        f"port:{container_port}"
    )
    return container_name, container_port


def docker_image_create(ssh, image_name, compose_id):
    """
    Create docker image.
    :param ssh: ssh access to docker server
    :param image_name: image name to create
    :param compose_id: rhel compose id
    """
    if not docker_image_exist(ssh, image_name):
        ssh.runcmd("subscription-manager unregister;" "subscription-manager clean")
        repo_file = "/tmp/docker/compose.repo"
        rhel_compose_repo(ssh, compose_id, repo_file)
        ret, _ = ssh.runcmd(f"sh /tmp/docker/mk_image.sh -y {repo_file} {image_name}")
        if ret != 0:
            raise FailException(f"Failed to create docker image {image_name}")


def docker_container_create(
    ssh,
    image_name,
    container_name,
    container_port,
    container_username,
    container_password,
):
    """
    Create docker container.
    :param ssh: ssh access to docker server
    :param image_name: docker image name
    :param container_name: docker container name
    :param container_port: docker container port
    :param container_username: docker container username
    :param container_password: docker container password
    """
    ssh.runcmd(
        f"sh /tmp/docker/mk_container.sh "
        f"-i {image_name} "
        f"-c {container_name} "
        f"-o {container_port} "
        f"-u {container_username} "
        f"-p {container_password}"
    )
    if not docker_container_exist(ssh, container_name):
        raise FailException(f"Failed to create docker container:{container_name}")


def docker_image_exist(ssh, image_name):
    """
    Check if the docker image exit or not.
    :param ssh: ssh access to docker server
    :param image_name: image name to check
    """
    ret, _ = ssh.runcmd(f"docker images | grep {image_name}")
    if ret == 0:
        return True
    return False


def docker_container_exist(ssh, keyword):
    """
    Check if the docker container exit or not.
    :param ssh: ssh access to docker server
    :param keyword: keywork in container name for checking
    """
    keyword = str(keyword)
    ret, output = ssh.runcmd(f"docker ps -a | grep '{keyword}'")
    if ret == 0 and keyword in output:
        return True
    return False


def docker_container_port(ssh):
    """
    Define the container port with a random number.
    :param ssh: ssh access to docker server
    """
    port = random.randint(53220, 60000)
    while docker_container_exist(ssh, port):
        port = random.randint(53220, 60000)
    return str(port)


def docker_container_name(image_name, container_port):
    """
    Define the container name based on image name and port.
    :param image_name: docker image name
    :param container_port: docker container port
    :return: container name as format imageName-port-666666
    """
    name = image_name.replace(".", "-") + "-port-" + container_port
    return name


def docker_arguments_parser():
    """
    Parse and convert the arguments from command line to parameters
    for function using, and generate help and usage messages for
    each arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rhel-compose",
        required=True,
        help="[Required] Such as: RHEL-7.9-20200917.0, RHEL-8.0-20181005.1",
    )
    parser.add_argument(
        "--docker-server", required=True, help="[Required] IP/Hostname of docker server"
    )
    parser.add_argument(
        "--docker-username",
        required=True,
        help="[Required] Username to access the docker server",
    )
    parser.add_argument(
        "--docker-password",
        required=True,
        help="[Required] Password to access the docker server",
    )
    parser.add_argument(
        "--container-name",
        required=False,
        default=None,
        help="[Optional] Default to make by the rhel compose id and " "container port",
    )
    parser.add_argument(
        "--container-port",
        required=False,
        default=None,
        help="[Optional] Default to create one randomly",
    )
    parser.add_argument(
        "--container-username",
        required=False,
        default="root",
        help="[Optional] Default to user root",
    )
    parser.add_argument(
        "--container-password", required=True, help="[Required] container password"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = docker_arguments_parser()
    create_rhel_container_by_docker(args)
