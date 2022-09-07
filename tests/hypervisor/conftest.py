import pytest


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
        }

    }

    return data
