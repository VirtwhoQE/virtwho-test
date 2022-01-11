virtwho/provision
=========

All the provision/*.py are defined for virt-who testing.

`virtwho_host.py`_ is used to configure virt-who host for an existing server or a new one installed by beaker.

This module helps to initiate the virt-who host, install virt-who package (by cdn, UMB msg or brew), download kube.conf for cnv mode and
configure no password ssh login for remote libvirt mode.


* If need to install system by beaker, we have to set the [beaker] section in virtwho.ini.

    * [beaker]
    * client=
    * client_username=
    * client_password=
    * default_username=
    * default_password=
    * keytab=
    * principal=

* We can configure the [virtwho] section to replace some arguments

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




`virtwho_satellite.py`_ is used to create rhel container.




.. _virtwho_host.py:
    https://github.com/VirtwhoQE/virtwho-test/blob/master/virtwho/provision/virtwho_host.py
.. _virtwho_hypervisor.py:
    https://github.com/VirtwhoQE/virtwho-test/blob/master/virtwho/provision/virtwho_hypervisor.py
.. _virtwho_satellite.py:
    https://github.com/VirtwhoQE/virtwho-test/blob/master/virtwho/provision/virtwho_satellite.py

