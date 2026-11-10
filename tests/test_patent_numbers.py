import pytest

from cvlac_json.patent_numbers import office_code, patent_numbers


def nums(raw, country=None):
    return [(x["field"], x["office"], x["number"]) for x in patent_numbers(raw, country)]


@pytest.mark.parametrize(
    "raw, country, expected",
    [
        ("NC2019/0013866", "Colombia", [("application", "CO", "2019013866")]),
        ("NC 2018/0014315", "Colombia", [("application", "CO", "2018014315")]),
        ("13016114", "Colombia", [("application", "CO", "13016114")]),
        ("15-045782-00000-0000", "Colombia", [("application", "CO", "15045782")]),
        ("PCT/IB2011/052609", "Colombia", [("application", "IB", "2011052609")]),
        ("US 2018/0146662 A1", "Estados Unidos", [("publication", "US", "20180146662")]),
        ("WO 2013/008209 A3", None, [("publication", "WO", "2013008209")]),
        ("US 10,085,948 B2", None, [("publication", "US", "10085948"), ("application", "US", "10085948")]),
        ("CO7010163A1", "Colombia", [("publication", "CO", "7010163"), ("application", "CO", "7010163")]),
        ("6973247", "Estados Unidos", [("publication", "US", "6973247"), ("application", "US", "6973247")]),
        ("20180146662 A1", "Estados Unidos", [("publication", "US", "20180146662"), ("application", "US", "20180146662")]),
        ("En trámite", "Colombia", []),
        ("6973247", None, []),
        ("", "Colombia", []),
        (None, None, []),
    ],
)
def test_patent_numbers(raw, country, expected):
    assert nums(raw, country) == expected


def test_office_code():
    assert office_code("Estados Unidos") == "US"
    assert office_code("ESPAÑA") == "ES"
    assert office_code("Oficina Europea de Patentes") == "EP"
    assert office_code("Narnia") is None
