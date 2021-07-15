"""NIC.RU (Ru-Center) DNS services manager."""

from __future__ import print_function
import os
import sys
import logging
import textwrap

import requests

from nic_api.oauth import OAuth2Token
from nic_api.oauth import get_token
from nic_api.models import *
from nic_api.exceptions import DnsApiException
from nic_api.exceptions import ExpiredToken


BASE_URL = 'https://api.nic.ru/dns-master'

DEFAULT_TTL = 600

_RECORD_CLASSES_CAN_ADD = (
    ARecord,
    AAAARecord,
    CNAMERecord,
    TXTRecord,
)


def is_sequence(arg):
    """Returns if argument is list/tuple/etc. or not."""
    return (not hasattr(arg, 'strip') and
            hasattr(arg, '__getitem__') or
            hasattr(arg, '__iter__'))


def pprint(record):
    """Pretty print for DNS records."""
    _format_default = '{:45} {:6} {:6} {}'
    _format_mx = '{:45} {:6} {:6} {:4} {}'
    _format_soa = textwrap.dedent("""\
                  {name:30} IN SOA {mname} {rname} (
                  {serial:>50} ; Serial
                  {refresh:>50} ; Refresh
                  {retry:>50} ; Retry
                  {expire:>50} ; Expire
                  {minimum:>50})""")

    if isinstance(record, ARecord):
        print(_format_default.format(
            record.name,
            record.ttl if record.ttl is not None else '',
            'A',
            record.a,
        ))
    elif isinstance(record, AAAARecord):
        print(_format_default.format(
            record.name,
            record.ttl if record.ttl is not None else '',
            'AAAA',
            record.aaaa,
        ))
    elif isinstance(record, CNAMERecord):
        print(_format_default.format(
            record.name, record.ttl, 'CNAME', record.cname))
    elif isinstance(record, MXRecord):
        print(_format_mx.format(
            record.name, record.ttl, 'MX', record.preference, record.exchange))
    elif isinstance(record, TXTRecord):
        print(_format_default.format(
            record.name, record.ttl, 'TXT', record.txt))
    elif isinstance(record, NSRecord):
        print(_format_default.format(record.name, ' ', 'NS', record.ns))
    elif isinstance(record, SOARecord):
        print(_format_soa.format(
            name=record.name,
            mname=record.mname.name,
            rname=record.rname.name,
            serial=record.serial,
            refresh=record.refresh,
            retry=record.retry,
            expire=record.expire,
            minimum=record.minimum
        ))
    else:
        print(record)
        print('Unknown record type: {}'.format(type(record)))


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
    datas = root.findall('data')
    if len(datas) != 1:
        raise ValueError("Can't find exact 1 <data> in response:\n{}".format(
            response.text))

    return datas[0]


class DnsApi(object):
    """Class for managing NIC.RU DNS services by API.

    Username and password are required only if it fails to authorize with
    cached token.

    Arguments:
        oauth_config: a dict with OAuth app credentials;
        default_service: a default name of NIC service to use in API calls;
        default_zone: a default DNS zone to use in API calls;
        debug: bool: enables debug logging level.


    oauth_config should contain the application login and the password.
    Example:

        {'APP_LOGIN': 'aaaaaa', 'APP_PASSWORD': 'bbbbb'}

    You can obtain these credentials at the NIC.RU application authorization
    page: https://www.nic.ru/manager/oauth.cgi?step=oauth.app_register
    """

    def __init__(self, oauth_config, default_service=None, default_zone=None,
                 debug=False):
        self._oauth_config = oauth_config
        self.default_service = default_service
        self.default_zone = default_zone
        self.__headers = None

        # Logging setup
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)

    def authorize(self, username=None, password=None, token_filename=None):
        """Gets the OAuth2 Bearer token and saves the authorization header.

        Arguments:
            username: username of your account;
            password: password of your account;
            token_filename: a path of the file to load/store cached
                OAuth token;
        """
        token_filename = token_filename or os.path.join(
            os.path.expanduser('~'), '.nic_api_token')
        token = None
        if not os.path.isfile(token_filename):
            self.logger.warning("Token cache file '%s' does not exist",
                                token_filename)
        else:
            try:
                token = OAuth2Token.from_cache(token_filename)
                self.logger.debug('Token is loaded from cache: %s', token)
            except (IOError, TypeError, ValueError) as ex_info:
                self.logger.error("Can't load token from cache!")
                self.logger.exception(ex_info)

        if not token:
            token = get_token(self._oauth_config, username, password)
        elif token.expired:
            raise ExpiredToken('Token is expired!')

        try:
            token.save_cache(token_filename)
        except IOError as err:
            self.logger.error("Can't save token to cache file!")
            self.logger.exception(err)

        self.__headers = {
            'Authorization': 'Bearer {}'.format(token.access_token)
        }

    def _get(self, url):
        """Wraps requests.get()"""
        return requests.get(BASE_URL + url, headers=self.__headers)

    def _post(self, url, data=None):
        """Wraps requests.post()"""
        return requests.post(BASE_URL + url, headers=self.__headers, data=data)

    def _put(self, url, data=None):
        """Wraps requests.put()"""
        return requests.put(BASE_URL + url, headers=self.__headers, data=data)

    def _delete(self, url):
        """Wraps requests.delete()"""
        return requests.delete(BASE_URL + url, headers=self.__headers)

    def services(self):
        """Get services available for management.

        Returns:
            a list of NICService objects.
        """
        response = self._get('/services')
        data = get_data(response)
        return [NICService.from_xml(service) for service in data]

    def zones(self, service=None):
        """Get zones in service.

        Returns:
            a list of NICZone objects.
        """
        service = self.default_service if service is None else service
        if service is None:
            response = self._get('/zones'.format(service))
        else:
            response = self._get('/services/{}/zones'.format(service))
        data = get_data(response)
        return [NICZone.from_xml(zone) for zone in data]

    def zonefile(self, service=None, zone=None):
        """Get zone file for single zone.

        Returns:
            a string with zonefile content.
        """
        service = self.default_service if service is None else service
        zone = self.default_zone if zone is None else zone
        response = self._get('/services/{}/zones/{}'.format(service, zone))
        return response.text

    def records(self, service=None, zone=None):
        """Get all records for single zone.

        Returns:
            a list with DNSRecord subclasses objects.
        """
        service = self.default_service if service is None else service
        zone = self.default_zone if zone is None else zone
        response = self._get(
            '/services/{}/zones/{}/records'.format(service, zone))
        data = get_data(response)
        _zone = data.find('zone')
        assert _zone.attrib['name'] == zone
        return [parse_record(rr) for rr in _zone.findall('rr')]

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
                raise TypeError('{} is not a valid DNS record!'.format(record))
            record_xml = record.to_xml()
            rr_list.append(record_xml)
            self.logger.debug('Prepared for addition new record on service %s'
                              ' zone %s: %s', service, zone, record_xml)

        _xml = textwrap.dedent(
            """\
            <?xml version="1.0" encoding="UTF-8" ?>
            <request><rr-list>
            {}
            </rr-list></request>"""
        ).format('\n'.join(rr_list))

        response = self._put(
            '/services/{}/zones/{}/records'.format(service, zone), data=_xml)

        self.logger.debug('Got response:\n%s', response.text)

        if response.status_code != requests.codes.ok:
            raise DnsApiException('Failed to add new records:\n{}'.format(
                response.text))

        self.logger.info('Successfully added %s records', len(rr_list))

    def delete_record(self, record_id, service=None, zone=None):
        """Deletes record by id."""
        if not isinstance(record_id, int):
            raise TypeError('"record_id" is not a valid int!')
        service = self.default_service if service is None else service
        zone = self.default_zone if zone is None else zone

        self.logger.debug('Deleting record #%s on service %s zone %s',
                          record_id, service, zone)

        response = self._delete('/services/{}/zones/{}/records/{}'.format(
            service, zone, record_id))

        if response.status_code != requests.codes.ok:
            raise DnsApiException('Failed to delete record: {}'.format(
                response.text))
        self.logger.info('Record #%s deleted!', record_id)

    def commit(self, service=None, zone=None):
        """Commits changes in zone."""
        service = self.default_service if service is None else service
        zone = self.default_zone if zone is None else zone
        response = self._post(
            '/services/{}/zones/{}/commit'.format(service, zone))
        if response.status_code != requests.codes.ok:
            raise DnsApiException('Failed to commit changes:\n{}'.format(
                response.text))
        self.logger.info('Changes committed!')

    def rollback(self, service=None, zone=None):
        """Rolls back changes in zone."""
        service = self.default_service if service is None else service
        zone = self.default_zone if zone is None else zone
        response = self._post(
            '/services/{}/zones/{}/rollback'.format(service, zone))
        if response.status_code != requests.codes.ok:
            raise DnsApiException('Failed to rollback changes:\n{}'.format(
                response.text))
        self.logger.info('Changes are rolled back!')

# vim: ts=4:sw=4:et:sta:si
