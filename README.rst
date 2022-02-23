NIC.RU API wrapper library
==========================

The package is a wrapper for the API of Russian DNS registrar Ru-Center
(a.k.a. NIC.RU). The library provides classes for managing DNS services,
zones and records.

Installation
------------

Using ``pip``::

    pip install nic-api

If you want to use the module in your project, add this line to the project's
``requirements.txt`` file::

    nic-api

Usage
-----

Initialization
~~~~~~~~~~~~~~

To start using the API, you should get a pair of OAuth application login and
password from NIC.RU. Here is the registration page:
https://www.nic.ru/manager/oauth.cgi?step=oauth.app_register

Create an instance of ``nic_api.DnsApi`` and provide the OAuth application
credentials:

.. code:: python

    from nic_api import DnsApi
    app_login = "your_application_login"
    app_password = "your_application_secret"
    api = DnsApi(app_login, app_password)

Authorization
~~~~~~~~~~~~~

Call the ``get_token()`` method and specify the username and the password for
your NIC.RU account:

.. code:: python

    api.get_token(
        username="Your_account/NIC-D",
        password="Your_password",
    )

Now you are ready to use the API.

While the token is valid, you don't need to provide neither client username or
password to access the API – just create an instance of the ``DnsApi`` class
with the same OAuth config, and pass the cached token as ``token`` parameter:

.. code:: python

    api = DnsApi(app_login, app_password, token)

You can add a callback to cache the token with ``token_updater_clb`` parameter.

Viewing services and DNS zones
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the NIC.RU, DNS zones are located in "services":

.. code:: python

    api.services()

Usually, there is one service per account. Let's view available zones in the
service ``MY_SERVICE``:

.. code:: python

    api.zones("MY_SERVICE")

**Always check if the zone has any uncommitted changes to it before
making any modifications - your commit will apply other changes too!**

Getting DNS records
~~~~~~~~~~~~~~~~~~~

For viewing or modifying records, you need to specify both service and DNS
zone name:

.. code:: python

    api.records("MY_SERIVCE", "example.com")

Creating a record
~~~~~~~~~~~~~~~~~

To add a record, create an instance of one of the ``nic_api.models.DNSRecord``
subclasses, i.e. ``ARecord``:

.. code:: python

    from nic_api.models import ARecord
    record_www = ARecord(name="www", a="8.8.8.8", ttl=3600)

Add this record to the zone and commit the changes:

.. code:: python

    api.add_record(record_www, "MY_SERVICE", "example.com")
    api.commit("MY_SERVICE", "example.com")

Deleting a record
~~~~~~~~~~~~~~~~~

Every record in the zone has an unique ID, and it's accessible via
``DNSRecord.id`` property. When you got the ID, pass it to the
``delete_record`` method:

.. code:: python

    api.delete_record(100000, "MY_SERVICE", "example.com")
    api.commit("MY_SERVICE", "example.com")

Do not forget to always commit the changes!

Default service and zone
~~~~~~~~~~~~~~~~~~~~~~~~

The ``service`` and ``zone`` parameters can be optional in all ``DnsApi``
methods, if you set ``default_service`` and ``default_zone`` properties:

.. code:: python

    api.default_service = "MY_SERVICE"
    api.default_zone = "example.com"

    api.delete_record(100000)  # service or zone are not needed
    api.commit()               # the same for commit() method
