"""NIC.RU (Ru-Center) DNS API library."""


from typing import List
from typing import Union
from xml.etree import ElementTree
import importlib.metadata
import logging

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import (
    LegacyApplicationClient,
    InvalidGrantError,
    InvalidClientError,
)
import requests

from nic_api.exceptions import (
    DnsApiException,
    ExpiredToken,
    InvalidRecord,
    ServiceNotFound,
    ZoneNotFound,
)
from nic_api.models import (
    parse_record,
    NICService,
    NICZone,
    DNSRecord,
    SOARecord,
    NSRecord,
    ARecord,
    AAAARecord,
    CNAMERecord,
    MXRecord,
    TXTRecord,
    SRVRecord,
    PTRRecord,
    DNAMERecord,
    HINFORecord,
    NAPTRRecord,
    RPRecord,
)


__version__ = importlib.metadata.version("nic_api")

logger = logging.getLogger(__name__)


def _is_sequence(arg):
    """Returns if argument is list/tuple/etc. or not."""
    return (
        not hasattr(arg, "strip")
        and hasattr(arg, "__getitem__")
        or hasattr(arg, "__iter__")
    )


def pprint(record):
    """Pretty print for DNS records."""
    _format_default = "{:45} {:6} {:6} {}"
    _format_mx = "{:45} {:6} {:6} {:4} {}"
    _format_soa = (
        "{name:30} IN SOA {mname} {rname} (\n"
        "{serial:>50} ; Serial\n"
        "{refresh:>50} ; Refresh\n"
        "{retry:>50} ; Retry\n"
        "{expire:>50} ; Expire\n"
        "{minimum:>50} ; Minimum\n"
        "{bracket:>50}"
    )
    _format_srv = "{:45} {:6} {:6} {:6} {:6} {:6} {:45}"
    _format_hinfo = '{:45} {:6} {:6} "{}" "{}"'
    _format_naptr = '{:45} {:6} {:6} {:6} {:6} "{}" "{}" "{}" "{}"'
    _format_rp = "{:45} {:6} {:6} {} {}"

    if isinstance(record, ARecord):
        print(
            _format_default.format(
                record.name,
                record.ttl if record.ttl is not None else "",
                "A",
                record.a,
            )
        )
    elif isinstance(record, AAAARecord):
        print(
            _format_default.format(
                record.name,
                record.ttl if record.ttl is not None else "",
                "AAAA",
                record.aaaa,
            )
        )
    elif isinstance(record, CNAMERecord):
        print(
            _format_default.format(
                record.name,
                record.ttl if record.ttl is not None else "",
                "CNAME",
                record.cname,
            )
        )
    elif isinstance(record, MXRecord):
        print(
            _format_mx.format(
                record.name,
                record.ttl if record.ttl is not None else "",
                "MX",
                record.preference,
                record.exchange,
            )
        )
    elif isinstance(record, TXTRecord):
        print(
            _format_default.format(
                record.name,
                record.ttl if record.ttl is not None else "",
                "TXT",
                record.txt,
            )
        )
    elif isinstance(record, NSRecord):
        print(_format_default.format(record.name, " ", "NS", record.ns))
    elif isinstance(record, SOARecord):
        print(
            _format_soa.format(
                name=record.name,
                mname=record.mname.name,
                rname=record.rname.name,
                serial=record.serial,
                refresh=record.refresh,
                retry=record.retry,
                expire=record.expire,
                minimum=record.minimum,
                bracket=")",
            )
        )
    elif isinstance(record, SRVRecord):
        print(
            _format_srv.format(
                record.name,
                record.ttl if record.ttl is not None else "",
                "SRV",
                record.priority,
                record.weight,
                record.port,
                record.target,
            )
        )
    elif isinstance(record, PTRRecord):
        print(
            _format_default.format(
                record.name if record.name is not None else "",
                record.ttl if record.ttl is not None else "",
                "PTR",
                record.ptr,
            )
        )
    elif isinstance(record, DNAMERecord):
        print(
            _format_default.format(
                record.name,
                record.ttl if record.ttl is not None else "",
                "DNAME",
                record.dname,
            )
        )
    elif isinstance(record, HINFORecord):
        print(
            _format_hinfo.format(
                record.name,
                record.ttl if record.ttl is not None else "",
                "HINFO",
                record.hardware,
                record.os,
            )
        )
    elif isinstance(record, NAPTRRecord):
        print(
            _format_naptr.format(
                record.name,
                record.ttl if record.ttl is not None else "",
                "NAPTR",
                record.order,
                record.preference,
                record.flags,
                record.service,
                record.regexp if record.regexp is not None else "",
                record.replacement if record.replacement is not None else "",
            )
        )
    elif isinstance(record, RPRecord):
        print(
            _format_rp.format(
                record.name,
                record.ttl if record.ttl is not None else "",
                "RP",
                record.mbox,
                record.txt,
            )
        )
    else:
        print(record)
        print("Unknown record type: {}".format(type(record)))


def raise_error(raw_xml: str):
    """Tries to parse API errors and raise proper exception."""
    try:
        root = ElementTree.fromstring(raw_xml)
        errors = root.findall("errors/error")
    except ElementTree.ParseError:
        return

    if len(errors) != 1:
        return

    error_code = int(errors[0].attrib.get("code", -1))
    error_text = errors[0].text
    if error_code == 4097:
        raise ExpiredToken(error_text)
    elif error_code == 4327:
        raise InvalidRecord(error_text)
    elif error_code == 4009:
        raise ServiceNotFound(error_text)
    elif error_code == 4028:
        raise ZoneNotFound(error_text)


def get_data(response: requests.Response):
    """Gets <data> from XML response.

    Arguments:
        response: an instance of requests.Response;

    Returns:
        (xml.etree.ElementTree.Element) <data> tag of response.
    """
    if response.status_code != requests.codes.ok:
        raise_error(response.text)
        raise DnsApiException(response.text)

    root = ElementTree.fromstring(response.text)
    datas = root.findall("data")
    if len(datas) != 1:
        raise ValueError(
            "Can't find exact 1 <data> in response:\n{}".format(response.text)
        )

    return datas[0]


class DnsApi(object):
    """Class for managing NIC.RU DNS services by API.

    Username and password are required only if it fails to authorize with
    cached token.

    Arguments:
        app_login: OAuth application name;
        app_password: OAuth application password;
        token: oauthlib.oauth2.rfc6749.tokens.OAuth2Token;
        token_updater_clb: a function to call when token is updated;
        offline: lifetime of a token that app should request from OAuth;
        scope: scope for NIC.RU services that should be requested.

    You can obtain these credentials at the NIC.RU application authorization
    page: https://www.nic.ru/manager/oauth.cgi?step=oauth.app_register

    For easier calling public methods, it is possible to set up a default
    NIC.RU service and a DNS zone via `DnsApi.default_service` and
    `DnsApi.default_zone` attributes. In case of using IDNs (non-ASCII domain
    names), those attribute values should be encoded with Punycode.
    """

    base_url = "https://api.nic.ru"
    default_service = None
    default_zone = None

    def __init__(
        self,
        app_login,
        app_password,
        token=None,
        token_updater_clb=None,
        offline=3600,
        scope=".+:/dns-master/.+",
    ):
        self._app_login = app_login
        self._app_password = app_password
        self._token = token
        self._token_updater_clb = token_updater_clb
        self._offline = offline
        self._scope = scope

        # Setup session
        self._session = OAuth2Session(
            client=LegacyApplicationClient(
                client_id=self._app_login,
                scope=self._scope,
            ),
            auto_refresh_url=self.token_url,
            auto_refresh_kwargs={
                "client_id": self._app_login,
                "client_secret": self._app_password,
                "offline": self._offline,
            },
            token_updater=self._token_updater,
            token=self._token,
        )

    @property
    def token_url(self):
        return "{}/oauth/token".format(self.base_url)

    def _token_updater(self, token):
        self._token = token
        if self._token_updater_clb is not None:
            self._token_updater_clb(token)

    def get_token(self, username, password) -> None:
        """Gets authorization token."""
        try:
            token = self._session.fetch_token(
                token_url=self.token_url,
                username=username,
                password=password,
                client_id=self._app_login,
                client_secret=self._app_password,
                offline=self._offline,
            )
        except (InvalidGrantError, InvalidClientError) as err:
            raise DnsApiException(str(err))
        self._token_updater(token)

    def refresh_token(self, refresh_token) -> None:
        """Refreshes authorization token."""
        try:
            token = self._session.refresh_token(
                token_url=self.token_url,
                refresh_token=refresh_token,
                client_id=self._app_login,
                client_secret=self._app_password,
                offline=self._offline,
            )
        except (InvalidGrantError, InvalidClientError) as err:
            raise DnsApiException(str(err))
        self._token_updater(token)

    def _url_for(self, url):
        return "{}/dns-master/{}".format(self.base_url, url)

    def _get(self, url):
        """Wraps requests.get()"""
        return self._session.get(self._url_for(url))

    def _post(self, url, data=None):
        """Wraps requests.post()"""
        return self._session.post(self._url_for(url), data=data)

    def _put(self, url, data=None):
        """Wraps requests.put()"""
        return self._session.put(self._url_for(url), data=data)

    def _delete(self, url):
        """Wraps requests.delete()"""
        return self._session.delete(self._url_for(url))

    def services(self) -> List[NICService]:
        """Get services available for management.

        Returns:
            a list of NICService objects.
        """
        response = self._get("services")
        data = get_data(response)
        return [NICService.from_xml(service) for service in data]

    def zones(self, service=None) -> List[NICZone]:
        """Get zones in service.

        Returns:
            a list of NICZone objects.
        """
        service = self.default_service if service is None else service
        if service is None:
            response = self._get("zones")
        else:
            response = self._get("services/{}/zones".format(service))
        data = get_data(response)
        return [NICZone.from_xml(zone) for zone in data]

    def zonefile(self, service=None, zone=None) -> str:
        """Get zone file for single zone.

        Returns:
            a string with zonefile content.
        """
        service = self.default_service if service is None else service
        zone = self.default_zone if zone is None else zone
        response = self._get("services/{}/zones/{}".format(service, zone))
        return response.text

    def records(self, service=None, zone=None) -> List[DNSRecord]:
        """Get all records for single zone.

        Returns:
            a list with DNSRecord subclasses objects.
        """
        service = self.default_service if service is None else service
        zone = self.default_zone if zone is None else zone
        response = self._get(
            "services/{}/zones/{}/records".format(service, zone)
        )
        data = get_data(response)
        _zone = data.find("zone")
        assert _zone.attrib["name"] == zone
        return [parse_record(rr) for rr in _zone.findall("rr")]

    def add_record(
        self,
        records: Union[DNSRecord, List[DNSRecord]],
        service=None,
        zone=None,
    ) -> List[DNSRecord]:
        """Adds records.

        Returns:
            a list with DNSRecord subclasses objects (with added IDs).
        """
        service = self.default_service if service is None else service
        zone = self.default_zone if zone is None else zone
        if not _is_sequence(records):
            _records = [records]
        else:
            _records = list(records)

        rr_list = []  # for XML representations

        for record in _records:
            record_xml = record.to_xml()
            rr_list.append(record_xml)
            logger.debug(
                "Preparing to add a new record on service %s zone %s: %s",
                service,
                zone,
                record_xml,
            )

        _xml = (
            '<?xml version="1.0" encoding="UTF-8" ?>'
            "<request><rr-list>"
            "{}"
            "</rr-list></request>"
        ).format("".join(rr_list))

        response = self._put(
            "services/{}/zones/{}/records".format(service, zone), data=_xml
        )

        if response.status_code != requests.codes.ok:
            raise_error(response.text)
            raise DnsApiException(
                "Failed to add new records:\n{}".format(response.text)
            )

        logger.info("Successfully added %s records", len(rr_list))
        data = get_data(response)
        _zone = data.find("zone")
        assert _zone.attrib["name"] == zone
        return [parse_record(rr) for rr in _zone.findall("rr")]

    def delete_record(self, record_id: int, service=None, zone=None) -> None:
        """Deletes record by id."""
        service = self.default_service if service is None else service
        zone = self.default_zone if zone is None else zone

        logger.debug(
            "Deleting record #%s on service %s zone %s",
            record_id,
            service,
            zone,
        )

        response = self._delete(
            "services/{}/zones/{}/records/{}".format(service, zone, record_id)
        )

        if response.status_code != requests.codes.ok:
            raise_error(response.text)
            raise DnsApiException(
                "Failed to delete record:\n{}".format(response.text)
            )

        logger.info("Record #%s deleted", record_id)

    def commit(self, service=None, zone=None) -> None:
        """Commits changes in zone."""
        service = self.default_service if service is None else service
        zone = self.default_zone if zone is None else zone
        response = self._post(
            "services/{}/zones/{}/commit".format(service, zone)
        )
        if response.status_code != requests.codes.ok:
            raise_error(response.text)
            raise DnsApiException(
                "Failed to commit changes:\n{}".format(response.text)
            )
        logger.info("Changes committed")

    def rollback(self, service=None, zone=None) -> None:
        """Rolls back changes in zone."""
        service = self.default_service if service is None else service
        zone = self.default_zone if zone is None else zone
        response = self._post(
            "services/{}/zones/{}/rollback".format(service, zone)
        )
        if response.status_code != requests.codes.ok:
            raise_error(response.text)
            raise DnsApiException(
                "Failed to rollback changes:\n{}".format(response.text)
            )
        logger.info("Changes are rolled back")
