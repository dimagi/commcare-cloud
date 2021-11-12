
Configuring VirtualBox for testing CommCare HQ
==============================================

Step 1: Download and Install VirtualBox
---------------------------------------

Follow the instructions for your host machine operating system found at the `VirtualBox Downloads page <https://www.virtualbox.org/wiki/Downloads>`_.

Step 2: Download, Install, and Configure Ubuntu
-----------------------------------------------


#. Download the latest `Ubuntu 18.04 Server Edition ISO <https://ubuntu.com/download/server/thank-you?version=18.04.2&architecture=amd64>`_.
#. Configure VirtualBox

   * Open VirtualBox and create a new Virtual Machine.
   * Provide the VM with at least 16GB RAM, and a 40GB Disk, as per the `minimum requirements for a monolith <../setup/new_environment.md#prerequisites>`_.
   * Once the VM is created, click Settings -> System -> Processor. Increase the number of processors to the maximum you can
   * Boot the VM and select the Ubuntu ISO you downloaded in the previous step
   * Follow the Ubuntu installation prompts, ensuring you install the OpenSSH server. The other defaults should all be left as-is unless you have specific requirements.

Step 3: Configuring VirtualBox Networking
-----------------------------------------

There are two options for configuring the VirtualBox network.

Before following these instructions it is wise to read and understand the ``NAT`` and ``Bridged`` sections of this `VirtualBox networking explained <https://technology.amis.nl/2018/07/27/virtualbox-networking-explained/>`_ article. The rest of this section assumes knoweldge of that article.

NAT
^^^

This is the easiest, but will prevent you from accessing some CommCare features like ``formplayer``.

Under the VM's network settings click "Advanced" then "Port Forwarding". Add the following rules:

.. list-table::
   :header-rows: 1

   * - Name
     - Protocol
     - Host IP
     - Host Port
     - Guest IP
     - Guest Port
   * - SSH
     - TCP
     - 127.0.0.1
     - 2222
     - 
     - 22
   * - HTTPS
     - TCP
     - 127.0.0.1
     - 8083
     - 
     - 443


With these settings:


* 
  SSH into your server with:

  .. code-block:: bash

       $ ssh username@localhost -P 2222

* Access CommCare HQ from a browser at:
  .. code-block::

       https://localhost:8083
    **Note**\ : the ``https`` part is important as redirects will not work using this method.

Bridged
^^^^^^^

In this mode, the virtual machine will get its own IP address from the router that the host is connected to. This will allow the VM to be accessed from outside of the host.

Prerequisites
~~~~~~~~~~~~~

Bridged mode requires a few things from the host:


* A wired network connection, or a wireless connection that allows bridged connections (many wireless network cards and wireless gateways do not allow this)
* Ideally, an ability to give specific MAC addresses a static IP address from the network router. Otherwise the VM's IP address might change on reboot.
* An ability to edit the host's ``host`` file (\ ``/etc/hosts`` on unix machines)

Setting up Bridged mode:
~~~~~~~~~~~~~~~~~~~~~~~~


* Under the VM's network settings, set the network adapter to be attached to the ``Bridged Adapter``. Select the network device on the host that is connected to the router (i.e. your wireless or wired card).
* For some wireless gateways which require a password, you might need to set the MAC address of the to the MAC address of the host. This may sometimes work to get a new IP address, but some wireless gateways will only give a single IP per MAC.
* If you have access to the router, set it up to give the VM's MAC address in the settings with a static IP
* Boot your VM. If the settings are correct, the machine should boot and be given an IP address. Verify what the IP address is with:
  .. code-block:: bash

     $ ip addr

* On the host, edit the ``/etc/hosts`` file:
  .. code-block:: bash

       $ sudo nano /etc/hosts
    and add the following line to the end:
  .. code-block::

       {ip address of the guest} monolith.commcarehq.test

With these settings:


* 
  SSH into your server with:

  .. code-block:: bash

       $ ssh username@{ip address of the guest}

* Access CommCare HQ from a browser at:
  .. code-block::

       https://monolith.commcarehq.test
