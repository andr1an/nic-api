"""NIC.RU (Ru-Center) DNS services manager."""

from __future__ import print_function
from xml.etree import ElementTree
import logging
import sys
import textwrap

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import (
    LegacyApplicationClient,
    InvalidGrantError,
    InvalidClientError,
)
import requests

from nic_api.exceptions import DnsApiException
from nic_api.models import (
    parse_record,
    NICService,
    NICZone,
    SOARecord,
    NSRecord,
    ARecord,
    AAAARecord,
    CNAMERecord,
    MXRecord,
    TXTRecord,
)


_RECORD_CLASSES_CAN_ADD = (ARecord, AAAARecord, CNAMERecord, TXTRecord)


def is_sequence(arg):
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
    _format_soa = textwrap.dedent(
        """\
                  {name:30} IN SOA {mname} {rname} (
                  {serial:>50} ; Serial
                  {refresh:>50} ; Refresh
                  {retry:>50} ; Retry
                  {expire:>50} ; Expire
                  {minimum:>50})"""
    )

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
                record.name, record.ttl, "CNAME", record.cname
            )
        )
    elif isinstance(record, MXRecord):
        print(
            _format_mx.format(
                record.name,
                record.ttl,
                "MX",
                record.preference,
                record.exchange,
            )
        )
    elif isinstance(record, TXTRecord):
        print(
            _format_default.format(record.name, record.ttl, "TXT", record.txt)
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
            )
        )
    else:
        print(record)
        print("Unknown record type: {}".format(type(record)))


def get_data(response):
    """Gets <data> from XML response.

    Arguments:
        response: an instance of requests.Response;

    Returns:
        (xml.etree.ElementTree.Element) <data> tag of response.
    """
    if not isinstance(response, requests.Response):
        raise TypeError('"response" must be an instance of requests.Response!')

    # Processing API errors
    if response.status_code != requests.codes.ok:
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
        scope: scope for NIC.RU services that should be requested;
        debug: bool: enables debug logging level.

    You can obtain these credentials at the NIC.RU application authorization
    page: https://www.nic.ru/manager/oauth.cgi?step=oauth.app_register

    For easier calling public methods, it is possible to set up a default
    NIC.RU service and a DNS zone via `DnsApi.default_service` and
    `DnsApi.default_zone` attributes.
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
        debug=False,
    ):
        self._app_login = app_login
        self._app_password = app_password
        self._token = token
        self._token_updater_clb = token_updater_clb
        self._offline = offline
        self._scope = scope

        # Logging setup
        # TODO: remove
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)

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

    def get_token(self, username, password):
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

    def services(self):
        """Get services available for management.

        Returns:
            a list of NICService objects.
        """
        response = self._get("services")
        data = get_data(response)
        return [NICService.from_xml(service) for service in data]

    def zones(self, service=None):
        """Get zones in service.

        Returns:
            a list of NICZone objects.
        """
        service = self.default_service if service is None else service
        if service is None:
            response = self._get("zones".format(service))
        else:
            response = self._get("services/{}/zones".format(service))
        data = get_data(response)
        return [NICZone.from_xml(zone) for zone in data]

    def zonefile(self, service=None, zone=None):
        """Get zone file for single zone.

        Returns:
            a string with zonefile content.
        """
        service = self.default_service if service is None else service
        zone = self.default_zone if zone is None else zone
        response = self._get("services/{}/zones/{}".format(service, zone))
        return response.text

    def records(self, service=None, zone=None):
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

    def add_record(self, records, service=None, zone=None):
        """Adds records."""
        service = self.default_service if service is None else service
        zone = self.default_zone if zone is None else zone
        if not is_sequence(records):
            _records = [records]
        else:
            _records = list(records)

        rr_list = []  # for XML representations

        for record in _records:
            if not isinstance(record, _RECORD_CLASSES_CAN_ADD):
                raise TypeError("{} is not a valid DNS record!".format(record))
            record_xml = record.to_xml()
            rr_list.append(record_xml)
            self.logger.debug(
                "Prepared for addition new record on service %s" " zone %s: %s",
                service,
                zone,
                record_xml,
            )

        _xml = textwrap.dedent(
            """\
            <?xml version="1.0" encoding="UTF-8" ?>
            <request><rr-list>
            {}
            </rr-list></request>"""
        ).format("\n".join(rr_list))

        response = self._put(
            "services/{}/zones/{}/records".format(service, zone), data=_xml
        )

        self.logger.debug("Got response:\n%s", response.text)

        if response.status_code != requests.codes.ok:
            raise DnsApiException(
                "Failed to add new records:\n{}".format(response.text)
            )

        self.logger.info("Successfully added %s records", len(rr_list))

    def delete_record(self, record_id, service=None, zone=None):
        """Deletes record by id."""
        if not isinstance(record_id, int):
            raise TypeError('"record_id" is not a valid int!')
        service = self.default_service if service is None else service
        zone = self.default_zone if zone is None else zone

        self.logger.debug(
            "Deleting record #%s on service %s zone %s",
            record_id,
            service,
            zone,
        )

        response = self._delete(
            "services/{}/zones/{}/records/{}".format(service, zone, record_id)
        )

        if response.status_code != requests.codes.ok:
            raise DnsApiException(
                "Failed to delete record: {}".format(response.text)
            )
        self.logger.info("Record #%s deleted!", record_id)

    def commit(self, service=None, zone=None):
        """Commits changes in zone."""
        service = self.default_service if service is None else service
        zone = self.default_zone if zone is None else zone
        response = self._post(
            "services/{}/zones/{}/commit".format(service, zone)
        )
        if response.status_code != requests.codes.ok:
            raise DnsApiException(
                "Failed to commit changes:\n{}".format(response.text)
            )
        self.logger.info("Changes committed!")

    def rollback(self, service=None, zone=None):
        """Rolls back changes in zone."""
        service = self.default_service if service is None else service
        zone = self.default_zone if zone is None else zone
        response = self._post(
            "services/{}/zones/{}/rollback".format(service, zone)
        )
        if response.status_code != requests.codes.ok:
            raise DnsApiException(
                "Failed to rollback changes:\n{}".format(response.text)
            )
        self.logger.info("Changes are rolled back!")
