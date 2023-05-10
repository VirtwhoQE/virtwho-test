import pytest


@pytest.fixture(scope="session")
def esx_assertion():
    """
    Collect all the assertion info for esx to this fixture
    :return:
    """
    login_error = "Unable to login to ESX"
    data = {
        "type": {
            "invalid": {
                "xxx": "Unsupported virtual type 'xxx' is set",
                "红帽€467aa": "Unsupported virtual type '红帽€467aa' is set",
                "": "Unsupported virtual type '' is set",
            },
            "non_rhel9": "virt-who can't be started",
            "disable": "no connection driver available",
            "disable_multi_configs": "no connection driver available",
        },
        "server": {
            "invalid": {
                "xxx": "Name or service not known",
                "红帽€467aa": "Option server needs to be ASCII characters only",
                "": "Option server needs to be set in config",
            },
            "disable": "virt-who can't be started",
            "disable_multi_configs": 'Required option: "server" not set',
            "null_multi_configs": "Option server needs to be set in config",
        },
        "username": {
            "invalid": {
                "xxx": login_error,
                "红帽€467aa": login_error,
                "": login_error,
            },
            "disable": 'Required option: "username" not set',
            "disable_multi_configs": 'Required option: "username" not set',
            "null_multi_configs": login_error,
        },
        "password": {
            "invalid": {
                "xxx": login_error,
                "红帽€467aa": login_error,
                "": login_error,
            },
            "disable": 'Required option: "password" not set',
            "disable_multi_configs": 'Required option: "password" not set',
            "null_multi_configs": login_error,
        },
        "encrypted_password": {
            "invalid": {
                "xxx": 'Option "encrypted_password" cannot be decrypted',
                "": 'Option "encrypted_password" cannot be decrypted',
            },
            "valid_multi_configs": 'Option "encrypted_password" cannot be decrypted',
        },
        "extension_file_name": {
            "file_name": "/etc/virt-who.d/esx.conf.txt",
            "warining_msg": "Configuration directory '/etc/virt-who.d/' "
            "does not have any '*.conf' files but is not empty",
            "error_msg": "Error in libvirt backend",
        },
        "redundant_options": {
            "error_msg": "virt-who can't be started: no valid configuration found"
        },
    }

    return data


@pytest.fixture(scope="session")
def rhevm_assertion():
    """
    Collect all the assertion info for rhevm to this fixture
    :return:
    """
    login_error = "Unable to connect to RHEV-M server: 401 Client Error"
    data = {
        "type": {
            "invalid": {
                "xxx": "Unsupported virtual type 'xxx' is set",
                "红帽€467aa": "Unsupported virtual type '红帽€467aa' is set",
                "": "Unsupported virtual type '' is set",
            },
            "non_rhel9": "virt-who can't be started",
            "disable": "Cannot read CA certificate '/etc/pki/CA/cacert.pem'",
            "disable_multi_configs": "Cannot read CA certificate '/etc/pki/CA/cacert.pem'",
        },
        "server": {
            "invalid": {
                "xxx": "Name or service not known",
                "红帽€467aa": "Unable to connect to RHEV-M server",
                "": "Option server needs to be set in config",
            },
            "disable": "virt-who can't be started",
            "disable_multi_configs": 'Required option: "server" not set',
            "null_multi_configs": "Option server needs to be set in config",
        },
        "username": {
            "invalid": {
                "xxx": login_error,
                "红帽€467aa": login_error,
                "": login_error,
            },
            "disable": 'Required option: "username" not set',
            "disable_multi_configs": 'Required option: "username" not set',
            "null_multi_configs": login_error,
        },
        "password": {
            "invalid": {
                "xxx": login_error,
                "红帽€467aa": login_error,
                "": login_error,
            },
            "disable": 'Required option: "password" not set',
            "disable_multi_configs": 'Required option: "password" not set',
            "null_multi_configs": login_error,
        },
        "encrypted_password": {
            "invalid": {
                "xxx": 'Option "encrypted_password" cannot be decrypted',
                "": 'Option "encrypted_password" cannot be decrypted',
            },
            "valid_multi_configs": 'Option "encrypted_password" cannot be decrypted',
        },
    }

    return data


@pytest.fixture(scope="session")
def hyperv_assertion():
    """
    Collect all the assertion info for rhevm to this fixture
    :return:
    """
    login_error = "Incorrect domain/username/password"
    data = {
        "type": {
            "invalid": {
                "xxx": "Unsupported virtual type 'xxx' is set",
                "红帽€467aa": "Unsupported virtual type '红帽€467aa' is set",
                "": "Unsupported virtual type '' is set",
            },
            "non_rhel9": "virt-who can't be started",
            "disable": "no connection driver available for URI",
            "disable_multi_configs": "no connection driver available for URI",
        },
        "server": {
            "invalid": {
                "xxx": "Name or service not known",
                "红帽€467aa": "Unable to connect to Hyper-V server",
                "": "Option server needs to be set in config",
            },
            "disable": "virt-who can't be started",
            "disable_multi_configs": 'Required option: "server" not set',
            "null_multi_configs": "Option server needs to be set in config",
        },
        "username": {
            "invalid": {
                "xxx": login_error,
                "红帽€467aa": login_error,
                "": login_error,
            },
            "disable": 'Required option: "username" not set',
            "disable_multi_configs": 'Required option: "username" not set',
            "null_multi_configs": login_error,
        },
        "password": {
            "invalid": {
                "xxx": login_error,
                "红帽€467aa": login_error,
                "": login_error,
            },
            "disable": 'Required option: "password" not set',
            "disable_multi_configs": 'Required option: "password" not set',
            "null_multi_configs": login_error,
        },
        "encrypted_password": {
            "invalid": {
                "xxx": 'Required option: "password" not set',
                "": 'Required option: "password" not set',
            },
            "valid_multi_configs": 'Required option: "password" not set',
        },
    }

    return data


@pytest.fixture(scope="session")
def kubevirt_assertion():
    """
    Collect all the assertion info for kubevirt to this fixture
    :return:
    """
    data = {
        "type": {
            "invalid": {
                "xxx": "Unsupported virtual type 'xxx' is set",
                "红帽€467aa": "Unsupported virtual type '红帽€467aa' is set",
                "": "Unsupported virtual type '' is set",
            },
            "non_rhel9": "virt-who can't be started",
            "disable": "Failed to connect socket to '/var/run/libvirt/libvirt-sock-ro'",
            "disable_multi_configs": "Failed to connect socket to '/var/run/libvirt/libvirt-sock-ro'",
        },
    }

    return data


@pytest.fixture(scope="session")
def ahv_assertion():
    """
    Collect all the assertion info for rhevm to this fixture
    :return:
    """
    login_error = "HTTP Auth Failed get"
    data = {
        "type": {
            "invalid": {
                "xxx": "Unsupported virtual type 'xxx' is set",
                "红帽€467aa": "Unsupported virtual type '红帽€467aa' is set",
                "": "Unsupported virtual type '' is set",
            },
            "non_rhel9": "virt-who can't be started",
            "disable": "no connection driver available for URI",
            "disable_multi_configs": "no connection driver available for URI",
        },
        "server": {
            "invalid": {
                "xxx": "Invalid server IP address provided",
                "红帽€467aa": "Invalid server IP address provided",
                "": "Option server needs to be set in config",
            },
            "disable": "virt-who can't be started",
            "disable_multi_configs": 'Required option: "server" not set',
            "null_multi_configs": "Option server needs to be set in config",
        },
        "username": {
            "invalid": {
                "xxx": login_error,
                "红帽€467aa": "internal error: Unable to parse URI qemu+ssh",
                "": "",
            },
        },
        "password": {
            "invalid": {
                "xxx": "",
                "红帽€467aa": "",
                "": "",
            },
        },
        "encrypted_password": {
            "invalid": {
                "xxx": "",
                "": "",
            },
        },
    }

    return data


@pytest.fixture(scope="session")
def libvirt_assertion():
    """
    Collect all the assertion info for libvirt to this fixture
    :return:
    """
    login_error = "fails with error: Cannot recv data"
    data = {
        "type": {
            "invalid": {
                "xxx": "Unsupported virtual type 'xxx' is set",
                "红帽€467aa": "Unsupported virtual type '红帽€467aa' is set",
                "": "Unsupported virtual type '' is set",
            },
            "non_rhel9": "virt-who can't be started",
            "disable": "no connection driver available for URI",
            "disable_multi_configs": "no connection driver available for URI",
        },
        "server": {
            "invalid": {
                "xxx": "Name or service not known",
                "红帽€467aa": "internal error: Unable to parse URI qemu+ssh",
                "": "Cannot recv data: Host key verification failed.",
            },
            "disable": "Failed to connect socket to '/var/run/libvirt/libvirt-sock-ro'",
            "disable_multi_configs": "Failed to connect socket to '/var/run/libvirt/libvirt-sock-ro'",
            "null_multi_configs": "Cannot recv data: Host key verification failed.",
        },
        "username": {
            "invalid": {
                "xxx": login_error,
                "红帽€467aa": login_error,
                "": login_error,
            },
            "disable": 'Required option: "username" not set',
            "disable_multi_configs": 'Required option: "username" not set',
            "null_multi_configs": login_error,
        },
        "password": {
            "invalid": {
                "xxx": login_error,
                "红帽€467aa": login_error,
                "": login_error,
            },
            "disable": 'Required option: "password" not set',
            "disable_multi_configs": 'Required option: "password" not set',
            "null_multi_configs": login_error,
        },
        "encrypted_password": {
            "invalid": {
                "xxx": 'Required option: "password" not set',
                "": 'Required option: "password" not set',
            },
            "valid_multi_configs": 'Required option: "password" not set',
        },
    }

    return data
