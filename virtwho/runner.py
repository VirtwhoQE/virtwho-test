import json
import queue
import re
import threading
import time
from virtwho import logger, FailException
from virtwho.configure import virtwho_ssh_connect


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
        self.config_file = f"/etc/virt-who.d/{self.mode}.conf"
        self.rhsm_log_file = "/var/log/rhsm/rhsm.log"
        self.print_json_file = "/temp/print.json"
        self.ssh = virtwho_ssh_connect(self.mode)

    def run_virtwho_cli(self,
                        debug=True,
                        oneshot=True,
                        interval=None,
                        prt=False,
                        config="default",
                        wait=None):
        """
        Run virt-who by command line and return log.
        Use parameters to define options in command line.

        :param debug: use '-d' option when debug is True.
        :param oneshot: use '-o' option when oneshot is True.
        :param interval: use '-i' option when configure interval time.
        :param prt: use '-p' option when prt is True.
        :param config: use '-c' option to define virt-who configuration
            file when define the config para.
            Default using '/etc/virt-who.d/mode.conf'.
        :param wait: set wait time before stop virt-who service when
            test interval function.
        :return:
        """
        cmd = 'virt-who '
        if debug is True:
            cmd += '-d '
        if oneshot is True:
            cmd += '-o '
        if interval:
            cmd += f'-i {interval} '
        if prt:
            cmd += '-p '
        if config:
            if config == 'default':
                config = f'{self.config_file}'
            cmd += f'-c {config} '

        if prt:
            cmd = f'{cmd} > {self.print_json_file}'
        result_data = self.virtwho_start(cli=cmd, wait=wait)
        return result_data

    def run_virtwho_service(self, wait=None):
        """
        Run virt-who by start service and return log.

        :param wait: set wait time before stop virt-who service when
            test interval function.
        :return: tty_output and rhsm_output
        """
        result_data = self.virtwho_start(wait=wait)
        return result_data

    def result_analyzer(self, rhsm_log):
        data = dict()
        data["debug"] = self.msg_search(rhsm_log, "\\[.*DEBUG\\]")
        data["oneshot"] = self.msg_search(rhsm_log, "virt-who terminated")
        data["thread_number"] = self.virtwho_thread_number()
        data["send_number"] = self.virtwho_send_number(rhsm_log)
        data["error_number"], data["error_list"] = self.virtwho_error_status()
        data["report_id"] = self.virtwho_report_id(rhsm_log)
        data["interval_time"] = self.virtwho_interval_time(rhsm_log)
        data["loop_number"], data["loop_time"] = self.virtwho_loop_status()
        data["mappings"] = self.virtwho_mappings(rhsm_log)
        data["print_json"] = self.virtwho_print_json()
        logger.info(f"Completed the analyzer after run virt-who, "
                    f"the result is:\n"
                    f"{data}")
        return data

    def virtwho_start(self, cli=None, wait=None):
        for i in range(4):
            rhsm_output = self.virtwho_thread_start(cli, wait)
            if self.msg_search(rhsm_output, "status=429"):
                wait_time = 60 * (i + 3)
                logger.warning(
                    f"429 code found, re-register virt-who host and try again "
                    f"after {wait_time} seconds...")
                # self.re_register() need to be defined here later
                time.sleep(wait_time)
            elif self.msg_search(rhsm_output,
                                 "RemoteServerException: Server error "
                                 "attempting a GET.*returned status 500"):
                logger.warning(
                    "RemoteServerException return 500 code, restart "
                    "virt-who again after 60s")
                time.sleep(60)
            else:
                result_data = self.result_analyzer(rhsm_output)
                return result_data
        raise FailException("Failed to run virt-who service.")

    def virtwho_thread_start(self, cli, wait):
        q = queue.Queue()
        self.virtwho_stop()
        self.log_clean()
        t1 = threading.Thread(target=self.virtwho_run, args=(q, cli))
        t1.setDaemon(True)
        t1.start()
        rhsm_ouput = self.rhsm_log_get(wait)
        return rhsm_ouput

    def virtwho_run(self, q, cli):
        if cli:
            logger.info(f"Start to run virt-who by cli: {cli}")
            _, output = self.ssh.runcmd(cli)
        else:
            logger.info("Start to run virt-who by service")
            _, output = self.run_service()
        q.put("tty_output", output)

    def virtwho_stop(self):
        _, _ = self.run_service("virt-who", "stop")
        if self.kill_pid_by_name("virt-who") is False:
            raise FailException("Failed to stop and clean virt-who process")

    def rhsm_log_get(self, wait):
        rhsm_output = ""
        if wait:
            time.sleep(wait)
        for i in range(30):
            time.sleep(10)
            _, rhsm_output = self.ssh.runcmd(f"cat {self.rhsm_log_file}")
            if self.msg_search(rhsm_output, "status=429") is True:
                logger.warning("429 code found when run virt-who")
                break
            if self.msg_search(rhsm_output, "\\[.*ERROR.*\\]") is True:
                logger.info("Error found when run virt-who")
                break
            if self.virtwho_send_number(rhsm_output) > 0:
                logger.info("Succeed to send mapping after run virt-who")
                break
            if self.virtwho_thread_number() == 0:
                logger.info("Virt-who is terminated after run once")
                break
            if i == 29:
                logger.info("Timeout when run virt-who")
                break
        return rhsm_output

    def log_clean(self):
        _, _ = self.ssh.runcmd("rm -rf /var/log/rhsm/*")
        _, _ = self.ssh.runcmd(f"rm -rf {self.print_json_file}")

    def virtwho_error_status(self):
        error_number = 0
        error_list = list()
        cmd = f"grep '\\[.*ERROR.*\\]' {self.rhsm_log_file} |sort"
        _, output = self.ssh.runcmd(cmd)
        if output is not None and output != "":
            error_list = output.strip().split("\n")
            error_number = len(error_list)
        return error_number, error_list

    def virtwho_send_number(self, rhsm_log):
        msg = ""
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
            if "rhsm" in self.register_type:
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

    def virtwho_report_id(self, rhsm_log):
        res = re.findall(r"reporter_id='(.*?)'", rhsm_log)
        if len(res) > 0:
            reporter_id = res[0].strip()
            return reporter_id

    def virtwho_interval_time(self, rhsm_log):
        res = re.findall(
            r"Starting infinite loop with(.*?)seconds interval",
            rhsm_log)
        if len(res) > 0:
            interval_time = res[0].strip()
            return int(interval_time)

    def virtwho_loop_number(self):
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

    def virtwho_loop_status(self):
        loop_time = -1
        key, loop_num = self.virtwho_loop_number()
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
        return loop_num, loop_time

    def virtwho_mappings(self, rhsm_log):
        if self.mode == "local":
            data = self.virtwho_mappings_local_mode(rhsm_log)
        else:
            data = self.virtwho_mappings_remote_mode(rhsm_log)
        return data

    def virtwho_mappings_local_mode(self, rhsm_log):
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

    def virtwho_mappings_remote_mode(self, rhsm_log):
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

    def virtwho_print_json(self):
        ret, output = self.ssh.runcmd(f"cat {self.print_json_file}")
        if ret == 0 and output != "":
            return output
        else:
            return None

    def virtwho_thread_number(self):
        thread_num = 0
        cmd = "ps -ef | grep virt-who -i | grep -v grep |wc -l"
        ret, output = self.ssh.runcmd(cmd)
        if output is not None and output != "":
            thread_num = int(output.strip())
        return thread_num

    def run_service(self, name='virt-who', action='restart'):
        cmd = f"systemctl {action} {name}"
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
