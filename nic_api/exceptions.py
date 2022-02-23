"""nic_api exceptions."""


class DnsApiException(Exception):
    """Base class for NIC.RU DNS API excpeptions."""


class ExpiredToken(DnsApiException):
    """Raised when OAuth token is expired."""


class InvalidRecord(DnsApiException):
    """Raised when invalid record data was passed to the API."""
