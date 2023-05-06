from xml.etree import ElementTree

from nic_api.models import (
    parse_record,
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


def _parse_record_nonstrict(xml_string: str) -> ElementTree.Element:
    rr = ElementTree.fromstring(xml_string)
    if not rr.find("idn-name"):
        _name = rr.find("name").text
        if _name:
            _name = _name.encode().decode("idna")
        ElementTree.SubElement(rr, "idn-name").text = _name
    return parse_record(rr)


def test_export_and_parse_soa():
    record = SOARecord(
        serial=1001,
        refresh=86400,
        retry=7200,
        expire=4000000,
        minimum=14400,
        mname={"name": "ns.nic-api-test.com."},
        rname={"name": "admin.nic-api-test.com."},
    )
    record_xml = record.to_xml()
    assert isinstance(record_xml, str)
    assert record_xml
    record_parsed = _parse_record_nonstrict(record_xml)
    assert isinstance(record_parsed, SOARecord)
    assert record_parsed.serial == 1001
    assert record_parsed.refresh == 86400
    assert record_parsed.retry == 7200
    assert record_parsed.expire == 4000000
    assert record_parsed.minimum == 14400
    assert record_parsed.mname.name == "ns.nic-api-test.com."
    assert record_parsed.rname.name == "admin.nic-api-test.com."


def test_export_and_parse_ns():
    record = NSRecord(ns="ns.nic-api-test.com.")
    record_xml = record.to_xml()
    assert isinstance(record_xml, str)
    assert record_xml
    record_parsed = _parse_record_nonstrict(record_xml)
    assert isinstance(record_parsed, NSRecord)
    assert record_parsed.ns == "ns.nic-api-test.com."


def test_export_and_parse_a():
    record = ARecord(a="192.168.0.1")
    record_xml = record.to_xml()
    assert isinstance(record_xml, str)
    assert record_xml
    record_parsed = _parse_record_nonstrict(record_xml)
    assert isinstance(record_parsed, ARecord)
    assert record_parsed.a == "192.168.0.1"


def test_export_and_parse_a_idna():
    record = ARecord(a="192.168.0.2", name="тест".encode("idna").decode())
    record_xml = record.to_xml()
    assert isinstance(record_xml, str)
    assert record_xml
    record_parsed = _parse_record_nonstrict(record_xml)
    assert isinstance(record_parsed, ARecord)
    assert record_parsed.a == "192.168.0.2"
    assert record_parsed.name == "xn--e1aybc"
    assert record_parsed.idn_name == "тест"


def test_export_and_parse_aaaa():
    record = AAAARecord(aaaa="fe80:cafe:cafe:cafe:cafe:cafe")
    record_xml = record.to_xml()
    assert isinstance(record_xml, str)
    assert record_xml
    record_parsed = _parse_record_nonstrict(record_xml)
    assert isinstance(record_parsed, AAAARecord)
    assert record_parsed.aaaa == "fe80:cafe:cafe:cafe:cafe:cafe"


def test_export_and_parse_cname():
    record = CNAMERecord(cname="www")
    record_xml = record.to_xml()
    assert isinstance(record_xml, str)
    assert record_xml
    record_parsed = _parse_record_nonstrict(record_xml)
    assert isinstance(record_parsed, CNAMERecord)
    assert record_parsed.cname == "www"


def test_export_and_parse_mx():
    record = MXRecord(preference=10, exchange="mail")
    record_xml = record.to_xml()
    assert isinstance(record_xml, str)
    assert record_xml
    record_parsed = _parse_record_nonstrict(record_xml)
    assert isinstance(record_parsed, MXRecord)
    assert record_parsed.preference == 10
    assert record_parsed.exchange == "mail"


def test_export_and_parse_txt():
    record = TXTRecord(txt="hello world")
    record_xml = record.to_xml()
    assert isinstance(record_xml, str)
    assert record_xml
    record_parsed = _parse_record_nonstrict(record_xml)
    assert isinstance(record_parsed, TXTRecord)
    assert record_parsed.txt == "hello world"


def test_export_and_parse_srv():
    record = SRVRecord(
        priority=0,
        weight=5,
        port=9999,
        target="example.nic-api-test.com.",
    )
    record_xml = record.to_xml()
    assert isinstance(record_xml, str)
    assert record_xml
    record_parsed = _parse_record_nonstrict(record_xml)
    assert isinstance(record_parsed, SRVRecord)
    assert record_parsed.priority == 0
    assert record_parsed.weight == 5
    assert record_parsed.port == 9999
    assert record_parsed.target == "example.nic-api-test.com."


def test_export_and_parse_ptr():
    record = PTRRecord(ptr="1.0.168.192.in-addr.arpa.")
    record_xml = record.to_xml()
    assert isinstance(record_xml, str)
    assert record_xml
    record_parsed = _parse_record_nonstrict(record_xml)
    assert isinstance(record_parsed, PTRRecord)
    assert record_parsed.ptr == "1.0.168.192.in-addr.arpa."


def test_export_and_parse_dname():
    record = DNAMERecord(dname="nic-api-test-2.com.")
    record_xml = record.to_xml()
    assert isinstance(record_xml, str)
    assert record_xml
    record_parsed = _parse_record_nonstrict(record_xml)
    assert isinstance(record_parsed, DNAMERecord)
    assert record_parsed.dname == "nic-api-test-2.com."


def test_export_and_parse_hinfo():
    record = HINFORecord(hardware="IBM-PC/XT", os="OS/2")
    record_xml = record.to_xml()
    assert isinstance(record_xml, str)
    assert record_xml
    record_parsed = _parse_record_nonstrict(record_xml)
    assert isinstance(record_parsed, HINFORecord)
    assert record_parsed.hardware == "IBM-PC/XT"
    assert record_parsed.os == "OS/2"


def test_export_and_parse_naptr():
    record = NAPTRRecord(
        order=1,
        preference=100,
        flags="S",
        service="sip+D2U",
        replacement="_sip._udp.nic-api-test.com.",
    )
    record_xml = record.to_xml()
    assert isinstance(record_xml, str)
    assert record_xml
    record_parsed = _parse_record_nonstrict(record_xml)
    assert isinstance(record_parsed, NAPTRRecord)
    assert record_parsed.order == 1
    assert record_parsed.preference == 100
    assert record_parsed.flags == "S"
    assert record_parsed.service == "sip+D2U"
    assert record_parsed.replacement == "_sip._udp.nic-api-test.com."


def test_export_and_parse_rp():
    record = RPRecord(mbox="info.andrian.ninja.", txt=".")
    record_xml = record.to_xml()
    assert isinstance(record_xml, str)
    assert record_xml
    record_parsed = _parse_record_nonstrict(record_xml)
    assert isinstance(record_parsed, RPRecord)
    assert record_parsed.mbox == "info.andrian.ninja."
    assert record_parsed.txt == "."
