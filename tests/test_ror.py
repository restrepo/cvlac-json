from cvlac_json import extract, ror

UDEA = {
    "id": "https://ror.org/03bp5hc83",
    "names": [{"value": "Universidad de Antioquia", "types": ["ror_display", "label"]}, {"value": "UdeA", "types": ["acronym"]}],
    "types": ["education"],
    "external_ids": [{"type": "grid", "preferred": "grid.412881.6", "all": ["grid.412881.6"]}],
    "locations": [{"geonames_details": {"name": "Medellín", "country_name": "Colombia", "country_code": "CO"}}],
}
UNAL = {
    "id": "https://ror.org/059yx9a68",
    "names": [{"value": "Universidad Nacional de Colombia", "types": ["ror_display"]}],
    "types": ["education"],
    "external_ids": [],
    "locations": [{"geonames_details": {"name": "Bogotá", "country_name": "Colombia", "country_code": "CO"}}],
}
OTHER = {
    "id": "https://ror.org/000000000",
    "names": [{"value": "Universidad de Jaén", "types": ["ror_display"]}],
    "types": ["education"],
    "external_ids": [],
    "locations": [],
}


def test_period_years():
    assert ror.period_years("Noviembre de 1995 Marzo de 2001") == (1995, 2001)
    assert ror.period_years("Febrero de 1995 de", now=2030) == (1995, 2030)
    assert ror.period_years("Marzo de 2006 de Actual", now=2030) == (2006, 2030)
    assert ror.period_years("") == (None, None)


def test_accept_exact_name_not_rors_chosen_flag():
    items = [{"chosen": True, "score": 1.0, "organization": OTHER}, {"chosen": False, "score": 1.0, "organization": UDEA}]
    org, how = ror._accept("UNIVERSIDAD DE ANTIOQUIA", items)
    assert org is UDEA and how == "name"


def test_accept_prefix_needs_high_score():
    items = [{"chosen": True, "score": 1.0, "organization": UNAL}]
    org, how = ror._accept("UNIVERSIDAD NACIONAL DE COLOMBIA SEDE MEDELLÍN", items)
    assert org is UNAL and how == "prefix"
    low = [{"chosen": True, "score": 0.5, "organization": UNAL}]
    assert ror._accept("UNIVERSIDAD NACIONAL DE COLOMBIA SEDE MEDELLÍN", low) == (None, None)


def test_no_match_for_units():
    assert ror._accept("FACULTAD DE INGENIERIA", [{"chosen": True, "score": 0.8, "organization": OTHER}]) == (None, None)


def test_enrich_with_mocked_ror(page, monkeypatch):
    answers = {
        "universidad de antioquia": [{"chosen": False, "score": 1.0, "organization": UDEA}],
        "universidad nacional de colombia sede medellin": [{"chosen": True, "score": 1.0, "organization": UNAL}],
    }

    def fake_lookup(name, cache):
        k = ror.norm(name)
        if k not in cache:
            org, how = ror._accept(name, answers.get(k, []))
            cache[k] = (
                None
                if org is None
                else {
                    "id": org["id"].rsplit("/", 1)[-1],
                    "name": ror._display(org),
                    "match": how,
                    "types": [{"source": "ror", "type": t} for t in org["types"]],
                    "external_ids": [{"provenance": "ror", "source": "ror", "id": org["id"]}],
                    "addresses": [],
                }
            )
        return cache[k]

    monkeypatch.setattr(ror, "lookup", fake_lookup)
    data = extract("1", html=page, scienti="off", ror=True, log=lambda m: None)
    assert [e["ror"]["id"] for e in data["experience"]] == ["03bp5hc83", "059yx9a68"]
    aff = data["works"][0]["authors"][0]["affiliations"][0]
    assert aff["id"] == "03bp5hc83" and aff["name"] == "Universidad de Antioquia"
    thesis = data["sections"]["Trabajos dirigidos/tutorías"][0]
    assert thesis["institution"]["id"] == "03bp5hc83"
    student = next(a for a in thesis["authors"] if a["type"] == "student")
    assert student["affiliations"][0]["id"] == "03bp5hc83"
    co = next(a for a in thesis["authors"] if a["type"] == "co-advisor")
    assert co["affiliations"] == []
