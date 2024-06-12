import pytest


@pytest.fixture(scope="session")
def register_assertion():
    """
    Collect all the assertion info for rhsm to this fixture
    :return:
    """
    owner_error_wrong = [
        "owner.* is different",
        "Communication with subscription manager failed",
    ]
    owner_error_null = "system is not registered or you are not root"
    owner_error_disable = [
        "owner not in|"
        "owner.* not set|"
        "virt-who can't be started|"
        "Communication with subscription manager failed"
    ]
    rhsm_hostname_error1 = [
        "Name or service not known",
        "No address associated with hostname"
    ]
    rhsm_hostname_error2 = [
        "Server error attempting a GET to /rhsm/status/",
        "Communication with subscription manager failed",
    ]
    rhsm_port_error = ["Connection refused", "Connection timed out"]
    rhsm_prefix_error = "Communication with subscription manager failed"

    rhsm_user_pwd_error_wrong = "Communication with subscription manager failed"
    rhsm_user_pwd_error_null_disable = "system is not registered or you are not root"
    rhsm_user_pwd_error_decode = [
        "codec can't decode",
        "Communication with subscription manager failed",
    ]

    rhsm_encrypted_password_error = [
        "Communication with subscription manager failed",
        'Option "rhsm_encrypted_password" cannot be decrypted',
    ]

    data = {
        "unregister_host": "system is not registered or you are not root",
        "owner": {
            "invalid": {"xxx": owner_error_wrong, "": owner_error_null},
            "disable": owner_error_disable,
            "disable_with_another_good": owner_error_disable,
            "null_with_another_good": owner_error_null,
        },
        "rhsm_hostname": {
            "invalid": {"xxx": rhsm_hostname_error1, "": rhsm_hostname_error2},
            "disable": rhsm_hostname_error2,
        },
        "rhsm_port": {
            "invalid": {
                "123": rhsm_port_error,
            },
        },
        "rhsm_prefix": {
            "invalid": {"/xxx": rhsm_prefix_error},
            "null": rhsm_prefix_error,
            "disable": rhsm_prefix_error,
        },
        "rhsm_username": {
            "invalid": {
                "xxx": rhsm_user_pwd_error_wrong,
                "": rhsm_user_pwd_error_null_disable,
                "红帽©¥®ðπ∉": rhsm_user_pwd_error_decode,
            },
            "disable": rhsm_user_pwd_error_null_disable,
        },
        "rhsm_password": {
            "invalid": {
                "xxx": rhsm_user_pwd_error_wrong,
                "": rhsm_user_pwd_error_null_disable,
                "红帽©¥®ðπ∉": rhsm_user_pwd_error_decode,
            },
            "disable": rhsm_user_pwd_error_null_disable,
        },
        "rhsm_encrypted_password": {
            "invalid": {
                "xxx": rhsm_encrypted_password_error,
                "": rhsm_encrypted_password_error,
            },
        },
    }

    return data
