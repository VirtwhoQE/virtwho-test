"""
run_virtwho_cli()
run_virtwho_service()
log_analyzer()
"""
import json
import queue
import re
import threading

from virtwho.configure import virtwho_ssh_connect
from virtwho.logger import getLogger
from multiprocessing import Process, Queue, Pool
import os, time, random, subprocess

logger = getLogger(__name__)


class Runner:

    def __init__(self, mode, register_type):
        self.mode = mode
        self.register_type = register_type
        self.ssh = virtwho_ssh_connect(mode)

    # def check_virtwho_info(self,
    #                        helps=False,
    #                        manvirtwho=False,
    #                        manvirtwhoconfig=False,
    #                        version=False):
    #     cmd = ''
    #     if helps is True:
    #         cmd = 'virt-who --help'
    #         ret, output = self.ssh.runcmd(cmd)
    #         logger.info(output)
    #         return output
    #     elif manvirtwho is True:
    #         cmd = 'man virt-who'
    #     elif version is True:
    #         cmd = 'virt-who --version'
    #     ret, output = self.ssh.runcmd(cmd)
    #     logger.info(output)
    #     return output

    def run_virtwho_cli(self,
                        normal=True,
                        debug=True,
                        oneshot=False,
                        interval=None,
                        config=None,
                        exp_loopnum=0,
                        event=None):
        cmd = 'virt-who '
        if debug is True:
            cmd += '-d '
        if oneshot is True:
            cmd += '-o '
        if interval:
            cmd += f'-i {interval} '
        if config:
            cmd += f'-c {config}'
        tty_output, rhsm_output = self.vw_start(cli=cmd,
                                            normal=normal,
                                            oneshot=oneshot,
                                            exp_loopnum=exp_loopnum,
                                            event=event)
        return tty_output, rhsm_output

    def run_virtwho_service(self,
                            normal=True,
                            oneshot=False,
                            exp_loopnum=0,
                            event=None):
        tty_output, rhsm_output = self.vw_start(normal=normal,
                                             oneshot=oneshot,
                                             exp_loopnum=exp_loopnum,
                                             event=event)
        return tty_output, rhsm_output

    def log_analyzer(self):
        # self.rhsm_log = os.path.join(TEMP_DIR, f'rhsmrandom.conf')
        data = dict()
        rhsm_output = ''
        if "virtwho.main DEBUG" in rhsm_output and \
                (
                        "Domain info:" in rhsm_output
                        or "Host-to-guest mapping being sent to" in rhsm_output
                ):
            # send_number
            data['send_num'] = self.vw_callback_send_num(rhsm_output)
            # error_number, error_list
            data['error_num'], data['error_list'] = self.vw_callback_error_num()
            # reporter_id
            res = re.findall(r"reporter_id='(.*?)'", rhsm_output)
            if len(res) > 0:
                reporter_id = res[0].strip()
                data['reporter_id'] = reporter_id
            # interval_time
            res = re.findall(
                r"Starting infinite loop with(.*?)seconds interval",
                rhsm_output)
            if len(res) > 0:
                interval_time = res[0].strip()
                data['interval_time'] = int(interval_time)
            # loop_time
            data['loop_time'] = self.vw_callback_loop_time()
            #is_async
            if "Domain info:" in rhsm_output:
                data = self.vw_local_mode_log(data, rhsm_output)
            res = re.findall(r"Server has capability '(.*?)'", rhsm_output)
            if len(res) > 0:
                is_async = res[0].strip()
                data['is_async'] = is_async
                data = self.vw_async_log(data, rhsm_output)
            else:
                data['is_async'] = "not_async"
                data = self.vw_unasync_log(data, rhsm_output)
        return data

    def vw_start(self, cli=None, normal=True, oneshot=False, exp_loopnum=None, event=None):
        for i in range(4):
            tty_output, rhsm_output = self.vw_start_thread(cli, normal, oneshot, exp_loopnum, event)
            # if data['is_429'] == "yes":
            if self.vw_callback_429_check() == 'yes':
                wait_time = 60*(i+3)
                logger.warning("429 code found, re-register virt-who host and try again after %s seconds..." % wait_time)
                # self.reregister()
                time.sleep(wait_time)
            elif len(re.findall('RemoteServerException: Server error attempting a GET.*returned status 500', rhsm_output, re.I)) > 0:
                logger.warning("RemoteServerException return 500 code, restart virt-who again after 60s")
                time.sleep(60)
            else:
                return tty_output, rhsm_output
        if self.vw_callback_429_check() == 'yes':
            raise AssertionError("Failed to due to 429 code, please check")
        else:
            logger.warning("Exception to run virt-who, please check")
            return tty_output, rhsm_output

    def vw_start_thread(
        self, cli, normal, oneshot, exp_loopnum, event):
        q = queue.Queue()
        results = list()
        threads = list()
        t1 = threading.Thread(target=self.vw_thread_clean, args=())
        threads.append(t1)
        t2 = threading.Thread(target=self.vw_thread_run, args=(t1, q, cli))
        threads.append(t2)
        t3 = threading.Thread(
            target=self.vw_thread_timeout,
            args=(t1, q, normal, oneshot, exp_loopnum, event)
        )
        threads.append(t3)
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        while not q.empty():
            results.append(q.get())
        for item in results:
            if item[0] == "tty_output":
                tty_output = item[1]
            if item[0] == "rhsm_output":
                rhsm_output = item[1]
        return tty_output, rhsm_output

    def vw_thread_run(self, t1, q, cli):
        while t1.is_alive():
            time.sleep(3)
        if cli is not None:
            logger.info("Start to run virt-who by cli: %s" % cli)
            ret, tty_output = self.ssh.runcmd(cli)
        else:
            logger.info("Start to run virt-who by service")
            ret, tty_output = self.run_service()
        q.put(("tty_output", tty_output))

    def vw_thread_timeout(self, t1, q, normal, oneshot, exp_loopnum, event):
        while t1.is_alive():
            time.sleep(5)
        if event is not None:
            time.sleep(60)
            pass
        while True:
            time.sleep(10)
            ret, output = self.ssh.runcmd("ls /var/log/rhsm/")
            if (
                ret == 0
                and output is not None
                and output != ""
                and "Unable to connect to" not in output
                and "No such file or directory" not in output
            ):
                break
        start = time.time()
        while True:
            time.sleep(10)
            end = time.time()
            spend_time = int(end-start)
            if self.vw_callback_429_check() == "yes":
                logger.info("virt-who is terminated by 429 status")
                break
            if self.vw_callback_thread_num() == 0:
                logger.info("virt-who is terminated by pid exit")
                break
            if self.vw_callback_error_num() != 0 and normal is True:
                logger.info("virt-who is terminated by error msg")
                break
            if spend_time >= 900:
                logger.info("virt-who is terminated by timeout(900s)")
                break
            # test normal and interval
            if (
                    normal is True
                    and oneshot is False
                    and self.vw_callback_loop_num() >= exp_loopnum
            ):
                logger.info(
                    "virt-who is terminated by expected_send and expected_loop"
                )
                break
            # test oneshot
            if oneshot is True and self.vw_callback_thread_num() is 0:
                logger.info('virt-who is terminalted normally with oneshot')
            # test unnormal configuration
            if normal is False and self.vw_callback_error_num() != 0:
                logger.info('virt-who is terminated with error')
                break
        self.vw_stop()
        ret, rhsm_output = self.ssh.runcmd("cat /var/log/rhsm/rhsm.log")
        q.put(("rhsm_output", rhsm_output))

    # def vw_thread_callback(self):
    #     is_429 = self.vw_callback_429_check()
    #     error_num, error_list = self.vw_callback_error_num()
    #     key, loop_num = self.vw_callback_loop_num()
    #     loop_time = self.vw_callback_loop_time()
    #     send_num = self.vw_callback_send_num()
    #     logger.info("is_429: %s, loop_num: %s, loop_time: %s, send_num: %s, error_num: %s" \
    #             % (len(pending_job), is_429, loop_num, loop_time, send_num, error_num))
    #     return pending_job, is_429, loop_num, loop_time, send_num, error_num, error_list

    # def vw_callback_pending_job(self):
    #     pending_job = list()
    #     if "stage" in self.register_type:
    #         ret, rhsm_output = self.ssh.runcmd("cat /var/log/rhsm/rhsm.log")
    #         pending_job = re.findall(r"Job (.*?) not finished", rhsm_output)
    #     return pending_job

    def vw_callback_429_check(self):
        cmd = 'grep "status=429" /var/log/rhsm/rhsm.log |sort'
        ret, output = self.ssh.runcmd(cmd)
        if output is not None and output != "":
            return "yes"
        else:
            return "no"

    def vw_callback_error_num(self):
        error_num = 0
        error_list = list()
        cmd = 'grep "\[.*ERROR.*\]" /var/log/rhsm/rhsm.log |sort'
        ret, output = self.ssh.runcmd(cmd)
        if output is not None and output != "":
            error_list = output.strip().split('\n')
            error_num = len(error_list)
        return error_num, error_list

    def vw_callback_thread_num(self):
        thread_num = 0
        cmd = "ps -ef | grep virt-who -i | grep -v grep |wc -l"
        ret, output = self.ssh.runcmd(cmd)
        if output is not None and output != "":
            thread_num = int(output.strip())
        return thread_num

    def vw_callback_loop_num(self):
        key = ""
        loop_num = 0
        cmd = "grep 'Report for config' /var/log/rhsm/rhsm.log |grep 'placing in datastore' | head -1"
        ret, output = self.ssh.runcmd(cmd)
        keys = re.findall(r'Report for config "(.*?)"', output)
        if output is not None and output != "" and len(keys) > 0:
            key = "Report for config \"%s\" gathered, placing in datastore" % keys[0]
            cmd = "grep '%s' /var/log/rhsm/rhsm.log | wc -l" % key
            ret, output = self.ssh.runcmd(cmd)
            if output is not None or output != "":
                loop_num = int(output)-1
        return key, loop_num

    def vw_callback_loop_time(self):
        loop_time = -1
        key, loop_num = self.vw_callback_loop_num()
        if loop_num != 0:
            cmd = "grep '%s' /var/log/rhsm/rhsm.log | head -2" % key
            ret, output = self.ssh.runcmd(cmd)
            output = output.split('\n')
            if len(output) > 0:
                d1 = re.findall(r"\d{2}:\d{2}:\d{2}", output[0])[0]
                d2 = re.findall(r"\d{2}:\d{2}:\d{2}", output[1])[0]
                h, m, s = d1.strip().split(":")
                s1 = int(h) * 3600 + int(m) * 60 + int(s)
                h, m, s = d2.strip().split(":")
                s2 = int(h) * 3600 + int(m) * 60 + int(s)
                loop_time = s2-s1
        return loop_time

    def vw_callback_send_num(self, rhsm_ouput=None):
        if rhsm_ouput is None:
            ret, rhsm_output = self.ssh.runcmd("cat /var/log/rhsm/rhsm.log")
        if rhsm_output is None or rhsm_output == "":
            ret1, output1 = self.ssh.runcmd(
                "ls /var/log/rhsm/virtwho/rhsm.log")
            ret2, output2 = self.ssh.runcmd(
                "ls /var/log/rhsm/virtwho/virtwho.log")
            ret3, output3 = self.ssh.runcmd(
                "ls /var/log/rhsm/virtwho.destination_*.log")
            if ret1 == 0:
                cmd = "cat {0}".format(output1)
            elif ret2 == 0:
                cmd = "cat {0}".format(output2)
            elif ret3 == 0:
                cmd = "cat {0}".format(output3)
            ret, rhsm_output = self.ssh.runcmd(cmd)
        if "0 hypervisors and 0 guests found" in rhsm_output:
            logger.info("virt-who send terminated because '0 hypervisors and 0 guests found'")
            msg = "0 hypervisors and 0 guests found"
        elif "virtwho.main DEBUG" in rhsm_output or "rhsm.connection DEBUG" in rhsm_output:
            if "satellite" in self.register_type():
                if self.mode == "local":
                    msg = r'Response: status=200, request="PUT /rhsm/consumers'
                else:
                    msg = r'Response: status=200, request="POST /rhsm/hypervisors'
            if "stage" in self.register_type():
                if self.mode == "local":
                    msg = r'Response: status=20.*requestUuid.*request="PUT /subscription/consumers'
                else:
                    msg = r'Response: status=20.*requestUuid.*request="POST /subscription/hypervisors'
        else:
            if self.mode == "local":
                msg = r"Sending update in guests lists for config"
            else:
                msg = r"Sending updated Host-to-guest mapping to"
        res = re.findall(msg, rhsm_output, re.I)
        return len(res)


    def vw_thread_clean(self):
        self.vw_stop()
        cmd = "rm -rf /var/log/rhsm/*"
        ret, output = self.ssh.runcmd(cmd)

    def vw_stop(self):
        ret, output = self.run_service("virt-who", "stop")
        assert self.kill_pid_by_name("virt-who")

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
        self.ssh.runcmd(cmd)
        cmd = "rm -f /var/run/%s.pid" % process_name
        self.ssh.runcmd(cmd)
        cmd = "ps -ef | grep %s -i | grep -v grep |sort" % process_name
        ret, output = self.ssh.runcmd(cmd)
        if output.strip() == "" or output.strip() is None:
            return True
        else:
            return False

    def vw_local_mode_log(self, data, rhsm_output):
        key = "Domain info:"
        rex = re.compile(r'(?<=Domain info: )\[.*?\]\n+(?=\d\d\d\d|$)', re.S)
        mapping_info = rex.findall(rhsm_output)[0]
        try:
            mapping_info = json.loads(mapping_info.replace('\n', ''),
                                      strict=False)
        except:
            logger.warning("json.loads failed: %s" % mapping_info)
            return data
        for item in mapping_info:
            guestId = item['guestId']
            attr = dict()
            attr['state'] = item['state']
            attr['active'] = item['attributes']['active']
            attr['type'] = item['attributes']['virtWhoType']
            data[guestId] = attr
        return data

    def vw_async_log(self, data, rhsm_output):
        orgs = re.findall(r"Host-to-guest mapping being sent to '(.*?)'",
                          rhsm_output)
        if len(orgs) > 0:
            data['orgs'] = orgs
            org_data = dict()
            for org in orgs:
                key = "Host-to-guest mapping being sent to '%s'" % org
                rex = re.compile(r'(?<=: ){.*?}\n+(?=202|$)', re.S)
                mapping_info = rex.findall(rhsm_output)[-1]
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

    def vw_unasync_log(self, data, rhsm_output):
        orgs = re.findall(r"Host-to-guest mapping being sent to '(.*?)'",
                          rhsm_output)
        if len(orgs) > 0:
            data['orgs'] = orgs
            org_data = dict()
            for org in orgs:
                key = "Host-to-guest mapping being sent to '%s'" % org
                rex = re.compile(r'(?<=: ){.*?}\n+(?=201|$)', re.S)
                mapping_info = rex.findall(rhsm_output)[-1]
                try:
                    mapping_info = json.loads(mapping_info.replace('\n', ''),
                                              strict=False)
                except:
                    logger.warning("json.loads failed: %s" % mapping_info)
                    return data
                org_data['hypervisor_num'] = len(mapping_info.keys())
                for hypervisor_id, hypervisors_data in mapping_info.items():
                    facts = dict()
                    guests = list()
                    for guest in hypervisors_data:
                        guestId = guest['guestId']
                        guests.append(guestId)
                        attr = dict()
                        attr['guest_hypervisor'] = hypervisor_id
                        attr['state'] = guest['state']
                        attr['active'] = guest['attributes']['active']
                        attr['type'] = guest['attributes']['virtWhoType']
                        org_data[guestId] = attr
                    facts['guests'] = guests
                    org_data[hypervisor_id] = facts
                data[org] = org_data
        return data