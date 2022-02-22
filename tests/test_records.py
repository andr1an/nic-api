"""Simulates `DnsApi.add_record()` beahvior to test Python 2.7 and 3.X `str`
compatibility.
"""

import random
import textwrap

from nic_api.models import ARecord, CNAMERecord, TXTRecord


def test_a_root():
    record = ARecord(a="255.255.255.255")
    record_xml = record.to_xml()
    assert record_xml


def test_a_to_xml():
    rr_list = []

    for _ in range(3):
        _name = "testrec{:.0f}".format(random.random() * 1000.0)
        record = ARecord(name=_name, a="255.255.255.255")
        record_xml = record.to_xml()
        rr_list.append(record_xml)

    _xml = textwrap.dedent(
        """\
        <?xml version="1.0" encoding="UTF-8" ?>
        <request><rr-list>
        {}
        </rr-list></request>"""
    ).format("\n".join(rr_list))

    assert _xml


def test_cname_to_xml():
    rr_list = []

    for _ in range(3):
        _name = "testrec{:.0f}".format(random.random() * 1000.0)
        record = CNAMERecord(name=_name, cname="www")
        record_xml = record.to_xml()
        rr_list.append(record_xml)

    _xml = textwrap.dedent(
        """\
        <?xml version="1.0" encoding="UTF-8" ?>
        <request><rr-list>
        {}
        </rr-list></request>"""
    ).format("\n".join(rr_list))

    assert _xml


def test_txt_to_xml():
    rr_list = []

    for _ in range(3):
        _name = "testrec{:.0f}".format(random.random() * 1000.0)
        _txt = "{:.0f}".format(random.random() * 1000000000.0)
        record = TXTRecord(name=_name, txt=_txt)
        record_xml = record.to_xml()
        rr_list.append(record_xml)

    _xml = textwrap.dedent(
        """\
        <?xml version="1.0" encoding="UTF-8" ?>
        <request><rr-list>
        {}
        </rr-list></request>"""
    ).format("\n".join(rr_list))

    assert _xml
