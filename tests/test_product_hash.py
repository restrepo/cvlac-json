import hashlib
import json
import pathlib

import pytest

from cvlac_json import extract, product_hash
from cvlac_json.parser import product_lists
from cvlac_json.product_hash import hash_key, product_hashes, title_key

VECTORS = json.loads((pathlib.Path(__file__).parent / "product_hash_vectors.json").read_text(encoding="utf-8"))
TOY = pathlib.Path(__file__).parent / "fixtures" / "cvlac_juguete.html"


@pytest.mark.parametrize("v", VECTORS, ids=[v["key"][:40] for v in VECTORS])
def test_vectors(v):
    """The same vectors are in gruplac-json: both packages must give these keys and hashes."""
    assert hash_key(v["title"], v["cod_rh"], v["kind"], v["year"], v.get("n", 1)) == v["key"]
    assert product_hash(v["title"], v["cod_rh"], v["kind"], v["year"], v.get("n", 1)) == v["hash"]
    assert v["hash"] == hashlib.sha1(v["key"].encode("ascii")).hexdigest()


def test_title_key():
    assert title_key("Bleomicina: Una revisión") == title_key("bleomicina:una  revision") == "bleomicinaunarevision"
    assert title_key("Física √𝑠=13  TeV") == "fisicas13tev"
    assert title_key(None) == title_key("") == ""


def test_key_parts():
    assert hash_key("Un título", "707619", "work", 2024) == "untitulo|0000707619|work|2024"
    assert hash_key("Un título", "0000707619", "other", None) == "untitulo|0000707619|other|"
    assert product_hash("x", "1", "work", 2020) != product_hash("x", "1", "work", 2021)  # the year counts
    assert product_hash("x", "1", "work", 2020) != product_hash("x", "1", "other", 2020)  # and the kind
    with pytest.raises(ValueError):
        hash_key("x", "1", "event")


def test_on_the_owner_entry_of_every_record():
    d = extract("2", html=TOY.read_text(encoding="latin-1"), scienti="off", ror=False, log=lambda m: None)
    cod = d["cod_rh"]
    kinds = [("work", w, w["year_published"]) for w in d["works"]] + [("project", p, p["start"]["year"]) for p in d["projects"]]
    kinds += [("patent" if t == "Patentes" else "other", it, it.get("year")) for t, v in product_lists(d) for it in v]
    assert len(kinds) == 7
    for kind, rec, year in kinds:
        (owner,) = [a for a in rec["authors"] if a["id"] == cod]
        assert owner["product_hash"] == product_hash(rec["title"], cod, kind, year)
        assert all(a.get("product_hash") is None for a in rec["authors"] if a["id"] != cod)  # null: same keys rule
    assert d["counts"]["product_hash_repeated"] == 0


def test_same_title_and_year_get_an_occurrence_number():
    page = TOY.read_text(encoding="latin-1")
    page = page.replace('"El dueño con el nombre abreviado"', '"Un artículo de juguete con DOI"').replace(",2008,", ",2019,")
    d = extract("2", html=page, scienti="off", ror=False, log=lambda m: None)
    h = [next(a["product_hash"] for a in w["authors"] if a["id"] == "0000000002") for w in d["works"]]
    assert len(set(h)) == 3  # unique: the second record with the key gets n = 2
    assert h[0] == product_hash("Un artículo de juguete con DOI", "2", "work", 2019)
    assert h[1] == product_hash("Un artículo de juguete con DOI", "2", "work", 2019, n=2)
    assert d["counts"]["product_hash_repeated"] == 1


def test_product_hashes_numbers_repeats_in_order():
    recs = [("A", "other", 2020), ("B", "other", 2020), ("a", "other", 2020), (None, "other", 2020), ("", "other", 2020)]
    hs = product_hashes(recs, "1")
    assert len(set(hs)) == 5
    assert hs[2] == product_hash("A", "1", "other", 2020, n=2) and hs[4] == product_hash(None, "1", "other", 2020, n=2)
    assert hash_key("A", "1", "other", 2020, n=3) == "a|0000000001|other|2020|3"


def test_reproducible_from_a_gruplac_record():
    """A GrupLAC work lists the members who authored it; each member's hash is the one in that member's CvLAC."""
    d = extract("2", html=TOY.read_text(encoding="latin-1"), scienti="off", ror=False, log=lambda m: None)
    cv = next(a["product_hash"] for a in d["works"][0]["authors"] if a["id"] == "0000000002")
    gruplac_work = {
        "title": "Un artículo de juguete con DOI ",  # GrupLAC writes the title with other spacing
        "year_published": 2019,
        "authors": [{"full_name": "JUAN PABLO EJEMPLO PRUEBA", "id": "0000000002"}, {"full_name": "OTRA", "id": None}],
    }
    member = gruplac_work["authors"][0]
    assert product_hash(gruplac_work["title"], member["id"], "work", gruplac_work["year_published"]) == cv


def test_untitled_items_are_hashed_with_their_text():
    """Par evaluador reviews have no title: their text (scope, what was reviewed, journal or institution, year, month)
    takes its place, so reviews of one year get different hashes instead of |n numbers."""
    from cvlac_json.parser import add_product_hashes

    cod = "0000000002"
    owner = {"full_name": "JUAN PABLO EJEMPLO PRUEBA", "id": cod}

    def review(venue, month):
        text = f"Ámbito: Internacional Par evaluador de: Material para publicación científica Revista: {venue}, 2020, {month}"
        return {"authors": [dict(owner)], "venue": venue, "text": text, "year": 2020}

    revs = [review("REVISTA UNO", "Julio"), review("REVISTA DOS", "Julio"), review("REVISTA UNO", "Julio")]
    data = {"cod_rh": cod, "works": [], "projects": [], "patents": [], "other_products": {"Par evaluador": revs}}
    add_product_hashes(data)
    h = [r["authors"][0]["product_hash"] for r in revs]
    assert h[0] == product_hash(revs[0]["text"], cod, "other", 2020)
    assert h[1] == product_hash(revs[1]["text"], cod, "other", 2020)
    assert h[2] == product_hash(revs[0]["text"], cod, "other", 2020, n=2)  # the same review entered twice
    assert data["counts"]["product_hash_repeated"] == 1 and data["counts"]["product_hash_from_text"] == 3
    assert hash_key(revs[0]["text"], cod, "other", 2020).startswith("ambitointernacionalparevaluadorde")
