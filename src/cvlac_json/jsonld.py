"""JSON-LD view of the CvLAC JSON.

``to_jsonld(data)`` returns the same document plus ``@context``, ``@id`` and ``@type``: every key keeps its
name and value, so the document reads as before. The context maps keys to schema.org where the meaning is
clear and to the cvlac-json vocabulary otherwise.

- Keys that are page labels ('Nombre en citaciones', 'Categoría'...) get their own terms, with the label
  percent-encoded in the IRI. Open dictionaries of labels (``counts``, ``fields``) stay JSON literals.
- ``sections`` is an index map: each item gets a ``section`` property with its section title.
- ``authors`` is an ordered list, so the citation order survives in RDF.
- Works, projects, events and section items get an ``@id`` made of the profile IRI and a JSON Pointer to
  their place in the document: ``<profile IRI>#/works/0``.
"""

import copy
import re
from urllib.parse import quote

VOCAB = "https://github.com/fedevergara/cvlac-json/blob/main/docs/cvlac_json_esquema.md#"
CVLAC_URL = "https://scienti.minciencias.gov.co/cvlac/visualizador/generarCurriculoCv.do?cod_rh="

_SAFE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TERMS = {
    "cod_rh": "schema:identifier",
    "id": "schema:identifier",
    "url": "schema:url",
    "retrieved": {"@id": "prov:generatedAtTime", "@type": "xsd:dateTime"},
    "name": "schema:name",
    "full_name": "schema:name",
    "title": "schema:name",
    "summary": "schema:abstract",
    "keywords": "schema:keywords",
    "authors": {"@id": "schema:author", "@container": "@list"},  # citation order matters
    "year_published": {"@id": "schema:datePublished", "@type": "xsd:gYear"},
    "doi": {"@id": "schema:sameAs", "@type": "@id"},
    "counts": {"@type": "@json"},
    "fields": {"@type": "@json"},
    "sections": {"@container": "@index", "@index": "section"},
    "Nombre": "schema:name",
    "Nacionalidad": "schema:nationality",
    "Sexo": "schema:gender",
}
_ITEMS = (("works", "schema:CreativeWork"), ("projects", "schema:ResearchProject"), ("events", "schema:Event"))


def context(vocab=VOCAB, labels=()):
    """The @context; ``labels`` are extra keys (page labels) that need their own term."""
    ctx = {
        "@version": 1.1,
        "@vocab": vocab,
        "schema": "https://schema.org/",
        "prov": "http://www.w3.org/ns/prov#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        **_TERMS,
    }
    for k in labels:
        if k not in ctx and not _SAFE.match(k):
            ctx[k] = vocab + quote(k, safe="")
    return ctx


def pointer(*parts):
    """JSON Pointer fragment (RFC 6901), percent-encoded for an IRI: pointer('sections', 'A/B', 0) -> '#/sections/A~1B/0'."""
    return "#" + "".join("/" + quote(str(p).replace("~", "~0").replace("/", "~1"), safe="~") for p in parts)


def to_jsonld(data, base=None, vocab=VOCAB):
    """JSON-LD document for the output of ``extract()``; ``data`` is not modified.

    The profile IRI is ``base + cod_rh`` when ``base`` is given (e.g. the URL of a service that serves the
    profiles), otherwise the URL of the CvLAC page.
    """
    doc = copy.deepcopy(data)
    cod = doc.get("cod_rh") or ""
    iri = f"{base}{cod}" if base else doc.get("url") or CVLAC_URL + cod
    for key, typ in _ITEMS:
        for i, item in enumerate(doc.get(key) or []):
            item["@id"], item["@type"] = iri + pointer(key, i), typ
    for title, items in (doc.get("sections") or {}).items():
        for i, item in enumerate(items or []):
            if isinstance(item, dict):
                item["@id"] = iri + pointer("sections", title, i)
    return {
        "@context": context(vocab, labels=doc.get("profile") or {}),
        "@id": iri,
        "@type": ["schema:ProfilePage", "CvlacProfile"],
        **doc,
    }
