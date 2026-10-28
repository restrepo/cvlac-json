from cvlac_json import scienti


def test_norm_and_doi():
    assert scienti.norm("Évaluación  de  ÑAME!") == "evaluacion de name"
    assert scienti.ndoi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert scienti.ndoi("doi: 10.1000/x") == "10.1000/x"
    assert scienti.ndoi("not a doi") is None


def _rec(id_, title, year, doi=None, issn=()):
    return {
        "id": id_,
        "title": scienti.norm(title),
        "raw_title": title,
        "year": year,
        "doi": doi,
        "issn": set(issn),
        "isbn": set(),
        "venues": set(),
        "patent": None,
        "type": "Producción bibliográfica",
        "code": "111",
    }


INDEX = [
    _rec("1-10", "A synthetic benchmark for testing CvLAC parsers", 2017, doi="10.9999/synthetic.2017.003"),
    _rec("1-11", "Un segundo artículo de prueba sin DOI", 2010, issn={"23456780"}),
    _rec("1-12", "Estudio muy largo sobre la influencia de la composición química de los gases", 2015),
]


def test_match_by_doi():
    c, by, ev = scienti.match_entry(INDEX, set(), title="whatever", doi="https://doi.org/10.9999/SYNTHETIC.2017.003", year=2017)
    assert c["id"] == "1-10" and by == "doi" and "year" in ev


def test_match_by_title_needs_evidence():
    c, by, ev = scienti.match_entry(INDEX, set(), title="Un segundo artículo de prueba sin DOI", year=2010)
    assert (c["id"], by, ev) == ("1-11", "title", ["year"])
    assert scienti.match_entry(INDEX, set(), title="Un segundo artículo de prueba sin DOI", year=1999) == (None, None, None)


def test_match_truncated_title_same_year():
    long = "Estudio muy largo sobre la influencia de la composición química de los gases naturales colombianos"
    c, by, _ = scienti.match_entry(INDEX, set(), title=long, year=2015)
    assert c["id"] == "1-12" and by == "title prefix"
    assert scienti.match_entry(INDEX, set(), title=long, year=2016)[0] is None


def test_apikey_precedence(monkeypatch):
    assert scienti.apikey() is None
    scienti.KEY_FILE.write_text("from-file\n")
    assert scienti.apikey() == "from-file"
    monkeypatch.setenv("COLAV_APIKEY", "from-env")
    assert scienti.apikey() == "from-env"
    assert scienti.apikey("explicit") == "explicit"


def test_enrich_without_key_is_skipped():
    msgs = []
    assert scienti.enrich({"works": []}, "0000000001", log=msgs.append) is False
    assert "no API key" in msgs[0]
