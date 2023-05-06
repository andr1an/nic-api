# NIC.RU API Python library

This library provides interfaces for managing DNS zones and records for the DNS
service NIC.RU (Ru-Center).

## Installation

Using `pip`:

```shell
pip install nic-api
```

If you want to use this module in your project, add `nic-api` to its
dependencies.

## Usage

### Initialization

To start using the API, you should get an OAuth application login and a
password from NIC.RU. Here is the registration page:
https://www.nic.ru/manager/oauth.cgi?step=oauth.app_register

Create an instance of `nic_api.DnsApi` and provide the obtained credentials:

```python
from nic_api import DnsApi
app_login = "your_application_login"
app_password = "your_application_secret"
api = DnsApi(app_login, app_password)
```

### Authentication

Call the `DnsApi.get_token()` method with the username and the password for
your NIC.RU account:

```python
api.get_token(
    username="Your_account/NIC-D",
    password="Your_password",
)
```

Now you are ready to use the API.

Till the token is valid, you don't need to provide neither client username or
password to access the API – just create an instance of the `DnsApi` class
with the same OAuth config, and pass the cached token as `token` parameter:

```python
api = DnsApi(app_login, app_password, token)
```

If you have a valid refresh token, you can get a new access token with it:

```python
api.refresh_token(refresh_token)
```

You can add a callback method to save the token somewhere outside of the
`DnsApi` object. Use the `token_updater_clb` parameter for that.

### Viewing services and DNS zones

In the NIC.RU, DNS zones are located in “services”:

```python
api.services()
```

Usually there is only one service per account. To view available zones in the
service `MY_SERVICE` call `DnsApi.zones()`:

```python
api.zones("MY_SERVICE")
```

**Always check if there are any uncommitted changes in the zone before making
any modifications – your commit would apply all unsaved changes!**

### Getting DNS records

For viewing or modifying records, you need to specify both service and DNS
zone name:

```python
api.records("MY_SERIVCE", "example.com")
```

### Creating a record

To add a record, create an instance of one of the `nic_api.models.DNSRecord`
subclasses, i.e. `ARecord`:

```python
from nic_api.models import ARecord
record_www = ARecord(name="www", a="8.8.8.8", ttl=3600)
```

Add this record to the zone and commit the changes:

```python
api.add_record(record_www, "MY_SERVICE", "example.com")
api.commit("MY_SERVICE", "example.com")
```

### Deleting a record

Every record in the zone has an unique ID, and it's accessible via
`DNSRecord.id` property. When you got the ID, pass it to the
`DnsApi.delete_record()` method:

```python
api.delete_record(100000, "MY_SERVICE", "example.com")
api.commit("MY_SERVICE", "example.com")
```

Do not forget to commit the changes afterwards.

### Default service and zone

The `service` and `zone` parameters can be optional in all `DnsApi`
methods, if you set `default_service` and `default_zone` properties:

```python
api.default_service = "MY_SERVICE"
api.default_zone = "example.com"

api.delete_record(100000)  # service or zone are not required now
api.commit()               # the same for commit() method
```

### Internationalized domain names

For using IDNs, you need to encode parameters with Punycode before passing them
to the classes or methods, with the only exception of `idn_name` argument. In
Python 3.7+ this is done via calling `.encode("idna").decode()` methods on the
`str` object:

```python
record_idn = ARecord(a="192.168.0.1", name="тест".encode("idna").decode())
api.add_record(record_idn, "MY_SERVICE", "example.com")
api.commit("MY_SERVICE", "example.com")
```

For working with top-level IDNs, use the same approach:

```python
api.records("MY_SERIVCE", "мой-домен.рф".encode("idna").decode())

# or:
api.default_service = "MY_SERVICE"
api.default_zone = "мой-домен.рф".encode("idna").decode()
api.records()
```

## Note for Python old versions' users

Python 2.7 was EOLed on 2020-01-01, and Python 3.7 is going to be EOLed on
2023-06-27, so the 1.x.x release branch of `nic-api` is going to only support 
active Python releases. If you still need old Python version support, please
use 0.x.x releases of `nic-api`. These versions would still receive bugfixes,
but no enhancements.
