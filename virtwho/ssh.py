import os
import paramiko
from virtwho import logger


class SSHConnect:
    """Extended SSHClient allowing custom methods"""

    def __init__(self, host, user, pwd=None, rsafile=None, port=22, timeout=3000):
        """
        :param str host: The hostname or ip of the server to establish connection.
        :param str user: The username to use when connecting.
        :param str pwd: The password to use when connecting.
        :param str rsafile: The path of the ssh private key to use when connecting to the server
        :param int port: The server port to connect to, the default port is 22.
        :param int timeout: Time (seconds) to wait for the ssh command to finish.
        """
        self.host = host
        self.user = user
        self.pwd = pwd
        self.rsa = rsafile
        self.port = int(port)
        self.timeout = timeout
        self.err = "passwd or rsafile can not be None"

    def _connect(self):
        """SSH command execution connection"""
        if self.pwd:
            return self.pwd_connect()
        elif self.rsa:
            return self.rsa_connect()
        else:
            # it will try to use keys from SSH AutoAgent
            return self.pwd_connect()

    def _transfer(self):
        """Sftp download/upload execution connection"""
        if self.pwd:
            return self.pwd_transfer()
        elif self.rsa:
            return self.rsa_transfer()
        else:
            # it will try to use keys from SSH AutoAgent
            return self.pwd_transfer()

    def pwd_connect(self):
        """SSH command execution connection by password"""
        ssh = ""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if self.pwd:
                ssh.connect(self.host, self.port, self.user, self.pwd, timeout=self.timeout)
            else:
                logger.info("ssh connect will try to use ssh-agent")
                ssh.connect(hostname=self.host,
                            port=self.port,
                            username=self.user,
                            timeout=self.timeout)
            return ssh
        except Exception:
            raise ConnectionError(f"Failed to ssh connect the {self.host}.")

    def rsa_connect(self):
        """SSH command execution connection by key file"""
        pkey = paramiko.RSAKey.from_private_key_file(self.rsa)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.host, self.port, self.user, pkey=pkey, timeout=self.timeout)
        return ssh

    def pwd_transfer(self):
        """Sftp download/upload execution connection by password"""
        # transport = paramiko.Transport((self.host, self.port))
        # transport.connect(username=self.user, password=self.pwd)
        # sftp = paramiko.SFTPClient.from_transport(transport)
        # return sftp, transport
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.host, self.port, self.user, self.pwd, timeout=self.timeout)
            return ssh.open_sftp(), ssh.get_transport()
        except Exception:
            raise ConnectionError(f"Failed to ssh connect the {self.host}.")

    def rsa_transfer(self):
        """Sftp download/upload execution connection by key file"""
        pkey = paramiko.RSAKey.from_private_key_file(self.rsa)
        transport = paramiko.Transport((self.host, self.port))
        transport.connect(username=self.user, pkey=pkey)
        sftp = paramiko.SFTPClient.from_transport(transport)
        return sftp, transport

    def runcmd(self, cmd, if_stdout=False, log_print=True):
        """Executes SSH command on remote hostname.
        :param str cmd: The command to run
        :param str if_stdout: default to return to stderr
        :param str log_print: default to print the output
        """
        ssh = self._connect()
        logger.info(f"[{self.host}:{self.port}] >>> {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        code = stdout.channel.recv_exit_status()
        stdout, stderr = stdout.read(), stderr.read()
        ssh.close()
        if if_stdout or not stderr:
            if log_print:
                logger.info("<<< stdout\n{}".format(stdout.decode()))
            return code, stdout.decode()
        else:
            if log_print:
                logger.info("<<< stderr\n{}".format(stderr.decode()))
            return code, stderr.decode()

    def get_file(self, remote_file, local_file):
        """Download a remote file to the local machine."""
        sftp, conn = self._transfer()
        sftp.get(remote_file, local_file)
        conn.close()

    def put_file(self, local_file, remote_file):
        """Upload a local file to a remote machine
        :param local_file: either a file path or a file-like object to be uploaded.
        :param remote_file: a remote file path where the uploaded file will be placed.
        """
        sftp, conn = self._transfer()
        sftp.put(local_file, remote_file)
        conn.close()

    def remove_file(self, remote_file):
        """Remove the file at the given path.
        :param remote_file: a remote file path to remove
        """
        sftp, conn = self._transfer()
        sftp.remove(remote_file)
        conn.close()

    def put_dir(self, local_dir, remote_dir):
        """Upload all files from directory to a remote directory
        :param local_dir: all files from local path to be uploaded.
        :param remote_dir: a remote path where the uploaded files will be placed.
        """
        sftp, conn = self._transfer()
        for root, dirs, files in os.walk(local_dir):
            for filespath in files:
                local_file = os.path.join(root, filespath)
                a = local_file.replace(local_dir, "")
                remote_file = os.path.join(remote_dir, a)
                try:
                    sftp.put(local_file, remote_file)
                except Exception:
                    sftp.mkdir(os.path.split(remote_file)[0])
                    sftp.put(local_file, remote_file)
            for name in dirs:
                local_path = os.path.join(root, name)
                a = local_path.replace(local_dir, "")
                remote_path = os.path.join(remote_dir, a)
                try:
                    sftp.mkdir(remote_path)
                except Exception as e:
                    logger.info(e)
        conn.close()
