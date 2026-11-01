import datetime as dt

import pytest

from cvlac_json import extract, normalize_cod_rh
from cvlac_json.parser import build, find_doi, items, work_from_item

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


def test_profile_name_parts(data):
    p = data["profile"]
    assert p["Nombre"] == "Ana María Pérez Gómez"  # original fields are kept
    assert (p["full_name"], p["first_names"], p["last_names"], p["name_split_by"]) == (
        "Ana María Pérez Gómez",
        ["Ana", "María"],
        ["Pérez", "Gómez"],
        "page",
    )


@pytest.mark.parametrize(
    ("prof", "raw", "first", "last", "by"),
    [
        (
            {"Nombre": "José Edgar Zapata Montoya", "Nombre en citaciones": "ZAPATA MONTOYA, JOSÉ EDGAR"},
            "<td>Nombre</td><td>José Edgar&nbsp;Zapata&nbsp;Montoya</td>",
            ["José", "Edgar"],
            ["Zapata", "Montoya"],
            "page",
        ),
        (
            {"Nombre": "Rosa Ospina", "Nombre en citaciones": "OSPINA, ROSA"},
            "<td>Nombre</td><td>Rosa&nbsp;Ospina&nbsp;</td>",
            ["Rosa"],
            ["Ospina"],
            "page",
        ),
        (
            {"Nombre": "Pedro Luis de la Cruz Ruiz", "Nombre en citaciones": "DE LA CRUZ RUIZ, PEDRO LUIS"},
            None,
            ["Pedro", "Luis"],
            ["de la Cruz", "Ruiz"],
            "citation name",
        ),
        (
            {"Nombre": "Ana María Pérez Gómez", "Nacionalidad": "Colombiana"},
            None,
            ["Ana", "María"],
            ["Pérez", "Gómez"],
            "nationality",
        ),
        ({"Nombre": "Hans Peter Müller", "Nacionalidad": "Alemana"}, None, ["Hans", "Peter"], ["Müller"], "nationality"),
    ],
)
def test_split_name(prof, raw, first, last, by):
    from cvlac_json.parser import split_name

    out = split_name(raw, prof)
    assert (out["first_names"], out["last_names"], out["name_split_by"]) == (first, last, by)


@pytest.mark.parametrize(
    "texts, doi",
    [
        (["10.1111/rda.13599"], "10.1111/rda.13599"),
        (["https://doi.org/10.1016/j.acci.2016.02.002"], "10.1016/j.acci.2016.02.002"),
        (["Rev. Acad. Colomb. Cienc. Ex. Fis. Nahttp://dx.doi.org/10.18257/raccefyn.258"], "10.18257/raccefyn.258"),
        (["10.1093/femsle/fnad098/"], "10.1093/femsle/fnad098"),
        (["10.1590/S0120-41572010000100002."], "10.1590/s0120-41572010000100002"),
        (["10.1016/0002-9149(83)90004-X"], "10.1016/0002-9149(83)90004-x"),
        (["(10.1016/j.x.2020.01.001)"], "10.1016/j.x.2020.01.001"),
        (["sin doi", "texto con 10.1007/s00134-020-06022-5 al final"], "10.1007/s00134-020-06022-5"),
        (["", None, "http://example.org/x"], None),
    ],
)
def test_find_doi(texts, doi):
    # Cases taken from real CvLAC pages: URL forms, junk before the DOI, trailing punctuation.
    assert find_doi(*texts) == doi


def test_labeled_book_year_from_presentation_date():
    # Labeled formats: the free text holds the title, which may name other years ('al año 2050').
    frag = (
        "<tr><td><li><b>Producción bibliográfica - Libro - Libros de divulgación y/o Compilación de divulgación </b>"
        "</li></td></tr>"
        "<tr><td><blockquote><i>Nombre del libro: </i>Plan prospectivo al año 2050 (Ley 1333 de 2009),&nbsp; "
        "<i>Fecha de presentaci&oacute;n: </i>2024 -  Julio,&nbsp; <i>Isbn: </i>978-628-96104-0-6,&nbsp; "
        "<i>Editorial: </i>Editorial de prueba,&nbsp;</blockquote></td></tr>"
    )
    ((hdr, endorsed, bq),) = items(frag)
    owner = {"cod_rh": COD, "name": "ANA MARIA PEREZ GOMEZ", "citation_name": None}
    w = work_from_item("Libros de divulgación", hdr, endorsed, bq, owner, 1)
    assert w["title"] == "Plan prospectivo al año 2050 (Ley 1333 de 2009)"
    assert w["year_published"] == 2024


def test_section_coauthors_and_contract(data):
    (c,) = data["sections"]["Consultorías"]
    assert c["title"] == "Diagnóstico sintético de calidad de datos, para pruebas"
    assert [(a["full_name"], a["id"]) for a in c["authors"]] == [
        ("ANA MARIA PEREZ GOMEZ", data["cod_rh"]),
        ("LUIS FERNANDO TORRES VEGA", None),
    ]
    assert c["country"] == "Colombia" and c["year"] == 2020
    assert c["duration"] == {"value": 6, "unit": "meses"}
    assert c["identifiers"] == [{"source": "contract/registration", "id": "CT-0042 de 2020"}]
    assert c["fields"]["contrato/registro"] == "CT-0042 de 2020"  # no longer runs into '. En: Colombia, ,2020'


def test_section_course(data):
    (c,) = data["sections"]["Cursos de corta duración"]
    assert c["title"] == "Curso sintético de análisis de datos"
    assert c["purpose"] == "Formar analistas de prueba"
    assert c["institution"] == "UNIVERSIDAD DE ANTIOQUIA" and c["role"] == "Docente"
    assert c["duration"] == {"value": 16, "unit": "semanas"}


def test_section_sequence_links_and_accession(data):
    (s,) = data["sections"]["Nueva secuencia genética"]
    assert s["title"] == "Organismo sintético gen X, partial cds"
    assert s["date"] == "2016-06" and s["city"] == "MEDELLÍN" and s["database"] == "GenBank"
    assert [x["url"] for x in s["links"]] == ["https://www.ncbi.nlm.nih.gov/nuccore/MG000001.1"]
    assert {"source": "accession", "id": "MG000001"} in s["identifiers"]


def test_section_patent(data):
    (p,) = data["sections"]["Patentes"]
    assert p["title"] == "MÉTODO SINTÉTICO DE PRUEBA"
    assert p["date"] == "2020-12-07" and p["country"] == "Colombia"
    assert p["holder"] == "UNIVERSIDAD DE ANTIOQUIA"
    assert p["identifiers"] == [{"source": "patent", "id": "NC2020/0000001"}, {"source": "gazette", "id": "39514"}]
