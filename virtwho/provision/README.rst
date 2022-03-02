virtwho/provision
=========

All the provision/*.py are defined for virt-who testing.

`virtwho_host.py`_ is used to configure virt-who host for an existing server or a new one installed by beaker.

It helps to initiate the virt-who host, install virt-who package (by cdn, UMB msg or brew url), download kube.conf for cnv mode and
configure no password ssh login for remote libvirt mode.

* If need to install system by beaker, we need to firstly set the [beaker] section in virtwho.ini.

    * [beaker]
    * client=
    * client_username=
    * client_password=
    * default_username=
    * default_password=
    * keytab=
    * principal=

* We can optionally configure the [virtwho] section to replace some arguments.

    * [virtwho]
    * server=
    * username=root
    * password=red2015
    * port=

* Below are examples to run the file with required arguments.

    * # python3 virtwho_host.py --rhel-compose=RHEL-7.9-20200917.0 --variant=Server --arch=x86_64 --type=virtual

    * # python3 virtwho_host.py --rhel-compose=RHEL-8.6.0-20220105.3 --server=10.10.10.10 --gating-msg=[JSON]

    * # python3 virtwho_host.py --rhel-compose=RHEL-9.0.0-20220105.3 --arch=x86_64 --server=10.10.10.10 --virtwho-pkg-url=[URL]



`virtwho_hypervisor.py`_




`virtwho_satellite.py`_ is used to deploy and configure satellite for virt-who testing.

It helps to install and initiate a host by beaker, install satellite pkg, deploy satellite server,
load manifest and set for virt-who testing.

* If need to install system by beaker, we should firstly set the [beaker] section in virtwho.ini.

    * [beaker]
    * client=
    * client_username=
    * client_password=
    * default_username=
    * default_password=
    * keytab=
    * principal=

* Define the register and repo information before deploying.

    * cnd,  define the [rhsm] section in virtwho.ini
    * dogfood, define the [satellite]:dogfood= in virtwho.ini


* We can optionally configure the [satellite] in virtwho.ini to replace some arguments.

    * [satellite]
    * server=
    * username=
    * password=
    * ssh_username=
    * ssh_passowrd=

* Below are examples to run the file with required arguments.

    * # python3 virtwho_satellite.py --version=6.9 --repo=cdn --rhel-compose=RHEL-7.9-20200917.0
    * # python3 virtwho_satellite.py --version=6.10 --repo=dogfood --rhel-compose=RHEL-7.9-20200917.0 --server=ent-02-vm-x.lab.eng.nay.redhat.com --ssh-username=root --ssh-password=redhat --admin-username=admin --admin-password=password





.. _virtwho_host.py:
    https://github.com/VirtwhoQE/virtwho-test/blob/master/virtwho/provision/virtwho_host.py
.. _virtwho_hypervisor.py:
    https://github.com/VirtwhoQE/virtwho-test/blob/master/virtwho/provision/virtwho_hypervisor.py
.. _virtwho_satellite.py:
    https://github.com/VirtwhoQE/virtwho-test/blob/master/virtwho/provision/virtwho_satellite.py

