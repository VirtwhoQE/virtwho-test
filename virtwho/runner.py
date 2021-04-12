import json
import queue
import re
import threading
import time
from virtwho.configure import virtwho_ssh_connect
from virtwho.logger import getLogger

logger = getLogger(__name__)


class Runner:

    def __init__(self, mode, register_type):
        """
        - self.config_file is used to define virt-who configuration.
        - self.rhsm_log_file is used to store the latest rhsm log.

        :param mode: the hypervisor mode.
            (esx, xen, hyperv, rhevm, libvirt, kubevirt, local)
        :param register_type: the subscription server. (rhsm, satellite)
        """
        self.mode = mode
        self.register_type = register_type
        self.config_file = f'/etc/virt-who.d/{self.mode}.conf'
        self.rhsm_log_file = '/root/vw-rhsm.log'
        self.ssh = virtwho_ssh_connect(self.mode)

    def run_virtwho_cli(self,
                        debug=True,
                        oneshot=True,
                        interval=None,
                        config='default',
                        wait=None):
        """
        Run virt-who by command line and return log.
        Use parameters to define options in command line.

        :param debug: use '-d' option when debug is True.
        :param oneshot: use '-o' option when oneshot is True.
        :param interval: use '-i' option when configure interval time.
        :param config: use '-c' option to define virt-who configuration
            file when define the config para.
            Default using '/etc/virt-who.d/mode.conf'.
        :param wait: set wait time before stop virt-who service when
            test interval function.
        :return: tty_output
        """
        cmd = 'virt-who '
        if debug is True:
            cmd += '-d '
        if oneshot is True:
            cmd += '-o '
        if interval:
            cmd += f'-i {interval} '
        if config:
            if config == 'default':
                config = f'{self.config_file}'
            cmd += f'-c {config} '
        tty_output, rhsm_output = self.vw_start(cli=cmd, wait=wait)
        return tty_output

    def run_virtwho_service(self, wait=None):
        """
        Run virt-who by start service and return log.

        :param wait: set wait time before stop virt-who service when
            test interval function.
        :return: tty_output and rhsm_output
        """
        tty_output, rhsm_output = self.vw_start(wait=wait)
        return tty_output, rhsm_output

    def log_analyzer(self,
                     rhsm_log,
                     send_number=1,
                     error_number=0,
                     error_list=None,
                     report_id=None,
                     interval_time=None,
                     loop_number=None,
                     loop_time=None):
        """

        :param rhsm_log: the log to be analyzed.
        :param send_number:
        :param error_number:
        :param error_list:
        :param report_id:
        :param interval_time:
        :param loop_number:
        :param loop_time:
        :return:
        """
        analyzer_list = list()
        if send_number:
            send_number_get = self.vw_send_number(rhsm_log)
            logger.info(f'The send number get from log is {send_number_get}')
            analyzer_list.append(send_number_get == send_number)
        if error_number:
            error_number_get = self.vw_error_number(rhsm_log)
            logger.info(f'The error number get from log is {error_number_get}')
            if error_number == 'nonzero' or error_number == 'nz':
                analyzer_list.append(error_number_get > 0)
            analyzer_list.append(error_number_get == error_number)
        if error_list:
            error_list_get = self.vw_error_list()
            logger.info(f'The error list get from log is {error_list_get}')
            analyzer_list.append(
                self.msg_search(str(error_list_get), error_list)
            )
        if report_id:
            report_id_get = self.vw_report_id(rhsm_log)
            logger.info(f'The report id get from log is {report_id_get}')
            analyzer_list.append(report_id_get == report_id)
        if interval_time:
            interval_time_get = self.vw_interval_time(rhsm_log)
            logger.info(f'The interval time get from log is '
                        f'{interval_time_get}')
            analyzer_list.append(interval_time_get == interval_time)
        if loop_number:
            loop_number_get = self.vw_loop_number()[1]
            logger.info(f'The loop number get from log is {loop_number_get}')
            analyzer_list.append(loop_number_get == loop_number)
        if loop_time:
            loop_time_get = self.vw_loop_time()
            logger.info(f'The loop time get from log is {loop_time_get}')
            analyzer_list.append(loop_time_get == loop_time)
        if 'False' in analyzer_list:
            return False
        else:
            return True

    def vw_start(self, cli=None, wait=None):
        for i in range(4):
            tty_output, rhsm_output = self.vw_start_thread(cli, wait)
            if self.vw_429_error():
                wait_time = 60 * (i + 3)
                logger.warning(
                    f'429 code found, re-register virt-who host and try again '
                    f'after {wait_time} seconds...')
                # self.re_register() need to be defined after register.py finished.
                time.sleep(wait_time)
            elif len(re.findall(
                    'RemoteServerException: Server error attempting a '
                    'GET.*returned status 500',
                    rhsm_output, re.I)) > 0:
                logger.warning(
                    'RemoteServerException return 500 code, restart '
                    'virt-who again after 60s')
                time.sleep(60)
            else:
                logger.info('Finished to run virt-who')
                return tty_output, rhsm_output
        if self.vw_429_error():
            raise AssertionError('Failed due to 429 code, please check')
        else:
            logger.warning('Run virt-who abnormally, please check')
            return tty_output, rhsm_output

    def vw_start_thread(self, cli, wait):
        q = queue.Queue()
        results = list()
        threads = list()
        tty_output = ''
        rhsm_output = ''
        self.kill_pid_by_name("virt-who")
        t1 = threading.Thread(target=self.get_rhsm_log,
                              args=(q, self.rhsm_log_file))
        t2 = threading.Thread(target=self.vw_thread_run,
                              args=(q, cli))
        t3 = threading.Thread(target=self.vw_thread_timeout,
                              args=(cli, wait))
        threads.append(t1)
        threads.append(t2)
        threads.append(t3)
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        while not q.empty():
            results.append(q.get())
        for item in results:
            if item[0] == 'tty_output':
                tty_output = item[1]
            if item[0] == 'rhsm_output':
                rhsm_output = item[1]
        return tty_output, rhsm_output

    def vw_thread_run(self, q, cli):
        if cli:
            logger.info(f'Start to run virt-who by cli: {cli}')
            ret, tty_output = self.ssh.runcmd(cli)
        else:
            logger.info('Start to run virt-who by service')
            ret, tty_output = self.run_service()
        q.put(('tty_output', tty_output))

    def vw_thread_timeout(self, cli, wait):
        oneshot = self.vw_oneshot_check(cli)
        if wait:
            time.sleep(wait)
        for i in range(30):
            time.sleep(10)
            if self.vw_429_error() is True:
                logger.warning('virt-who is terminated by 429 status')
                break
            if oneshot is True and self.vw_thread_number() == 0:
                logger.info('virt-who is terminated normally by oneshot')
                break
            if oneshot is False and self.vw_error_number() > 0:
                logger.info('virt-who is terminated due to error found')
                break
            if oneshot is False and self.vw_send_number() > 0:
                logger.info(
                    'virt-who is terminated normally after send mappings')
                break
        self.kill_pid_by_name("virt-who")
        self.kill_pid_by_name('tail')

    def vw_oneshot_check(self, cli):
        if cli and ' -o ' in cli:
            return True
        cmd1 = "grep '^\\[global\\]$' /etc/virt-who.conf"
        cmd2 = "grep '^oneshot=\\(1\\|true\\|True\\)$' /etc/virt-who.conf"
        _, output1 = self.ssh.runcmd(cmd1)
        _, output2 = self.ssh.runcmd(cmd2)
        if output1 and output2:
            return True
        else:
            return False

    def get_rhsm_log(self, q, file):
        cmd_tail = 'tail -n 0 -f /var/log/rhsm/rhsm.log'
        cmd = f'{cmd_tail} & {cmd_tail} > {file}'
        ret, output = self.ssh.runcmd(cmd)
        q.put(("rhsm_output", output))

    def vw_thread_number(self):
        thread_num = 0
        cmd = "ps -ef | grep virt-who -i | grep -v grep |wc -l"
        ret, output = self.ssh.runcmd(cmd)
        if output is not None and output != "":
            thread_num = int(output.strip())
        return thread_num

    def vw_429_error(self):
        cmd = f'grep "status=429" {self.rhsm_log_file} |sort'
        ret, output = self.ssh.runcmd(cmd)
        if output is not None and output != "":
            return True
        else:
            return False

    def vw_error_list(self):
        error_list = list()
        cmd = f'grep "\\[.*ERROR.*\\]" {self.rhsm_log_file} |sort'
        _, output = self.ssh.runcmd(cmd)
        if output is not None and output != "":
            error_list = output.strip().split('\n')
        return error_list

    def vw_error_number(self, rhsm_log=None):
        if not rhsm_log:
            ret, rhsm_log = self.ssh.runcmd(f"cat {self.rhsm_log_file}")
        error_number = self.msg_number(rhsm_log, '\\[.*ERROR.*\\]')
        return error_number

    def vw_send_number(self, rhsm_log=None):
        if not rhsm_log:
            ret, rhsm_log = self.ssh.runcmd(f"cat {self.rhsm_log_file}")
        if "0 hypervisors and 0 guests found" in rhsm_log:
            msg = "0 hypervisors and 0 guests found"
        elif ("virtwho.main DEBUG" in rhsm_log
              or
              "rhsm.connection DEBUG" in rhsm_log):
            if "satellite" in self.register_type:
                if self.mode == "local":
                    msg = r'Response: status=200, ' \
                          r'request="PUT /rhsm/consumers'
                else:
                    msg = r'Response: status=200, ' \
                          r'request="POST /rhsm/hypervisors'
            if "stage" in self.register_type:
                if self.mode == "local":
                    msg = r'Response: status=20.*requestUuid.*request=' \
                          r'"PUT /subscription/consumers'
                else:
                    msg = r'Response: status=20.*requestUuid.*request=' \
                          r'"POST /subscription/hypervisors'
        else:
            if self.mode == "local":
                msg = r"Sending update in guests lists for config"
            else:
                msg = r"Sending updated Host-to-guest mapping to"
        res = re.findall(msg, rhsm_log, re.I)
        return len(res)

    def vw_report_id(self, rhsm_log):
        res = re.findall(r"reporter_id='(.*?)'", rhsm_log)
        if len(res) > 0:
            reporter_id = res[0].strip()
            return reporter_id

    def vw_interval_time(self, rhsm_log):
        res = re.findall(
            r"Starting infinite loop with(.*?)seconds interval",
            rhsm_log)
        if len(res) > 0:
            interval_time = res[0].strip()
            return int(interval_time)

    def vw_loop_number(self):
        key = ""
        loop_num = 0
        cmd = f'''grep 'Report for config' {self.rhsm_log_file} |
                 grep 'placing in datastore' |
                 head -1'''
        _, output = self.ssh.runcmd(cmd)
        keys = re.findall(r'Report for config "(.*?)"', output)
        if output is not None and output != "" and len(keys) > 0:
            key = f'Report for config "{keys[0]}" gathered, placing in datastore'
            cmd = f"grep '{key}' {self.rhsm_log_file} | wc -l"
            _, output = self.ssh.runcmd(cmd)
            if output is not None or output != "":
                loop_num = int(output) - 1
        return key, loop_num

    def vw_loop_time(self):
        loop_time = -1
        key, loop_num = self.vw_loop_number()
        if loop_num != 0:
            cmd = f"grep '{key}' {self.rhsm_log_file} | head -2"
            _, output = self.ssh.runcmd(cmd)
            output = output.split('\n')
            if len(output) > 0:
                d1 = re.findall(r"\d{2}:\d{2}:\d{2}", output[0])[0]
                d2 = re.findall(r"\d{2}:\d{2}:\d{2}", output[1])[0]
                h, m, s = d1.strip().split(":")
                s1 = int(h) * 3600 + int(m) * 60 + int(s)
                h, m, s = d2.strip().split(":")
                s2 = int(h) * 3600 + int(m) * 60 + int(s)
                loop_time = s2 - s1
        return loop_time

    def vw_mapping_facts(self, rhsm_log):
        if self.mode == 'local':
            data = self.vw_mapping_facts_local_mode(rhsm_log)
        else:
            data = self.vw_mapping_facts_remote_mode(rhsm_log)
        return data

    def vw_mapping_facts_local_mode(self, rhsm_log):
        data = dict()
        key = "Domain info:"
        rex = re.compile(r'(?<=Domain info: )\[.*?\]\n+(?=\d\d\d\d|$)', re.S)
        mapping_info = rex.findall(rhsm_log)[0]
        try:
            mapping_info = json.loads(mapping_info.replace('\n', ''),
                                      strict=False)
        except:
            logger.warning(f"json.loads failed: {mapping_info}")
            return data
        for item in mapping_info:
            guestId = item['guestId']
            attr = dict()
            attr['state'] = item['state']
            attr['active'] = item['attributes']['active']
            attr['type'] = item['attributes']['virtWhoType']
            data[guestId] = attr
        return data

    def vw_mapping_facts_remote_mode(self, rhsm_log):
        data = dict()
        orgs = re.findall(r"Host-to-guest mapping being sent to '(.*?)'",
                          rhsm_log)
        if len(orgs) > 0:
            data['orgs'] = orgs
            org_data = dict()
            for org in orgs:
                key = f"Host-to-guest mapping being sent to '{org}'"
                rex = re.compile(r'(?<=: ){.*?}\n+(?=202|$)', re.S)
                mapping_info = rex.findall(rhsm_log)[-1]
                try:
                    mapping_info = json.loads(mapping_info.replace('\n', ''),
                                              strict=False)
                except:
                    logger.warning("Failed to run json.loads for rhsm.log")
                    return data
                hypervisors = mapping_info['hypervisors']
                org_data["hypervisor_num"] = len(hypervisors)
                for item in hypervisors:
                    hypervisorId = item['hypervisorId']['hypervisorId']
                    if 'name' in item.keys():
                        hypervisor_name = item['name']
                    else:
                        hypervisor_name = ""
                    facts = dict()
                    facts['name'] = hypervisor_name
                    facts['type'] = item['facts']['hypervisor.type']
                    facts['version'] = item['facts']['hypervisor.version']
                    facts['socket'] = item['facts']['cpu.cpu_socket(s)']
                    facts['dmi'] = item['facts']['dmi.system.uuid']
                    if 'hypervisor.cluster' in item['facts'].keys():
                        facts['cluster'] = item['facts']['hypervisor.cluster']
                    else:
                        facts['cluster'] = ''
                    guests = list()
                    for guest in item['guestIds']:
                        guestId = guest['guestId']
                        guests.append(guestId)
                        attr = dict()
                        attr['guest_hypervisor'] = hypervisorId
                        attr['state'] = guest['state']
                        attr['active'] = guest['attributes']['active']
                        attr['type'] = guest['attributes']['virtWhoType']
                        org_data[guestId] = attr
                    facts['guests'] = guests
                    org_data[hypervisorId] = facts
                data[org] = org_data
        return data

    def run_service(self, name='virt-who', action='restart'):
        cmd = f'systemctl {action} {name}'
        ret, output = self.ssh.runcmd(cmd)
        time.sleep(10)
        return ret, output

    def kill_pid_by_name(self, process_name):
        cmd = '''ps -ef |
                grep %s -i |
                grep -v grep |
                awk '{print $2}' |
                xargs -I {} kill -9 {}''' % process_name
        _, _ = self.ssh.runcmd(cmd)
        cmd = f"rm -f /var/run/{process_name}.pid"
        _, _ = self.ssh.runcmd(cmd)
        cmd = f"ps -ef | grep {process_name} -i | grep -v grep |sort"
        ret, output = self.ssh.runcmd(cmd)
        if output.strip() == "" or output.strip() is None:
            return True
        else:
            return False

    def msg_search(self, output, msgs):
        """
        Check if the key messages exist or not in output.
        :param output: messages to search around
        :param msgs: key messages to be searched.
            msgs could be a string or a list.
            If '|' in string, it means 'or' for the left and right.
        :return: Ture or False
        """
        if type(msgs) is str:
            msgs = [msgs]
        search_list = list()
        for msg in msgs:
            if_find = "No"
            if "|" in msg:
                keys = msg.split("|")
                for key in keys:
                    if self.msg_number(output, key) > 0:
                        if_find = "Yes"
            else:
                if self.msg_number(output, msg) > 0:
                    if_find = "Yes"
            if if_find == "Yes":
                logger.info(f"Found msg: {msg}")
            else:
                logger.info(f"Haven't found msg: {msg}")
            search_list.append(if_find)
        if "No" in search_list:
            return False
        else:
            return True

    def msg_number(self, output, msg):
        """
        Get message numbers.
        :param output: output to search around
        :param msg: message string to be searched
        :return: the message number
        """
        num = len(re.findall(msg, output, re.I))
        logger.info(f"Find '{msg}' {num} times")
        return num
