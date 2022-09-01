import pytest


@pytest.fixture(scope='session')
def esx_assertion():
    """
    Collect all the assertion info for esx to this fixture
    :return:
    """
    data = {
        'type': {
            'invalid': {
                'xxx': "Unsupported virtual type 'xxx' is set",
                '红帽€467aa': "Unsupported virtual type '红帽€467aa' is set",
                '': "Unsupported virtual type '红帽€467aa' is set",

            },
            'non_rhel9': "virt-who can't be started",
            'disable': 'Error in libvirt backend',
            'disable_multi_configs': 'Error in libvirt backend'
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
                'xxx': 'Unable to login to ESX',
                '红帽€467aa': 'Unable to login to ESX',
                '': 'Unable to login to ESX',
            },
            'disable': 'Required option: "username" not set' ,
            'disable_multi_configs': 'Required option: "username" not set',
            'null_multi_configs': 'Unable to login to ESX',
        },
        'password': {
            'invalid': {
                'xxx': 'Unable to login to ESX',
                '红帽€467aa': 'Unable to login to ESX',
                '': 'Unable to login to ESX',
            },
            'disable': 'Required option: "password" not set',
            'disable_multi_configs': 'Required option: "password" not set',
            'null_multi_configs': 'Unable to login to ESX',
        }

    }

    return data
