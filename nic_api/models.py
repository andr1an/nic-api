"""nic_api - classes for entities returned by API."""

from xml.etree import ElementTree

from nic_api.compat import XML_ENCODING


def _strtobool(string):
    """Converts a string from NIC API response to a bool."""
    return {"true": True, "false": False}[string]


def parse_record(rr):
    """Parses record XML representation to one of DNSRecord subclasses.

    Reads <rr> tag, gets record type and passes <rr> internals to the specific
    DNS record model.

    Arguments:
        rr: an instance if ElementTree.Element: <rr> tag from API response;

    Returns:
        one of SOARecord, NSRecord, ARecord, AAAARecord, CNAMERecord, MXRecord,
        TXTRecord.
    """
    # TODO: move this to the DNSRecord class as "from_xml"
    if not isinstance(rr, ElementTree.Element):
        raise TypeError('"rr" must be an instance of ElementTree.Element')

    record_classes = {
        "SOA": SOARecord,
        "NS": NSRecord,
        "A": ARecord,
        "AAAA": AAAARecord,
        "CNAME": CNAMERecord,
        "MX": MXRecord,
        "TXT": TXTRecord,
        "SRV": SRVRecord,
    }

    record_type = rr.find("type").text

    if record_type not in record_classes:
        raise TypeError("Unknown record type: {}".format(record_type))

    return record_classes[record_type].from_xml(rr)


# *****************************************************************************
# Model of service
#


class NICService(object):
    """Model of service object."""

    def __init__(
        self,
        admin,
        domains_limit,
        domains_num,
        enable,
        has_primary,
        name,
        payer,
        tariff,
        rr_limit=None,
        rr_num=None,
    ):
        self.admin = admin
        self.domains_limit = int(domains_limit)
        self.domains_num = int(domains_num)
        self.enable = enable
        self.has_primary = has_primary
        self.name = name
        self.payer = payer
        if rr_limit is not None:
            self.rr_limit = int(rr_limit)
        if rr_num is not None:
            self.rr_num = int(rr_num)
        self.tariff = tariff

    def __repr__(self):
        return repr(vars(self))

    @classmethod
    def from_xml(cls, service):
        """Alternative constructor - creates an instance of NICService from
        its XML representation.
        """
        if not isinstance(service, ElementTree.Element):
            raise TypeError(
                '"service" must be an instance of ElementTree.Element'
            )

        kwargs = {k.replace("-", "_"): v for k, v in service.attrib.items()}
        kwargs["enable"] = _strtobool(kwargs["enable"])
        kwargs["has_primary"] = _strtobool(kwargs["has_primary"])
        return cls(**kwargs)


# *****************************************************************************
# Model of DNS zone
#


class NICZone(object):
    """Model of zone object."""

    def __init__(
        self,
        admin,
        enable,
        has_changes,
        has_primary,
        id_,
        idn_name,
        name,
        payer,
        service,
    ):
        self.admin = admin
        self.enable = enable
        self.has_changes = has_changes
        self.has_primary = has_primary
        self.id = int(id_)
        self.idn_name = idn_name
        self.name = name
        self.payer = payer
        self.service = service

    def __repr__(self):
        return repr(vars(self))

    def to_xml(self):
        # TODO: add implementation if needed
        raise NotImplementedError("Not implemented!")

    @classmethod
    def from_xml(cls, zone):
        """Alternative constructor - creates an instance of NICZone from
        its XML representation.
        """
        if not isinstance(zone, ElementTree.Element):
            raise TypeError('"zone" must be an instance of ElementTree.Element')

        kwargs = {k.replace("-", "_"): v for k, v in zone.attrib.items()}

        kwargs["id_"] = kwargs["id"]
        kwargs.pop("id")

        kwargs["enable"] = _strtobool(kwargs["enable"])
        kwargs["has_changes"] = _strtobool(kwargs["has_changes"])
        kwargs["has_primary"] = _strtobool(kwargs["has_primary"])
        return cls(**kwargs)


# *****************************************************************************
# Models of DNS records
#
# Each model has __init__() method that loads data into object by direct
# assigning and a class method from_xml() that constructs the object from
# an ElementTree.Element.
#
# Each model has to_xml() method that returns (str) an XML representation
# of the current record.
#


class DNSRecord(object):
    """Base model of NIC.RU DNS record."""

    def __init__(self, id_=None, name="", idn_name=None):
        if id_ is None:
            self.id = id_
        else:
            self.id = int(id_)
        if self.id == 0:
            raise ValueError("Invalid record ID!")
        self.name = name
        self.idn_name = idn_name if idn_name else name

    def __repr__(self):
        return repr(vars(self))


class SOARecord(DNSRecord):
    """Model of SOA record."""

    def __init__(
        self, serial, refresh, retry, expire, minimum, mname, rname, **kwargs
    ):
        super(SOARecord, self).__init__(**kwargs)
        self.serial = int(serial)
        self.refresh = int(refresh)
        self.retry = int(retry)
        self.expire = int(expire)
        self.minimum = int(minimum)
        self.mname = DNSRecord(**mname)
        self.rname = DNSRecord(**rname)

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = ElementTree.Element("rr")
        if self.id:
            root.attrib["id"] = str(self.id)
        ElementTree.SubElement(root, "name").text = self.name
        ElementTree.SubElement(root, "type").text = "SOA"
        _soa = ElementTree.SubElement(root, "soa")
        _mname = ElementTree.SubElement(_soa, "mname")
        ElementTree.SubElement(_mname, "name").text = self.mname.name
        _rname = ElementTree.SubElement(_soa, "rname")
        ElementTree.SubElement(_rname, "name").text = self.rname.name
        ElementTree.SubElement(_soa, "serial").text = str(self.serial)
        ElementTree.SubElement(_soa, "refresh").text = str(self.refresh)
        ElementTree.SubElement(_soa, "retry").text = str(self.retry)
        ElementTree.SubElement(_soa, "expire").text = str(self.expire)
        ElementTree.SubElement(_soa, "minimum").text = str(self.minimum)
        return ElementTree.tostring(root, encoding=XML_ENCODING)

    @classmethod
    def from_xml(cls, rr):
        """Alternative constructor - creates an instance of SOARecord from
        its XML representation.
        """
        if not isinstance(rr, ElementTree.Element):
            raise TypeError('"rr" must be an instance of ElementTree.Element')
        if rr.find("type").text != "SOA":
            raise ValueError("Record is not a SOA record!")

        id_ = rr.attrib["id"] if "id" in rr.attrib else None
        name = rr.find("name").text
        idn_name = rr.find("idn-name").text
        soa_fields = {
            elem: rr.find("soa/" + elem).text
            for elem in ("serial", "refresh", "retry", "expire", "minimum")
        }
        soa_fields["mname"] = {
            elem.tag.replace("-", "_"): elem.text
            for elem in rr.findall("soa/mname/*")
        }
        soa_fields["rname"] = {
            elem.tag.replace("-", "_"): elem.text
            for elem in rr.findall("soa/rname/*")
        }
        return cls(id_=id_, name=name, idn_name=idn_name, **soa_fields)


class NSRecord(DNSRecord):
    """Model of NS record."""

    ttl = None

    def __init__(self, ns, ttl=None, **kwargs):
        super(NSRecord, self).__init__(**kwargs)
        if ttl is not None:
            self.ttl = int(ttl)
            if self.ttl == 0:
                raise ValueError("Invalid TTL!")
        self.ns = ns

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = ElementTree.Element("rr")
        if self.id:
            root.attrib["id"] = str(self.id)
        ElementTree.SubElement(root, "name").text = self.name
        if self.ttl is not None:
            ElementTree.SubElement(root, "ttl").text = str(self.ttl)
        ElementTree.SubElement(root, "type").text = "NS"
        _ns = ElementTree.SubElement(root, "ns")
        ElementTree.SubElement(_ns, "name").text = self.ns
        return ElementTree.tostring(root, encoding=XML_ENCODING)

    @classmethod
    def from_xml(cls, rr):
        """Alternative constructor - creates an instance of NSRecord from
        its XML representation.
        """
        if not isinstance(rr, ElementTree.Element):
            raise TypeError('"rr" must be an instance of ElementTree.Element')
        if rr.find("type").text != "NS":
            raise ValueError("Record is not a NS record!")

        id_ = rr.attrib["id"] if "id" in rr.attrib else None
        name = rr.find("name").text
        idn_name = rr.find("idn-name").text
        ns = rr.find("ns/name").text
        return cls(id_=id_, name=name, idn_name=idn_name, ns=ns)


class ARecord(DNSRecord):
    """Model of A record."""

    ttl = None

    def __init__(self, a, ttl=None, **kwargs):
        super(ARecord, self).__init__(**kwargs)
        if ttl is not None:
            self.ttl = int(ttl)
            if self.ttl == 0:
                raise ValueError("Invalid TTL!")
        self.a = a

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = ElementTree.Element("rr")
        if self.id:
            root.attrib["id"] = str(self.id)
        ElementTree.SubElement(root, "name").text = self.name
        if self.ttl is not None:
            ElementTree.SubElement(root, "ttl").text = str(self.ttl)
        ElementTree.SubElement(root, "type").text = "A"
        ElementTree.SubElement(root, "a").text = self.a
        return ElementTree.tostring(root, encoding=XML_ENCODING)

    @classmethod
    def from_xml(cls, rr):
        """Alternative constructor - creates an instance of ARecord from
        its XML representation.
        """
        if not isinstance(rr, ElementTree.Element):
            raise TypeError('"rr" must be an instance of ElementTree.Element')
        if rr.find("type").text != "A":
            raise ValueError("Record is not an A record!")

        id_ = rr.attrib["id"] if "id" in rr.attrib else None
        name = rr.find("name").text
        idn_name = rr.find("idn-name").text
        elem_ttl = rr.find("ttl")
        ttl = elem_ttl.text if elem_ttl is not None else None
        a = rr.find("a").text
        return cls(id_=id_, name=name, idn_name=idn_name, ttl=ttl, a=a)


class AAAARecord(DNSRecord):
    """Model of AAAA record."""

    ttl = None

    def __init__(self, aaaa, ttl=None, **kwargs):
        super(AAAARecord, self).__init__(**kwargs)
        if ttl is not None:
            self.ttl = int(ttl)
            if self.ttl == 0:
                raise ValueError("Invalid TTL!")
        self.aaaa = aaaa

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = ElementTree.Element("rr")
        if self.id:
            root.attrib["id"] = str(self.id)
        ElementTree.SubElement(root, "name").text = self.name
        if self.ttl is not None:
            ElementTree.SubElement(root, "ttl").text = str(self.ttl)
        ElementTree.SubElement(root, "type").text = "AAAA"
        ElementTree.SubElement(root, "aaaa").text = self.aaaa
        return ElementTree.tostring(root, encoding=XML_ENCODING)

    @classmethod
    def from_xml(cls, rr):
        """Alternative constructor - creates an instance of AAAARecord from
        its XML representation.
        """
        if not isinstance(rr, ElementTree.Element):
            raise TypeError('"rr" must be an instance of ElementTree.Element')
        if rr.find("type").text != "AAAA":
            raise ValueError("Record is not an AAAA record!")

        id_ = rr.attrib["id"] if "id" in rr.attrib else None
        name = rr.find("name").text
        idn_name = rr.find("idn-name").text
        elem_ttl = rr.find("ttl")
        ttl = elem_ttl.text if elem_ttl is not None else None
        aaaa = rr.find("aaaa").text
        return cls(id_=id_, name=name, idn_name=idn_name, ttl=ttl, aaaa=aaaa)


class CNAMERecord(DNSRecord):
    """Model of CNAME record."""

    ttl = None

    def __init__(self, cname, ttl=None, **kwargs):
        super(CNAMERecord, self).__init__(**kwargs)
        if ttl is not None:
            self.ttl = int(ttl)
            if self.ttl == 0:
                raise ValueError("Invalid TTL!")
        self.cname = cname

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = ElementTree.Element("rr")
        if self.id:
            root.attrib["id"] = str(self.id)
        _name = ElementTree.SubElement(root, "name")
        _name.text = self.name
        if self.ttl is not None:
            ElementTree.SubElement(root, "ttl").text = str(self.ttl)
        ElementTree.SubElement(root, "type").text = "CNAME"
        _cname = ElementTree.SubElement(root, "cname")
        ElementTree.SubElement(_cname, "name").text = self.cname
        return ElementTree.tostring(root, encoding=XML_ENCODING)

    @classmethod
    def from_xml(cls, rr):
        """Alternative constructor - creates an instance of CNAMERecord from
        its XML representation.
        """
        if not isinstance(rr, ElementTree.Element):
            raise TypeError('"rr" must be an instance of ElementTree.Element')
        if rr.find("type").text != "CNAME":
            raise ValueError("Record is not a CNAME record!")

        id_ = rr.attrib["id"] if "id" in rr.attrib else None
        name = rr.find("name").text
        idn_name = rr.find("idn-name").text
        elem_ttl = rr.find("ttl")
        ttl = elem_ttl.text if elem_ttl is not None else None
        cname = rr.find("cname/name").text
        return cls(id_=id_, name=name, idn_name=idn_name, ttl=ttl, cname=cname)


class MXRecord(DNSRecord):
    """Model of MX record."""

    ttl = None

    def __init__(self, preference, exchange, ttl=None, **kwargs):
        super(MXRecord, self).__init__(**kwargs)
        if ttl is not None:
            self.ttl = int(ttl)
            if self.ttl == 0:
                raise ValueError("Invalid TTL!")
        self.preference = int(preference)
        self.exchange = exchange

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = ElementTree.Element("rr")
        if self.id:
            root.attrib["id"] = str(self.id)
        _name = ElementTree.SubElement(root, "name")
        _name.text = self.name
        if self.ttl is not None:
            ElementTree.SubElement(root, "ttl").text = str(self.ttl)
        ElementTree.SubElement(root, "type").text = "MX"
        _mx = ElementTree.SubElement(root, "mx")
        ElementTree.SubElement(_mx, "preference").text = str(self.preference)
        _exchange = ElementTree.SubElement(_mx, "exchange")
        ElementTree.SubElement(_exchange, "name").text = str(self.exchange)
        return ElementTree.tostring(root, encoding=XML_ENCODING)

    @classmethod
    def from_xml(cls, rr):
        """Alternative constructor - creates an instance of MXRecord from
        its XML representation.
        """
        if not isinstance(rr, ElementTree.Element):
            raise TypeError('"rr" must be an instance of ElementTree.Element')
        if rr.find("type").text != "MX":
            raise ValueError("Record is not an MX record!")

        id_ = rr.attrib["id"] if "id" in rr.attrib else None
        name = rr.find("name").text
        idn_name = rr.find("idn-name").text
        elem_ttl = rr.find("ttl")
        ttl = elem_ttl.text if elem_ttl is not None else None
        preference = rr.find("mx/preference").text
        exchange = rr.find("mx/exchange/name").text
        return cls(
            id_=id_,
            name=name,
            idn_name=idn_name,
            ttl=ttl,
            preference=preference,
            exchange=exchange,
        )


class TXTRecord(DNSRecord):
    """Model of TXT record."""

    ttl = None

    def __init__(self, txt, ttl=None, **kwargs):
        super(TXTRecord, self).__init__(**kwargs)
        if ttl is not None:
            self.ttl = int(ttl)
            if self.ttl == 0:
                raise ValueError("Invalid TTL!")
        self.txt = txt

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = ElementTree.Element("rr")
        if self.id:
            root.attrib["id"] = str(self.id)
        _name = ElementTree.SubElement(root, "name")
        _name.text = self.name
        if self.ttl is not None:
            ElementTree.SubElement(root, "ttl").text = str(self.ttl)
        ElementTree.SubElement(root, "type").text = "TXT"
        _txt = ElementTree.SubElement(root, "txt")
        ElementTree.SubElement(_txt, "string").text = self.txt
        return ElementTree.tostring(root, encoding=XML_ENCODING)

    @classmethod
    def from_xml(cls, rr):
        """Alternative constructor - creates an instance of TXTRecord from
        its XML representation.
        """
        if not isinstance(rr, ElementTree.Element):
            raise TypeError('"rr" must be an instance of ElementTree.Element')
        if rr.find("type").text != "TXT":
            raise ValueError("Record is not a TXT record!")

        id_ = rr.attrib["id"] if "id" in rr.attrib else None
        name = rr.find("name").text
        idn_name = rr.find("idn-name").text
        elem_ttl = rr.find("ttl")
        ttl = elem_ttl.text if elem_ttl is not None else None
        txt = [string.text for string in rr.findall("txt/string")]
        if len(txt) == 1:
            txt = txt[0]
        return cls(id_=id_, name=name, idn_name=idn_name, ttl=ttl, txt=txt)


class SRVRecord(DNSRecord):
    """Model of SRV record."""

    ttl = None

    def __init__(self, priority, weight, port, target, ttl=None, **kwargs):
        super(SRVRecord, self).__init__(**kwargs)
        if ttl is not None:
            self.ttl = int(ttl)
            if self.ttl == 0:
                raise ValueError("Invalid TTL!")
        self.priority = int(priority)
        self.weight = int(weight)
        self.port = int(port)
        self.target = target

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = ElementTree.Element("rr")
        if self.id:
            root.attrib["id"] = str(self.id)
        _name = ElementTree.SubElement(root, "name")
        _name.text = self.name
        if self.ttl is not None:
            ElementTree.SubElement(root, "ttl").text = str(self.ttl)
        ElementTree.SubElement(root, "type").text = "SRV"
        _srv = ElementTree.SubElement(root, "srv")
        ElementTree.SubElement(_srv, "priority").text = str(self.priority)
        ElementTree.SubElement(_srv, "weight").text = str(self.weight)
        ElementTree.SubElement(_srv, "port").text = str(self.port)
        _target = ElementTree.SubElement(_srv, "target")
        ElementTree.SubElement(_target, "name").text = str(self.target)
        return ElementTree.tostring(root, encoding=XML_ENCODING)

    @classmethod
    def from_xml(cls, rr):
        """Alternative constructor - creates an instance of SRVRecord from
        its XML representation.
        """
        if not isinstance(rr, ElementTree.Element):
            raise TypeError('"rr" must be an instance of ElementTree.Element')
        if rr.find("type").text != "SRV":
            raise ValueError("Record is not a SRV record!")

        id_ = rr.attrib["id"] if "id" in rr.attrib else None
        name = rr.find("name").text
        idn_name = rr.find("idn-name").text
        elem_ttl = rr.find("ttl")
        ttl = elem_ttl.text if elem_ttl is not None else None
        priority = rr.find("srv/priority").text
        weight = rr.find("srv/weight").text
        port = rr.find("srv/port").text
        target = rr.find("srv/target/name").text
        return cls(
            id_=id_,
            name=name,
            idn_name=idn_name,
            ttl=ttl,
            priority=priority,
            weight=weight,
            port=port,
            target=target,
        )
