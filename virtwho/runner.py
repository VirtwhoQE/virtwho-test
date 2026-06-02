import json
import re
import threading
import time
from virtwho import logger, FailException, PRINT_JSON_FILE, HYPERVISOR
from virtwho.base import msg_search
from virtwho.configure import virtwho_ssh_connect, get_hypervisor_handler


class VirtwhoRunner:
    def __init__(self, mode, register_type):
        """
        - self.config_file is used to define virt-who configuration.
        - self.print_json_file is used to store the json created by
            print function.

        :param mode: the hypervisor mode.
            (esx, hyperv, rhevm, libvirt, kubevirt, local, fake)
        :param register_type: the subscription server. (rhsm, satellite)
        """
        self.mode = mode
        self.register_type = register_type
        self.config_file = f"/etc/virt-who.d/{self.mode}.conf"
        self.rhsm_log_file = "/var/log/rhsm/rhsm.log"
        self.ssh = virtwho_ssh_connect(self.mode)

    def run_cli(
        self,
        debug=True,
        oneshot=True,
        interval=None,
        prt=False,
        config="default",
        status=False,
        jsn=False,
        wait=None,
    ):
        """
        Run virt-who by command line and analyze the result.

        :param debug: use '-d' option when set True.
        :param oneshot: use '-o' option when set True.
        :param interval: use '-i' option when configure interval time.
        :param prt: use '-p' option when set True.
        :param config: use '-c' option to define virt-who configuration
            file when define the config para.
            Default using '/etc/virt-who.d/{mode}.conf'.
        :param status: use '-s' option when set True.
        :param jsn: use '-j' option when set True, together with -s
        :param wait: wait time after run virt-who, mainly used to test
            interval function.
        :return: a dict with analyzer result.
        """
        cmd = "virt-who "
        if debug is True:
            cmd += "-d "
        if oneshot is True:
            cmd += "-o "
        if interval:
            cmd += f"-i {interval} "
        if prt:
            cmd += "-p "
        if config:
            if config == "default":
                config = f"{self.config_file}"
            cmd += f"-c {config} "
        if status:
            cmd += "-s "
        if jsn:
            cmd += "-j "
        if prt:
            cmd = f"{cmd} > {PRINT_JSON_FILE}"

        if status:
            result_data = self.status(cmd)
        else:
            result_data = self.run_start(cli=cmd, wait=wait)
        return result_data

    def run_service(self, wait=None):
        """
        Run virt-who by start service and analyze the result.

        :param wait: set wait time before stop virt-who service when
            test interval function.
        :return: a dict with analyzer result.
        """
        result_data = self.run_start(wait=wait)
        return result_data

    def analyzer(self, rhsm_log, cli=None):
        """
        Return a dict including all necessary informations for case
        asserting.
        :param rhsm_log: the output of rhsm.log
        :param cli: virt-who command line
        :return: a dict including below keys.
            debug: check if find [DEBUG] log
            oneshot: check if find the oneshot keywords
            thread: check the alive thread number of virt-who
            send: check the mappings send number
            reporter_id: get the reporter id
            interval_time: check the interval time by keywords
            loop: calculate the actual interval time
            loop_num: calculate virt-who loop number
            mappings: get the host-to-guest mappings
            print_json: get the json output after by print function
            error: check the line number of error
            error_msg: get all error lines
            warning: check the line number of warning
            warning_msg: get all warning lines
        """
        data = dict()
        data["debug"] = msg_search(rhsm_log, "\\[.*DEBUG\\]")
        data["oneshot"] = msg_search(rhsm_log, "Thread '.*' stopped after running once")
        data["terminate"] = msg_search(rhsm_log, "virt-who terminated")
        data["thread"] = self.thread_number()
        data["send"] = self.send_number(rhsm_log)
        data["reporter_id"] = self.reporter_id(rhsm_log)
        data["interval"] = self.interval_time(rhsm_log)
        data["loop"], data["loop_num"] = self.loop_info()
        data["mappings"] = self.mappings(rhsm_log)
        data["print_json"] = self.print_json(cli)
        data["error"], data["error_msg"] = self.error_warning("error")
        data["warning"], data["warning_msg"] = self.error_warning("warning")
        if HYPERVISOR != "local":
            data["hypervisor_id"] = self.hypervisor_id(data["mappings"])
        # The below line is used to local debug.
        # logger.info(f'Got the data after run virt-who:-----\n{data}\n------')
        data["log"] = rhsm_log
        return data

    def associate_in_mapping(self, result_data, org, hypervisor, guest):
        """
        Check the hypervisor is associated with guest in mapping.
        :param result_data: rhsm log data, which is analyzed.
        :param org: organization of register server
        :param guest: guest uuid
        :param hypervisor: hypervisor host name/uuid/hwuuid
        """
        mappings = result_data["mappings"]
        hypervisor_in_mappings = mappings[org][guest]["guest_hypervisor"]
        if hypervisor_in_mappings == hypervisor:
            logger.info("Host and guest is associated correctly in mapping.")
            return True
        logger.error("Host and guest is not associated in mapping.")
        return False

    def run_start(self, cli=None, wait=None):
        """
        Start/loop to run virt-who and analyze the result mainly by the
        rhsm log.
        :param cli: the command to run virt-who, such as "virt-who -d -o",
            will start virt-who by service when no cli configured.
        :param wait: wait time after run virt-who
        :return: analyzer data dict
        """
        for i in range(4):
            rhsm_output = self.thread_start(cli, wait)
            if msg_search(rhsm_output, "status=429"):
                wait_time = 60 * (i + 3)
                logger.warning(
                    f"429 code found, re-register virt-who host and try again "
                    f"after {wait_time} seconds..."
                )
                # self.re_register() need to be defined here later
                time.sleep(wait_time)
            elif msg_search(
                rhsm_output,
                "RemoteServerException: Server error "
                "attempting a GET.*returned status 500",
            ):
                logger.warning(
                    "RemoteServerException return 500 code, restart "
                    "virt-who again after 30s"
                )
                time.sleep(30)
            else:
                result_data = self.analyzer(rhsm_output, cli)
                return result_data
        raise FailException("Failed to run virt-who service.")

    def thread_start(self, cli, wait=0):
        """
        Start virt-who in a sub-thread (t1), analyze and get rhsm log in
        the main-thread, the sub-thread will be auto stopped when the
        main-thread complete.
        :param cli: the command to run virt-who, such as "virt-who -d -o",
            will start virt-who by service when no cli configured.
        :param wait: wait time after run virt-who
        :return: output of rhsm log
        """
        self.stop()
        self.log_clean()
        t1 = threading.Thread(target=self.start, args=(None, cli), daemon=True)
        t1.start()
        rhsm_ouput = self.rhsm_log_get(wait)
        return rhsm_ouput

    def start(self, _unused=None, cli=None):
        """
        Start virt-who by command line or service.
        :param cli: the command to run virt-who, such as "virt-who -d -o",
            will start virt-who by service when no cli configured.
        """
        if cli:
            logger.info(f"Start to run virt-who by cli: {cli}")
            _, output = self.ssh.runcmd(cli, log_print=False)
        else:
            logger.info("Start to run virt-who by service")
            _, output = self.operate_service()

    def stop(self):
        """Stop virt-who service and then kill the pid"""
        self.operate_service("virt-who", "stop")
        if self.kill_pid("virt-who") is False:
            raise FailException("Failed to stop and clean virt-who process")

    def status(self, cmd):
        """
        Check virt-who status by run '#virt-who -s -j'
        :param cmd: virt-who command
        :return: a dic
        """
        status_data = dict()
        _, output = self.ssh.runcmd(cmd)
        if "-j " not in cmd and "Configuration Name" in output:
            status = output.strip().split("\n")
            for item in status:
                num = status.index(item)
                if "Configuration Name" in item:
                    config_name = item.split(":")[1].strip()
                    status_data[config_name] = dict()
                    if "Source Status:" in status[num + 1]:
                        status_data[config_name]["source_status"] = (
                            status[num + 1].split(":")[1].strip()
                        )
                    if "Destination Status:" in status[num + 2]:
                        status_data[config_name]["destination_status"] = (
                            status[num + 2].split(":")[1].strip()
                        )
        if "-j " in cmd and "configurations" in output:
            output = json.loads(output.replace("\n", ""), strict=False)
            configurations = output["configurations"]
            for item in configurations:
                name = item["name"]
                status_data[name] = dict()
                if "source" in item.keys():
                    status_data[name]["source"] = item["source"]
                if "destination" in item.keys():
                    status_data[name]["destination"] = item["destination"]
        logger.info(status_data)
        return status_data

    def rhsm_log_get(self, wait=0):
        """
        Get and return rhsm log when the expected message found in log.
        :param wait: wait time before starting analyzing log
        :return: output of rhsm log
        """
        rhsm_output = ""
        if wait:
            time.sleep(wait)
        for i in range(90):
            time.sleep(5)
            _, rhsm_output = self.ssh.runcmd(f"cat {self.rhsm_log_file}")
            if msg_search(rhsm_output, "status=429") is True:
                logger.warning("429 code found when run virt-who")
                break
            if self.thread_number() == 0:
                logger.info("Virt-who is terminated after run once")
                break
            if msg_search(rhsm_output, "\\[.*ERROR.*\\]") is True:
                logger.info("Error found when run virt-who")
                break
            if self.send_number(rhsm_output) > 0:
                logger.info("Succeed to send mapping after run virt-who")
                break
            if i == 89:
                logger.info("Timeout when run virt-who")
                break
        return rhsm_output

    def log_clean(self):
        """
        Clean all log files under /var/log/rhsm/
        Clean the json file created by print function of virt-who
        """
        self.ssh.runcmd("truncate -s 0 /var/log/rhsm/*.log")
        self.ssh.runcmd("rm -f /var/log/rhsm/*.gz")

        # comment this line as we need the print json file for fake mode testing
        # self.ssh.runcmd(f"rm -rf {PRINT_JSON_FILE}")

    def error_warning(self, msg="error"):
        """
        Analyze the rhsm log to calculate the error/warning number and
        collect all lines including any trailing context (e.g. Python
        tracebacks) that follow each marker line.

        Uses ``grep -c`` for the count (only lines with the marker) and
        ``grep -A`` for the text (marker lines plus context) so that
        multiline exceptions are captured.  Existing callers that do
        ``string in result["error_msg"]`` will continue to match because
        the extra context lines are appended, never removed.

        :param msg: 'error' or 'warning'
        :return: (count_of_marker_lines, all_marker_lines_with_context)
        """
        tag = msg.upper()
        marker = f"\\[.*{tag}.*\\]"

        # Count: only lines that carry the [ERROR]/[WARNING] tag
        cmd_count = f"grep -c '{marker}' {self.rhsm_log_file}"
        _, count_out = self.ssh.runcmd(cmd_count)
        msg_number = (
            int(count_out.strip()) if count_out and count_out.strip().isdigit() else 0
        )

        # Text: include up to 20 context lines after each marker so
        # multiline Python tracebacks are captured.
        cmd_text = f"grep -A 20 '{marker}' {self.rhsm_log_file}"
        _, output = self.ssh.runcmd(cmd_text)
        if output is None:
            output = ""

        return msg_number, output

    def send_number(self, rhsm_log):
        """
        Calculate virt-who mappings report number by analyzing the rhsm
        log based on keywords.
        :param rhsm_log: the rhsm.log
        :return: virt-who report times
        """
        msg = ""
        if "0 hypervisors and 0 guests found" in rhsm_log:
            msg = "0 hypervisors and 0 guests found"
        elif "virtwho.main DEBUG" in rhsm_log or "rhsm.connection DEBUG" in rhsm_log:
            if "satellite" in self.register_type:
                prefix = "/rhsm"
            elif "rhsm" in self.register_type:
                prefix = "/subscription"
            else:
                prefix = ""
            if prefix:
                if self.mode == "local":
                    msg = (
                        r"Response: status=20.*requestUuid.*request="
                        rf'"PUT {prefix}/consumers'
                    )
                    return len(re.findall(msg, rhsm_log, re.I))
                else:
                    for pattern in [
                        rf'"PUT {prefix}/consumers',
                        rf'"POST {prefix}/hypervisors',
                    ]:
                        msg = r"Response: status=20.*requestUuid.*request=" + pattern
                        hits = re.findall(msg, rhsm_log, re.I)
                        if hits:
                            return len(hits)
        else:
            if self.mode == "local":
                msg = r"Sending update in guests lists for config"
            else:
                msg = r"Sending updated Host-to-guest mapping to"
        res = re.findall(msg, rhsm_log, re.I)
        return len(res)

    def reporter_id(self, rhsm_log):
        """
        Get the reporter id from rhsm log based on keywords.
        :param rhsm_log: the rhsm.log
        :return: reporter id
        """
        res = re.findall(r"reporter_id='(.*?)'", rhsm_log)
        if len(res) > 0:
            reporter_id = res[0].strip()
            return reporter_id

    def interval_time(self, rhsm_log):
        """
        Get the interval time from rhsm log based on keywords.
        :param rhsm_log: the rhsm.log
        :return: interval time
        """
        res = re.findall(r"Starting infinite loop with(.*?)seconds interval", rhsm_log)
        if len(res) > 0:
            interval_time = res[0].strip()
            return int(interval_time)

    def loop_info(self):
        """
        Calculate the virt-who loop times and loop interval time, which
        mainly for interval function testing.
        :return: virt-who loop number and loop interval time
        """
        loop_time = -1
        key, loop_num = self.loop_number()
        if loop_num != 0:
            cmd = f"grep '{key}' {self.rhsm_log_file} | head -2"
            _, output = self.ssh.runcmd(cmd)
            output = output.split("\n")
            if len(output) > 0:
                d1 = re.findall(r"\d{2}:\d{2}:\d{2}", output[0])[0]
                d2 = re.findall(r"\d{2}:\d{2}:\d{2}", output[1])[0]
                h, m, s = d1.strip().split(":")
                s1 = int(h) * 3600 + int(m) * 60 + int(s)
                h, m, s = d2.strip().split(":")
                s2 = int(h) * 3600 + int(m) * 60 + int(s)
                loop_time = s2 - s1
        return loop_time, loop_num

    def loop_number(self):
        """
        Analyzing rhsm log to calculate the virt-who loop number.
        :return: keywords and loop number
        """
        key = ""
        loop_num = 0
        cmd = f"""grep 'Report for config' {self.rhsm_log_file} |
                 grep 'placing in datastore' |
                 head -1"""
        _, output = self.ssh.runcmd(cmd)
        keys = re.findall(r'Report for config "(.*?)"', output)
        if output is not None and output != "" and len(keys) > 0:
            key = f'Report for config "{keys[0]}" gathered, placing in datastore'
            cmd = f"grep '{key}' {self.rhsm_log_file} | wc -l"
            _, output = self.ssh.runcmd(cmd)
            if output is not None or output != "":
                loop_num = int(output) - 1
        return key, loop_num

    def mappings(self, rhsm_log):
        """
        Get mapping facts from log.
        :param rhsm_log: the rhsm.log
        :return: dict including all mapping facts
        """
        if self.mode == "local":
            data = self.mappings_local(rhsm_log)
        else:
            data = self.mappings_remote(rhsm_log)
        return data

    def mappings_local(self, rhsm_log):
        """
        Analyzing mappings of local mode from log.
        :param rhsm_log:
        :return: dict with local mode mapping facts
        """
        data = dict()
        key = "Domain info:"
        if key in rhsm_log:
            rex = re.compile(r"(?<=Domain info: )\[.*?\]\n+(?=\d\d\d\d|$)", re.S)
            mapping_info = rex.findall(rhsm_log)[0]
            try:
                mapping_info = json.loads(mapping_info.replace("\n", ""), strict=False)
            except Exception:
                logger.warning(f"json.loads failed: {mapping_info}")
                return data
            for item in mapping_info:
                guestId = item["guestId"]
                attr = dict()
                attr["state"] = item["state"]
                attr["active"] = item["attributes"]["active"]
                attr["type"] = item["attributes"]["virtWhoType"]
                data[guestId] = attr
        return data

    def mappings_remote(self, rhsm_log):
        """
        Analyzing mappings of remote mode from log.
        :param rhsm_log:
        :return: dict with remote mode mapping facts
        """
        data = dict()
        orgs = re.findall(r"Host-to-guest mapping being sent to '(.*?)'", rhsm_log)
        if len(orgs) > 0:
            data["orgs"] = orgs
            org_data = dict()
            for org in orgs:
                # key = f"Host-to-guest mapping being sent to '{org}'"
                rex = re.compile(r"(?<=: ){.*?}\n+(?=202|$)", re.S)
                mapping_info = rex.findall(rhsm_log)[-1]
                try:
                    mapping_info = json.loads(
                        mapping_info.replace("\n", ""), strict=False
                    )
                except Exception:
                    logger.warning("Failed to run json.loads for rhsm.log")
                    return data
                hypervisors = mapping_info["hypervisors"]
                org_data["hypervisor_num"] = len(hypervisors)
                for item in hypervisors:
                    hypervisorId = item["hypervisorId"]["hypervisorId"]
                    if "name" in item.keys():
                        hypervisor_name = item["name"]
                    else:
                        hypervisor_name = ""
                    facts = dict()
                    facts["name"] = hypervisor_name
                    facts["type"] = item["facts"]["hypervisor.type"]
                    facts["version"] = str(item["facts"]["hypervisor.version"])
                    facts["socket"] = item["facts"]["cpu.cpu_socket(s)"]
                    facts["dmi"] = item["facts"]["dmi.system.uuid"]
                    if "hypervisor.cluster" in item["facts"].keys():
                        facts["cluster"] = item["facts"]["hypervisor.cluster"]
                    else:
                        facts["cluster"] = ""
                    guests = list()
                    for guest in item["guestIds"]:
                        guestId = guest["guestId"]
                        guests.append(guestId)
                        attr = dict()
                        attr["guest_hypervisor"] = hypervisorId
                        attr["state"] = guest["state"]
                        attr["active"] = guest["attributes"]["active"]
                        attr["type"] = guest["attributes"]["virtWhoType"]
                        org_data[guestId] = attr
                    facts["guests"] = guests
                    org_data[hypervisorId] = facts
                data[org] = org_data
        return data

    def hypervisor_id(self, mapping):
        """
        Get the hypervisor id by mapping
        :param mapping: the host-to-guest mapping
        """
        if mapping and self.mode and "orgs" in mapping:
            guest_uuid = get_hypervisor_handler(self.mode).guest_uuid
            for org in mapping["orgs"]:
                org_dict = mapping.get(org)
                if org_dict and guest_uuid in org_dict.keys():
                    return org_dict[guest_uuid]["guest_hypervisor"]
        return ""

    def print_json(self, cli):
        """
        Get and return the json created by print function.
        :return: json output
        """
        if cli and "-p " in cli:
            ret, output = self.ssh.runcmd(f"cat {PRINT_JSON_FILE}")
            if ret == 0 and output != "":
                return output
        return None

    def thread_number(self):
        """
        Get the alive virt-who thread number.
        :return: virt-who thread number
        """
        cmd = "pgrep -c -x virt-who"
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and output is not None:
            first_line = output.strip().splitlines()[0]
            return int(first_line)
        return 0

    def operate_service(self, name="virt-who", action="restart", wait=10):
        """
        :param name: service name, default is virt-who
        :param action: start, stop, restart, status...
        :param wait: wait time
        :return: return code and output
        """
        cmd = f"systemctl {action} {name}"
        ret, output = self.ssh.runcmd(cmd)
        time.sleep(wait)
        if action == "status":
            if "Active: active (running)" in output:
                output = "running"
            if "Active: inactive (dead)" in output or "Active: failed" in output:
                output = "dead"
        return ret, output

    def kill_pid(self, process_name):
        """
        Kill an alive process id by process name.
        :param process_name: process name
        :return: True or False
        """
        # Use pkill -x to match only the process executable name, not the
        # full command line.  The old ``ps -ef | grep <name>`` approach
        # matched SSH sessions whose env vars contained the process name
        # (e.g. TEST_RPMS=...virt-who...), killing the test runner's own
        # SSH connection and causing exit-code 255 on Testing Farm.
        self.ssh.runcmd(f"pkill -9 -x {process_name} || true")
        self.ssh.runcmd(f"rm -f /var/run/{process_name}.pid")
        ret, output = self.ssh.runcmd(f"pgrep -x {process_name}")
        if not output or not output.strip():
            return True
        else:
            return False
