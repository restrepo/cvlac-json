import datetime as dt

import pytest

from cvlac_json import extract, normalize_cod_rh
from cvlac_json.parser import build

COD = "0000000001"


@pytest.fixture
def data(page):
    return extract(COD, html=page, scienti="off", ror=False, log=lambda m: None)


def test_normalize_cod_rh():
    assert normalize_cod_rh("26549") == "0000026549"
    assert normalize_cod_rh(" 0000026549 ") == "0000026549"
    with pytest.raises(ValueError):
        normalize_cod_rh("12a")
    with pytest.raises(ValueError):
        normalize_cod_rh("12345678901")


def test_build_rejects_page_without_sections():
    with pytest.raises(SystemExit):
        build("<html><body>no sections</body></html>", COD)


def test_top_level(data):
    assert data["cod_rh"] == COD
    assert data["url"].endswith(f"cod_rh={COD}")
    for key in ("profile", "education", "experience", "works", "projects", "events", "sections", "counts"):
        assert key in data


def test_profile(data):
    p = data["profile"]
    assert p["Nombre"] == "Ana María Pérez Gómez"
    assert p["Nombre en citaciones"] == "PÉREZ GÓMEZ, ANA MARÍA"
    assert p["notes"] == ["Par evaluador reconocido por Minciencias"]


def test_education(data):
    (phd,) = data["education"]["academic"]
    assert phd["level"] == "Doctorado"
    assert phd["start"] == {"year": 2010, "month": 1}
    assert phd["end"] == {"year": 2014, "month": 12}


def test_experience_years(data):
    udea, unal = data["experience"]
    assert (udea["start_year"], udea["end_year"], udea["open_end"]) == (2015, dt.date.today().year, True)
    assert (unal["start_year"], unal["end_year"], unal["open_end"]) == (2008, 2012, False)


def test_article(data):
    w = data["works"][0]
    assert w["id"] == f"cvlac:{COD}:1"
    assert w["title"] == "A synthetic benchmark for testing CvLAC parsers"
    assert [t["type"] for t in w["types"]] == ["Producción bibliográfica", "Artículo", "Publicado en revista especializada"]
    assert w["year_published"] == 2017
    assert w["doi"] == "https://doi.org/10.9999/synthetic.2017.003"
    assert w["source"]["name"] == "REVISTA DE PRUEBAS SINTETICAS"
    assert w["source"]["external_ids"] == [{"source": "issn", "id": "1234-5679"}]
    assert w["bibliographic_info"] == {"volume": "12", "issue": "3", "start_page": "101", "end_page": "115"}
    assert w["keywords"] == ["parsing", "testing"]
    assert w["cvlac"]["endorsed"] is True
    owner, coauthor = w["authors"]
    assert owner["id"] == COD and coauthor["id"] is None


def test_owner_affiliation_by_year(data):
    a2017, a2010 = (w["authors"][0]["affiliations"] for w in data["works"])
    assert [a["name"] for a in a2017] == ["UNIVERSIDAD DE ANTIOQUIA"]
    assert [a["name"] for a in a2010] == ["UNIVERSIDAD NACIONAL DE COLOMBIA SEDE MEDELLÍN"]


def test_same_keys_in_every_work(data):
    keys = {tuple(sorted(w)) for w in data["works"]}
    assert len(keys) == 1
    second = data["works"][1]
    assert second["doi"] is None  # kept, empty, because the first work has a DOI
    assert second["keywords"] == []
    assert second["bibliographic_info"]["issue"] is None  # 'N/A' on the page


def test_no_fields_cvlac_never_has(data):
    for k in ("abstracts", "citations_count", "groups", "ranking", "language", "date_published"):
        assert k not in data["works"][0]


def test_thesis_advisor(data):
    phd, _msc = data["sections"]["Trabajos dirigidos/tutorías"]
    assert phd["title"] == "Análisis de datos sintéticos para la evaluación de algoritmos (Caso de estudio)"
    assert phd["status"] == "ongoing" and phd["status_text"] == "Tesis en curso"
    assert phd["program"] == "Doctorado en Ingeniería Electrónica"
    assert phd["year"] == 2021
    assert [(a["full_name"], a["type"]) for a in phd["authors"]] == [
        ("ANA MARIA PEREZ GOMEZ", "advisor"),
        ("LUIS FERNANDO TORRES VEGA", "co-advisor"),
        ("Carlos Andrés Ruiz Mejía", "student"),
    ]
    assert phd["institution"]["name"] == "UNIVERSIDAD DE ANTIOQUIA"


def test_thesis_owner_as_co_advisor(data):
    msc = data["sections"]["Trabajos dirigidos/tutorías"][1]
    assert msc["status"] == "completed"
    assert msc["role"] == "Coturor/asesor"
    assert [a["type"] for a in msc["authors"]] == ["co-advisor", "student"]
    assert msc["duration_months"] == 12


def test_project(data):
    (p,) = data["projects"]
    assert p["title"] == "Plataforma sintética para pruebas"
    assert p["start"] == {"year": 2019, "month": 3}
    assert p["end"] == {"year": 2021, "month": 2}
    assert p["duration_months"] == 24


def test_counts(data):
    c = data["counts"]
    assert c["works"] == 2 and c["endorsed_works"] == 1 and c["projects"] == 1
    assert c["Trabajos dirigidos/tutorías"] == 2
