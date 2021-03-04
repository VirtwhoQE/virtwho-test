import yaml

from virt_who import *


class Base:
    @classmethod
    def paramiko_run(cls, cmd, host, username, password, timeout=1800, port=22):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(host, port, username, password, banner_timeout=300)
            ssh._transport.window_size = 2147483647
            chan = ssh.get_transport().open_session()
            chan.settimeout(timeout)
            try:
                chan.exec_command(cmd)
                contents = BytesIO()
                error = BytesIO()
                data = chan.recv(1024)
                while data:
                    contents.write(data)
                    data = chan.recv(1024)
                error_buff = chan.recv_stderr(1024)
                while error_buff:
                    error.write(error_buff)
                    error_buff = chan.recv_stderr(1024)
                exit_status = chan.recv_exit_status()
                output = contents.getvalue()+error.getvalue()
                if type(output) is bytes:
                    output = output.decode("utf-8")
                ssh.close()
                return exit_status, output
            except socket.timeout:
                msg = "timeout exceeded ...({0})".format(host)
                logger.info(msg)
                return -1, msg
        except Exception as e:
            return -1, str(e)
        finally:
            ssh.close()

    @classmethod
    def runcmd(cls, cmd, ssh, timeout=None, desc=None, debug=True, port=22):
        host = ssh['host']
        if ":" in host:
            var = host.split(':')
            host = var[0]
            port = int(var[1])
        username = ssh['username']
        password = ssh['password']
        retcode, stdout = cls.paramiko_run(cmd, host, username, password, timeout, port)
        fd = open(DEBUG_FILE, 'a')
        fd.write(">>> Running in: {0}:{1}, Desc: {2}\n".format(host, port, desc))
        fd.write("Command: {0}\n".format(str(cmd)))
        fd.write("Retcode: {0}\n".format(retcode))
        if debug or retcode != 0:
            try:
                fd.write("Output:\n{0}\n".format(str(stdout)))
            except:
                fd.write("Output:\n{0}\n".format(str(stdout.encode("utf-8"))))
                pass
        fd.close()
        return retcode, stdout.strip()

    @classmethod
    def read_yaml(cls, file):
        """
        :file: should be a yaml file
        :data: list format
        """
        with open(file, encoding='utf-8') as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
            return data

    @classmethod
    def case_get(cls, file):
        """
        :data: should be a list
        :file: should be a yaml file
        """
        case_list = cls.read_yaml(file)
        cases = " or ".join(i for i in case_list)
        return cases
