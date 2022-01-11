utils
=========
All the utils/*.py are defined as public tools.

`beaker.py`_ is used to install rhel host by beaker.

* Before run the file we need to set the [beaker] section in virtwho.ini.

    * [beaker]
    * client=
    * client_username=
    * client_password=
    * default_username=
    * default_password=
    * keytab=
    * principal=

* Below are examples to run the file with required arguments.

  # python3 beaker.py --rhel-compose=RHEL-7.9-20200917.0 --variant=Server --arch=x86_64 --type=virtual

  # python3 beaker.py --rhel-compose=RHEL-8.6.0-20220105.3 --arch=x86_64 --job-group=redhat

  # python3 beaker.py --rhel-compose=RHEL-9.0.0-20220105.3 --arch=x86_64 --job-group=redhat --host=%example%



`satellite.py`_ is used to deploy satellite by cdn or dogfood resource.

1. Define the register and repo information before deploying.

    * cnd,  define the [rhsm] section in virtwho.ini

    * dogfood, define the [satellite]:dogfood= in virtwho.ini

2. Run the satellite.py with the required arguments.

    * If you want to configure all arguments by command line, please run as below.

      # python3 satellite.py --version VERSION --repo REPO --rhel-compose COMPOSE_ID --server SERVER --ssh-username SSH_USERNAME --ssh-password SSH_PASSWORD --admin-username ADMIN_USERNAME --admin-password ADMIN_PASSWORD --manifest MANIFEST

    * You can also configure arguments by define the [satellite] section in virtwho.ini.

      * [satellite]
      * server=
      * username=
      * password=
      * ssh_username=
      * ssh_passowrd=
      * manifest=
      * dogfood=

      # python3 satellite.py --version VERSION --repo REPO --rhel-compose COMPOSE_ID

    * Below is an example to run the file with required arguments.

      # python3 satellite.py --version=6.9 --repo=cdn --rhel-compose=RHEL-7.9-20200917.0



`docker.py`_ is used to create rhel container.



`kickstart.py`_ is used to install rhel host by grub.



.. _beaker.py:
    https://github.com/VirtwhoQE/virtwho-test/blob/master/utils/beaker.py
.. _docker.py:
    https://github.com/VirtwhoQE/virtwho-test/blob/master/utils/docker.py
.. _kickstart.py:
    https://github.com/VirtwhoQE/virtwho-test/blob/master/utils/kickstart.py
.. _satellite.py:
    https://github.com/VirtwhoQE/virtwho-test/blob/master/utils/satellite.py
