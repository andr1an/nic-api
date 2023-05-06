"""nic_api exceptions."""


class DnsApiException(Exception):
    """Base class for NIC.RU DNS API excpeptions."""


class ExpiredToken(DnsApiException):
    """Raised when OAuth token is expired."""


class InvalidRecord(DnsApiException):
    """Raised when invalid record data was passed to the API."""


class ServiceNotFound(DnsApiException):
    """Raised when specified service was not found."""


class ZoneNotFound(DnsApiException):
    """Raised when specified DNS zone was not found on the service."""
