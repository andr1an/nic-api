"""NIC.RU does not provide a sandbox or demo accounts for API testing,
so this test only shows possibility to initialize DnsApi.
"""

from nic_api import DnsApi
from nic_api.exceptions import DnsApiException


def test_oauthfail():
    api = DnsApi(app_login="invalid", app_password="invalid")
    try:
        api.get_token("dummy", "dummy")
    except Exception as err:
        assert isinstance(err, DnsApiException)
        assert str(err) == "(invalid_client) "
