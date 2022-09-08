import pytest

from virtwho import HYPERVISOR, FailException, logger

from virtwho.configure import virtwho_ssh_connect


@pytest.fixture(scope='session')
def esx_assertion():
    """
    Collect all the assertion info for esx to this fixture
    :return:
    """
    login_error = 'Unable to login to ESX'
    data = {
        'type': {
            'invalid': {
                'xxx': "Unsupported virtual type 'xxx' is set",
                '红帽€467aa': "Unsupported virtual type '红帽€467aa' is set",
                '': "Unsupported virtual type '' is set",
            },
            'non_rhel9': "virt-who can't be started",
            'disable': 'no connection driver available',
            'disable_multi_configs': 'no connection driver available'
        },
        'server': {
            'invalid': {
                'xxx': 'Name or service not known',
                '红帽€467aa': 'Option server needs to be ASCII characters only',
                '': 'Option server needs to be set in config',
            },
            'disable': "virt-who can't be started",
            'disable_multi_configs': 'Required option: "server" not set',
            'null_multi_configs': 'Option server needs to be set in config',
        },
        'username': {
            'invalid': {
                'xxx': login_error,
                '红帽€467aa': login_error,
                '': login_error,
            },
            'disable': 'Required option: "username" not set',
            'disable_multi_configs': 'Required option: "username" not set',
            'null_multi_configs': login_error,
        },
        'password': {
            'invalid': {
                'xxx': login_error,
                '红帽€467aa': login_error,
                '': login_error,
            },
            'disable': 'Required option: "password" not set',
            'disable_multi_configs': 'Required option: "password" not set',
            'null_multi_configs': login_error,
        },
        'encrypted_password': {
            'invalid': {
                'xxx': 'Option "encrypted_password" cannot be decrypted',
                '': 'Option "encrypted_password" cannot be decrypted',
            },
            'valid_multi_configs': 'Option "encrypted_password" cannot be decrypted'
        }

    }

    return data


def encrypted_password(password):
    cmd = f'virt-who-password -p {password} > /tmp/vw.log'
    ret, output = virtwho_ssh_connect(HYPERVISOR).runcmd(cmd)
    if ret == 0:
        ret, output = virtwho_ssh_connect(HYPERVISOR).runcmd("cat /tmp/vw.log")
        if output is not None and output != '':
            encrypted_value = output.strip()
            logger.info(f'Succeeded to get encrypted_password : {encrypted_value}')
            return encrypted_value
        else:
            raise FailException("Failed to run virt-who-password")
    else:
        raise FailException("Failed to run virt-who-password")
