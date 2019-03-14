"""nic_api - OAuth-related methods and classes."""

import os
from time import time
import json

import requests

from nic_api.exceptions import DnsApiException
from nic_api.exceptions import EmptyCredentials


OAUTH_URL = 'https://api.nic.ru/oauth/token'


def get_token(oauth_config, username, password):
    """Returns a new OAuth token."""
    if not all([username, password]):
        raise EmptyCredentials(
            'No credentials were provided for the OAuth token request!')

    oauth_data = {
        'grant_type': 'password',
        'username': username,
        'password': password,
        'scope': r'.+:/dns-master/.+'
    }

    oauth_creds = (oauth_config['APP_LOGIN'], oauth_config['APP_PASSWORD'])

    result = requests.post(OAUTH_URL, data=oauth_data, auth=oauth_creds)

    if result.status_code != requests.codes.ok:
        raise DnsApiException(result.text)

    return OAuth2Token(**result.json())


class OAuth2Token(object):
    """Class for storing NIC.RU OAuth token.

    Arguments:
        access_token: the token for use in requests;
        token_type: type of th e token;
        expires_in: TTL for this token;
        mtime: the time of creation of this token for expiry calculation.
    """

    def __init__(self, access_token, token_type, expires_in, mtime=time()):
        self._access_token = access_token
        self._token_type = token_type
        self._expires_in = int(expires_in)
        self._mtime = mtime

    @property
    def access_token(self):
        """The token for use in request header."""
        return self._access_token

    @property
    def expired(self):
        """Returns if this token is expired or not."""
        return self._mtime + self._expires_in <= time()

    @property
    def as_dict(self):
        """Returns dict for storing token in cache, i.e. JSON."""
        return {
            'access_token': self._access_token,
            'token_type': self._token_type,
            'expires_in': str(self._expires_in),
        }

    @classmethod
    def from_cache(cls, filename):
        """Alternative constructor: loads the token from a JSON cache file."""
        mtime = os.path.getmtime(filename)
        with open(filename, 'r') as fp_cache:
            cache_data = json.load(fp_cache)
        return cls(mtime=mtime, **cache_data)

    def save_cache(self, filename):
        """"Saves the token to the JSON cache file."""
        old_umask = os.umask(0o077)
        try:
            with open(filename, 'w') as fp_cache:
                json.dump(self.as_dict, fp_cache)
        finally:
            os.umask(old_umask)
