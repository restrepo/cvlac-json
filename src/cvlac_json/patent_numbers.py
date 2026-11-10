"""Patent office numbers from the patent id a CvLAC gives (`patents[].identifiers[]` with source "patent").

    patent_numbers("NC2019/0013866", "Colombia")
    -> [{"field": "application", "office": "CO", "number": "2019013866"}]

A CvLAC writes the id as the researcher typed it. Each id is read, with the record's country, as the numbers patent
databases index (The Lens, EPO, WIPO, Google Patents: jurisdiction plus `doc_number` of the publication, or of the
application):

    NC2019/0013866            CO application 2019013866 (the publication is CO2019013866A1)
    13016114, 15-045782-...   CO application 13016114 / 15045782 (older SIC filing numbers; country Colombia)
    PCT/IB2011/052609         IB (WIPO) application 2011052609 (its record is the WO publication)
    US 2018/0146662 A1        US publication 20180146662 (US: year + 7 digits)
    WO 2013/008209 A3         WO publication 2013008209 (WO: year + 6 digits)
    US 10,085,948 B2          US publication 10085948, and the same number as an application
    6973247 (Estados Unidos)  US publication 6973247, and as an application (the office from the record's country)

field is "publication" or "application"; office a two-letter office code (a country, "EP", "WO" or "IB"). An id with
no recognisable number (a title, "En trámite") gives []. No network: standard library only.
"""

import re
import unicodedata

COUNTRY = {
    "colombia": "CO", "estados unidos": "US", "espana": "ES", "suiza": "CH", "alemania": "DE", "mexico": "MX",
    "francia": "FR", "china": "CN", "brasil": "BR", "chile": "CL", "canada": "CA", "peru": "PE", "india": "IN",
    "australia": "AU", "rusia": "RU", "reino unido": "GB", "inglaterra": "GB", "paises bajos": "NL", "japon": "JP",
    "corea del sur": "KR", "argentina": "AR", "oficina europea de patentes": "EP", "europa": "EP",
}  # fmt: skip
OFFICES = set(COUNTRY.values()) | {"WO", "EP", "IB"}


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def office_code(country):
    """The office code of a CvLAC country name ("Estados Unidos" -> "US"), or None."""
    return COUNTRY.get(_norm(country))


def patent_numbers(raw, country=None):
    """[{"field", "office", "number"}] for a CvLAC patent id and the record's country."""
    cc = office_code(country)
    s = re.sub(r"[\s,.]", "", (raw or "").upper())
    out = []
    if m := re.search(r"NC(\d{4})/?(\d{6,7})", s):
        out.append(("application", "CO", m.group(1) + m.group(2)[-6:]))
    elif m := re.search(r"PCT/?([A-Z]{2})(\d{4})/?(\d{6})", s):
        out.append(("application", m.group(1), m.group(2) + m.group(3)))
    elif m := re.search(r"(?<![A-Z])([A-Z]{2})/?(\d{4})/(\d{6,7})", s):  # US 2018/0146662 A1, WO 2013/008209 A3
        if m.group(1) in OFFICES:
            n = m.group(3)[-6:] if m.group(1) == "WO" else m.group(3).zfill(7)
            out.append(("publication", m.group(1), m.group(2) + n))
    elif m := re.search(r"(?<![A-Z])([A-Z]{2})(\d{5,12})", s):  # US10085948B2, EP1234567, CO7010163A1
        if m.group(1) in OFFICES:
            out += [("publication", m.group(1), m.group(2)), ("application", m.group(1), m.group(2))]
    elif cc == "CO" and (m := re.fullmatch(r"(\d{2})-?(\d{6})(-[\d-]+)?", s)):
        out.append(("application", "CO", m.group(1) + m.group(2)))
    elif cc and (m := re.fullmatch(r"(\d{6,12})([A-Z]\d?)?", s)):  # 20180146662 A1 (Estados Unidos)
        out += [("publication", cc, m.group(1)), ("application", cc, m.group(1))]
    return [{"field": f, "office": o, "number": n} for f, o, n in out]
