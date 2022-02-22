"""NIC.RU does not provide a sandbox or demo accounts for API testing,
so this test only shows possibility to initialize DnsApi.
"""

import os
from tempfile import mkdtemp
from shutil import rmtree

from nic_api import DnsApi
from nic_api.exceptions import DnsApiException


def test_oauthfail():
    fake_config_data = {"APP_LOGIN": "invalid", "APP_PASSWORD": "invalid"}
    tmpdir = mkdtemp()
    try:
        fake_token_storage = os.path.join(tmpdir, "token.json")
        api = DnsApi(fake_config_data)
        try:
            api.authorize("dummy", "dummy", fake_token_storage)
        except Exception as err:
            assert isinstance(err, DnsApiException)
            assert str(err) == '{"error":"invalid_client"}'
    finally:
        rmtree(tmpdir)
