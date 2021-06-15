virtwho/provison
=========

`beaker.py`_ is used to install rhel host by beaker, which is mainly for satellite deploying.

* Before run the file we need to set the [beaker] section in virtwho.ini.

    * [beaker]
    * client=
    * client_username=
    * client_password=
    * default_username=
    * default_password=
    * keytab=
    * principal=

* Below is an example to run the file with required arguments.

  # python3 beaker.py --rhel-compose=RHEL-7.9-20200917.0 --variant=Server --arch=x86_64 --type=virtual


`satellite.py`_ is used to deploy satellite by cdn or dogfood resource.

1. Define the register and repo information before deploying.

    * cnd,  define the [rhsm_product] section in virtwho.ini

    * dogfood, define the [satellite]:dogfood= in virtwho.ini

2. Run the satellite.py with the required arguments.

* If you want to configure all arguments by command line, please run as below.

    # python3 satellite.py --version VERSION --repo REPO --os OS --server SERVER --ssh-username SSH_USERNAME --ssh-password SSH_PASSWORD --admin-username ADMIN_USERNAME --admin-password ADMIN_PASSWORD --manifest MANIFEST

* You can also configure arguments by define the [satellite] section in virtwho.ini.

      * [satellite]
      * username=
      * password=
      * ssh_username=
      * ssh_passowrd=
      * manifest=

    # python3 satellite.py --version VERSION --repo REPO --os OS

* Below is an example to run the file with required arguments.

  # python3 satellite.py --version=6.9 --repo=cdn --os=RHEL-7.9-20200917.0


`docker.py`_ is used to create rhel container.


`hypervisor.py`_ is used gather the hypervisor and guest information.


`kickstart.py`_ is used to install rhel host by grub.



.. _beaker.py:
    https://github.com/VirtwhoQE/virtwho-test/blob/master/virtwho/provision/beaker.py
.. _docker.py:
    https://github.com/VirtwhoQE/virtwho-test/blob/master/virtwho/provision/docker.py
.. _hypervisor.py:
    https://github.com/VirtwhoQE/virtwho-test/blob/master/virtwho/provision/hypervisor.py
.. _kickstart.py:
    https://github.com/VirtwhoQE/virtwho-test/blob/master/virtwho/provision/kickstart.py
.. _satellite.py:
    https://github.com/VirtwhoQE/virtwho-test/blob/master/virtwho/provision/satellite.py