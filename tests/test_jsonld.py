import json
import re

import pytest

from cvlac_json import extract, to_jsonld
from cvlac_json.cli import main
from cvlac_json.jsonld import CVLAC_URL, VOCAB, context, pointer

COD = "0000000001"
BASE = "https://example.org/dam/scraped/cvlac/"


@pytest.fixture
def data(page):
    return extract(COD, html=page, scienti="off", ror=False, log=lambda m: None)


def strip_ld(v):
    """The document without the JSON-LD keys: it must be the input again."""
    if isinstance(v, dict):
        return {k: strip_ld(x) for k, x in v.items() if not k.startswith("@")}
    if isinstance(v, list):
        return [strip_ld(x) for x in v]
    return v


def test_same_document_plus_ld_keys(data):
    before = json.dumps(data, sort_keys=True)
    doc = to_jsonld(data)
    assert json.dumps(data, sort_keys=True) == before  # input not modified
    assert strip_ld(doc) == data
    assert doc["@id"] == data["url"] and "schema:ProfilePage" in doc["@type"]


def test_base_and_fallback_iri(data):
    assert to_jsonld(data, base=BASE)["@id"] == BASE + COD
    assert to_jsonld({k: v for k, v in data.items() if k != "url"})["@id"] == CVLAC_URL + COD


def test_items_are_json_pointers(data):
    doc = to_jsonld(data, base=BASE)
    assert doc["works"][0]["@id"] == f"{BASE}{COD}#/works/0"
    assert doc["projects"][0]["@type"] == "schema:ResearchProject"
    title, items = next(iter(doc["sections"].items()))
    assert items[0]["@id"] == BASE + COD + pointer("sections", title, 0)


def test_pointer_escapes():
    assert pointer("sections", "Trabajos dirigidos/tutorías", 0) == "#/sections/Trabajos%20dirigidos~1tutor%C3%ADas/0"
    assert pointer("a~b") == "#/a~0b"


def test_page_labels_get_terms():
    ctx = context(labels={"Nombre en citaciones": "x", "Nombre": "y", "notes": []})
    assert ctx["Nombre en citaciones"] == VOCAB + "Nombre%20en%20citaciones"
    assert ctx["Nombre"] == "schema:name"
    assert "notes" not in ctx  # plain keys use @vocab


def test_rdf(data):
    jsonld = pytest.importorskip("pyld.jsonld")
    nq = jsonld.to_rdf(to_jsonld(data, base=BASE), {"format": "application/n-quads"})
    iris = re.findall(r"<([^>]*)>", nq)
    assert iris and not [i for i in iris if re.search(r'[\s<>"{}|\\^`]', i)]
    assert f"<{BASE}{COD}#/works/0> <https://schema.org/author>" in nq  # ordered list of authors
    assert f"<{VOCAB}section>" in nq  # section title kept in RDF
    assert "http://www.w3.org/1999/02/22-rdf-syntax-ns#JSON" in nq  # counts, fields


def test_cli_jsonld(page, tmp_path, capsys):
    html = tmp_path / "cv.html"
    html.write_text(page, encoding="latin-1")
    rc = main([COD, "--html", str(html), "--scienti", "off", "--ror", "off", "--format", "jsonld", "--base", BASE, "-o", "-"])
    assert rc in (0, None)
    doc = json.loads(capsys.readouterr().out)
    assert doc["@id"] == BASE + COD and "@context" in doc
