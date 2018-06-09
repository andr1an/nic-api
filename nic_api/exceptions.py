"""nic_api exceptions."""


class DnsApiException(Exception):
    """Base class for NIC.RU DNS API excpeptions."""
    pass


class EmptyCredentials(DnsApiException):
    """Raised when there's no credentials for the OAuth token request."""
    pass


class ExpiredToken(DnsApiException):
    """Raised when OAuth token is expired."""
    pass
