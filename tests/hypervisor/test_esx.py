
from virtwho.runner import Runner
from virtwho.configure import VirtwhoHypervisorConfig
from virtwho.configure import VirtwhoGlobalConfig
from virtwho.settings import config
from virtwho.settings import virtwho_conf
from virtwho.logger import getLogger

logger = getLogger(__name__)

esx = VirtwhoHypervisorConfig('esx', 'satellite')
globalconfig = VirtwhoGlobalConfig('esx')
runner = Runner('esx', 'satellite')


class TestEsx:

    @classmethod
    def setup_class(cls):
        globalconfig.initiate()

    def test_password(self):
        # good password
        tty_output = runner.run_virtwho_cli()
        assert runner.log_analyzer(tty_output)
        # bad password
        error = 'Cannot complete login due to an incorrect user name or password'
        esx.update('password', 'xxxx')
        tty_output = runner.run_virtwho_cli()
        assert runner.log_analyzer(tty_output,
                                   send_number=0,
                                   error_number=2,
                                   error_list=error)
        # unicode password
