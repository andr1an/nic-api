"""nic_api - classes for entities returned by API."""


from xml.etree import ElementTree


def _strtobool(string):
    """Converts a string from NIC API response to a bool."""
    return {"true": True, "false": False}[string]


def parse_record(rr: ElementTree.Element):
    """Parses record XML representation to one of DNSRecord subclasses.

    Reads <rr> tag, gets record type and passes <rr> internals to the specific
    DNS record model.

    Arguments:
        rr: an instance if ElementTree.Element: <rr> tag from API response;

    Returns:
        one of SOARecord, NSRecord, ARecord, AAAARecord, CNAMERecord, MXRecord,
        TXTRecord.
    """
    record_classes = {
        "SOA": SOARecord,
        "NS": NSRecord,
        "A": ARecord,
        "AAAA": AAAARecord,
        "CNAME": CNAMERecord,
        "MX": MXRecord,
        "TXT": TXTRecord,
        "SRV": SRVRecord,
        "PTR": PTRRecord,
        "DNAME": DNAMERecord,
        "HINFO": HINFORecord,
        "NAPTR": NAPTRRecord,
        "RP": RPRecord,
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
    def from_xml(cls, service: ElementTree.Element):
        """Alternative constructor - creates an instance of NICService from
        its XML representation.
        """
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
        has_changes: bool,
        has_primary: bool,
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
        raise NotImplementedError("Not implemented")

    @classmethod
    def from_xml(cls, zone: ElementTree.Element):
        """Alternative constructor - creates an instance of NICZone from
        its XML representation.
        """
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

    ttl = None

    def __init__(self, id_=None, name="", idn_name=None):
        if id_ is None:
            self.id = id_
        else:
            self.id = int(id_)
        if self.id == 0:
            raise ValueError("Invalid record ID")
        if name is not None and not name.isascii():
            raise ValueError("Name should be an ASCII string")
        self.name = name
        if idn_name is not None:
            self.idn_name = idn_name
        elif name is not None:
            self.idn_name = name.encode().decode("idna")
        else:
            self.idn_name = name

    def __repr__(self):
        return repr(vars(self))

    @property
    def record_type(self):
        raise AttributeError("Class DNSRecord does not have a record_type")

    @property
    def as_etree(self):
        root = ElementTree.Element("rr")
        if self.id:
            root.attrib["id"] = str(self.id)
        ElementTree.SubElement(root, "name").text = self.name
        if self.ttl is not None:
            ElementTree.SubElement(root, "ttl").text = str(self.ttl)
        ElementTree.SubElement(root, "type").text = self.record_type
        return root


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

    @property
    def record_type(self):
        return "SOA"

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = self.as_etree
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
        return ElementTree.tostring(root, encoding="unicode")

    @classmethod
    def from_xml(cls, rr: ElementTree.Element):
        """Alternative constructor - creates an instance of SOARecord from
        its XML representation.
        """
        if rr.find("type").text != "SOA":
            raise ValueError("Record is not an SOA record")

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

    def __init__(self, ns, **kwargs):
        super(NSRecord, self).__init__(**kwargs)
        self.ns = ns

    @property
    def record_type(self):
        return "NS"

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = self.as_etree
        _ns = ElementTree.SubElement(root, "ns")
        ElementTree.SubElement(_ns, "name").text = self.ns
        return ElementTree.tostring(root, encoding="unicode")

    @classmethod
    def from_xml(cls, rr: ElementTree.Element):
        """Alternative constructor - creates an instance of NSRecord from
        its XML representation.
        """
        if rr.find("type").text != "NS":
            raise ValueError("Record is not an NS record")

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
                raise ValueError("Invalid TTL")
        self.a = a

    @property
    def record_type(self):
        return "A"

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = self.as_etree
        ElementTree.SubElement(root, "a").text = self.a
        return ElementTree.tostring(root, encoding="unicode")

    @classmethod
    def from_xml(cls, rr: ElementTree.Element):
        """Alternative constructor - creates an instance of ARecord from
        its XML representation.
        """
        if rr.find("type").text != "A":
            raise ValueError("Record is not an A record")

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
                raise ValueError("Invalid TTL")
        self.aaaa = aaaa

    @property
    def record_type(self):
        return "AAAA"

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = self.as_etree
        ElementTree.SubElement(root, "aaaa").text = self.aaaa
        return ElementTree.tostring(root, encoding="unicode")

    @classmethod
    def from_xml(cls, rr: ElementTree.Element):
        """Alternative constructor - creates an instance of AAAARecord from
        its XML representation.
        """
        if rr.find("type").text != "AAAA":
            raise ValueError("Record is not an AAAA record")

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
                raise ValueError("Invalid TTL")
        self.cname = cname

    @property
    def record_type(self):
        return "CNAME"

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = self.as_etree
        _cname = ElementTree.SubElement(root, "cname")
        ElementTree.SubElement(_cname, "name").text = self.cname
        return ElementTree.tostring(root, encoding="unicode")

    @classmethod
    def from_xml(cls, rr: ElementTree.Element):
        """Alternative constructor - creates an instance of CNAMERecord from
        its XML representation.
        """
        if rr.find("type").text != "CNAME":
            raise ValueError("Record is not a CNAME record")

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
                raise ValueError("Invalid TTL")
        self.preference = int(preference)
        self.exchange = exchange

    @property
    def record_type(self):
        return "MX"

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = self.as_etree
        _mx = ElementTree.SubElement(root, "mx")
        ElementTree.SubElement(_mx, "preference").text = str(self.preference)
        _exchange = ElementTree.SubElement(_mx, "exchange")
        ElementTree.SubElement(_exchange, "name").text = str(self.exchange)
        return ElementTree.tostring(root, encoding="unicode")

    @classmethod
    def from_xml(cls, rr: ElementTree.Element):
        """Alternative constructor - creates an instance of MXRecord from
        its XML representation.
        """
        if rr.find("type").text != "MX":
            raise ValueError("Record is not an MX record")

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
                raise ValueError("Invalid TTL")
        self.txt = txt

    @property
    def record_type(self):
        return "TXT"

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = self.as_etree
        _txt = ElementTree.SubElement(root, "txt")
        ElementTree.SubElement(_txt, "string").text = self.txt
        return ElementTree.tostring(root, encoding="unicode")

    @classmethod
    def from_xml(cls, rr: ElementTree.Element):
        """Alternative constructor - creates an instance of TXTRecord from
        its XML representation.
        """
        if rr.find("type").text != "TXT":
            raise ValueError("Record is not a TXT record")

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
                raise ValueError("Invalid TTL")
        self.priority = int(priority)
        self.weight = int(weight)
        self.port = int(port)
        self.target = target

    @property
    def record_type(self):
        return "SRV"

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = self.as_etree
        _srv = ElementTree.SubElement(root, "srv")
        ElementTree.SubElement(_srv, "priority").text = str(self.priority)
        ElementTree.SubElement(_srv, "weight").text = str(self.weight)
        ElementTree.SubElement(_srv, "port").text = str(self.port)
        _target = ElementTree.SubElement(_srv, "target")
        ElementTree.SubElement(_target, "name").text = str(self.target)
        return ElementTree.tostring(root, encoding="unicode")

    @classmethod
    def from_xml(cls, rr: ElementTree.Element):
        """Alternative constructor - creates an instance of SRVRecord from
        its XML representation.
        """
        if rr.find("type").text != "SRV":
            raise ValueError("Record is not an SRV record")

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


class PTRRecord(DNSRecord):
    """Model of PTR record."""

    ttl = None

    def __init__(self, ptr, ttl=None, **kwargs):
        super(PTRRecord, self).__init__(**kwargs)
        if ttl is not None:
            self.ttl = int(ttl)
            if self.ttl == 0:
                raise ValueError("Invalid TTL")
        self.ptr = ptr

    @property
    def record_type(self):
        return "PTR"

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = self.as_etree
        _ptr = ElementTree.SubElement(root, "ptr")
        ElementTree.SubElement(_ptr, "name").text = self.ptr
        return ElementTree.tostring(root, encoding="unicode")

    @classmethod
    def from_xml(cls, rr: ElementTree.Element):
        """Alternative constructor - creates an instance of PTRRecord from
        its XML representation.
        """
        if rr.find("type").text != "PTR":
            raise ValueError("Record is not a PTR record")

        id_ = rr.attrib["id"] if "id" in rr.attrib else None
        name = rr.find("name").text
        idn_name = rr.find("idn-name").text
        elem_ttl = rr.find("ttl")
        ttl = elem_ttl.text if elem_ttl is not None else None
        ptr = rr.find("ptr/name").text
        return cls(id_=id_, name=name, idn_name=idn_name, ttl=ttl, ptr=ptr)


class DNAMERecord(DNSRecord):
    """Model of DNAME record."""

    ttl = None

    def __init__(self, dname, ttl=None, **kwargs):
        super(DNAMERecord, self).__init__(**kwargs)
        if ttl is not None:
            self.ttl = int(ttl)
            if self.ttl == 0:
                raise ValueError("Invalid TTL")
        self.dname = dname

    @property
    def record_type(self):
        return "DNAME"

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = self.as_etree
        _dname = ElementTree.SubElement(root, "dname")
        ElementTree.SubElement(_dname, "name").text = self.dname
        return ElementTree.tostring(root, encoding="unicode")

    @classmethod
    def from_xml(cls, rr: ElementTree.Element):
        """Alternative constructor - creates an instance of DNAMERecord from
        its XML representation.
        """
        if rr.find("type").text != "DNAME":
            raise ValueError("Record is not a DNAME record")

        id_ = rr.attrib["id"] if "id" in rr.attrib else None
        name = rr.find("name").text
        idn_name = rr.find("idn-name").text
        elem_ttl = rr.find("ttl")
        ttl = elem_ttl.text if elem_ttl is not None else None
        dname = rr.find("dname/name").text
        return cls(id_=id_, name=name, idn_name=idn_name, ttl=ttl, dname=dname)


class HINFORecord(DNSRecord):
    """Model of HINFO record."""

    ttl = None

    def __init__(self, hardware, os, ttl=None, **kwargs):
        super(HINFORecord, self).__init__(**kwargs)
        if ttl is not None:
            self.ttl = int(ttl)
            if self.ttl == 0:
                raise ValueError("Invalid TTL")
        self.hardware = hardware
        self.os = os

    @property
    def record_type(self):
        return "HINFO"

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = self.as_etree
        _hinfo = ElementTree.SubElement(root, "hinfo")
        ElementTree.SubElement(_hinfo, "hardware").text = self.hardware
        ElementTree.SubElement(_hinfo, "os").text = self.os
        return ElementTree.tostring(root, encoding="unicode")

    @classmethod
    def from_xml(cls, rr: ElementTree.Element):
        """Alternative constructor - creates an instance of HINFORecord from
        its XML representation.
        """
        if rr.find("type").text != "HINFO":
            raise ValueError("Record is not an HINFO record")

        id_ = rr.attrib["id"] if "id" in rr.attrib else None
        name = rr.find("name").text
        idn_name = rr.find("idn-name").text
        elem_ttl = rr.find("ttl")
        ttl = elem_ttl.text if elem_ttl is not None else None
        hardware = rr.find("hinfo/hardware").text
        os = rr.find("hinfo/os").text
        return cls(
            id_=id_,
            name=name,
            idn_name=idn_name,
            ttl=ttl,
            hardware=hardware,
            os=os,
        )


class NAPTRRecord(DNSRecord):
    """Model of NAPTR record."""

    ttl = None

    def __init__(
        self,
        order,
        preference,
        flags,
        service,
        regexp="",
        replacement="",
        ttl=None,
        **kwargs,
    ):
        super(NAPTRRecord, self).__init__(**kwargs)
        if ttl is not None:
            self.ttl = int(ttl)
            if self.ttl == 0:
                raise ValueError("Invalid TTL")
        self.order = int(order)
        self.preference = int(preference)
        self.flags = flags
        self.service = service
        self.regexp = regexp
        self.replacement = replacement

    @property
    def record_type(self):
        return "NAPTR"

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = self.as_etree
        _naptr = ElementTree.SubElement(root, "naptr")
        ElementTree.SubElement(_naptr, "order").text = str(self.order)
        ElementTree.SubElement(_naptr, "preference").text = str(self.preference)
        ElementTree.SubElement(_naptr, "flags").text = self.flags
        ElementTree.SubElement(_naptr, "service").text = self.service
        ElementTree.SubElement(_naptr, "regexp").text = self.regexp
        _replacement = ElementTree.SubElement(_naptr, "replacement")
        ElementTree.SubElement(_replacement, "name").text = self.replacement
        return ElementTree.tostring(root, encoding="unicode")

    @classmethod
    def from_xml(cls, rr: ElementTree.Element):
        """Alternative constructor - creates an instance of NAPTRRecord from
        its XML representation.
        """
        if rr.find("type").text != "NAPTR":
            raise ValueError("Record is not an NAPTR record")

        id_ = rr.attrib["id"] if "id" in rr.attrib else None
        name = rr.find("name").text
        idn_name = rr.find("idn-name").text
        elem_ttl = rr.find("ttl")
        ttl = elem_ttl.text if elem_ttl is not None else None
        order = rr.find("naptr/order").text
        preference = rr.find("naptr/preference").text
        flags = rr.find("naptr/flags").text
        service = rr.find("naptr/service").text
        regexp = rr.find("naptr/regexp").text
        replacement = rr.find("naptr/replacement/name").text
        return cls(
            id_=id_,
            name=name,
            idn_name=idn_name,
            ttl=ttl,
            order=order,
            preference=preference,
            flags=flags,
            service=service,
            regexp=regexp,
            replacement=replacement,
        )


class RPRecord(DNSRecord):
    """Model of RP record."""

    ttl = None

    def __init__(self, mbox, txt, ttl=None, **kwargs):
        super(RPRecord, self).__init__(**kwargs)
        if ttl is not None:
            self.ttl = int(ttl)
            if self.ttl == 0:
                raise ValueError("Invalid TTL")
        self.mbox = mbox
        self.txt = txt

    @property
    def record_type(self):
        return "RP"

    def to_xml(self):
        """Returns an XML representation of record object."""
        root = self.as_etree
        _rp = ElementTree.SubElement(root, "rp")
        _mbox = ElementTree.SubElement(_rp, "mbox-dname")
        ElementTree.SubElement(_mbox, "name").text = self.mbox
        _txt = ElementTree.SubElement(_rp, "txt-dname")
        ElementTree.SubElement(_txt, "name").text = self.txt
        return ElementTree.tostring(root, encoding="unicode")

    @classmethod
    def from_xml(cls, rr: ElementTree.Element):
        """Alternative constructor - creates an instance of RPRecord from
        its XML representation.
        """
        if rr.find("type").text != "RP":
            raise ValueError("Record is not an HINFO record")

        id_ = rr.attrib["id"] if "id" in rr.attrib else None
        name = rr.find("name").text
        idn_name = rr.find("idn-name").text
        elem_ttl = rr.find("ttl")
        ttl = elem_ttl.text if elem_ttl is not None else None
        mbox = rr.find("rp/mbox-dname/name").text
        txt = rr.find("rp/txt-dname/name").text
        return cls(
            id_=id_,
            name=name,
            idn_name=idn_name,
            ttl=ttl,
            mbox=mbox,
            txt=txt,
        )
