from cvlac_json import scienti, siiu


def _siiu(code, name, reg, stages=(), short=None, state="finalizado", duration=24):
    return {
        "CODIGO": code,
        "NOMBRE_COMPLETO": name,
        "NOMBRE_CORTO": short,
        "FECHA_REGISTRO": f"{reg}-03-26 17:31:45",
        "FECHA_APROBACION_RECHAZO": None,
        "DURACION": duration,
        "ESTADO": state,
        "project_stage": [{"INICIO_VIGENCIA": f"{a}-01-01", "FIN_VIGENCIA": f"{b}-12-31"} for a, b in stages],
    }


TITLE = "Fenomenología sintética de modelos de prueba para parsers"


def test_span_and_distance():
    r = _siiu("2014-1", TITLE, 2014, stages=[(2014, 2016)])
    assert siiu.span(r) == (2014, 2016)
    assert siiu.distance(2015, (2014, 2016)) == 0 and siiu.distance(2012, (2014, 2016)) == 2


def test_exact_title_and_compatible_year():
    projects = [{"title": TITLE.upper() + "!", "start": {"year": 2013}}, {"title": TITLE, "start": {"year": 2010}}]
    assert siiu.match_projects(projects, [_siiu("2014-1", TITLE, 2014, stages=[(2014, 2015)])]) == 1
    assert projects[0]["siiu"]["id"] == "2014-1"  # one year before registration is within the slack
    assert projects[0]["external_ids"] == [{"provenance": "siiu", "source": "siiu", "id": "2014-1"}]
    assert "siiu" not in projects[1]  # 2010 is too far


def test_resubmission_goes_to_also():
    recs = [_siiu("2015-9", TITLE, 2015, state="validtec"), _siiu("2014-1", TITLE, 2014, stages=[(2014, 2015)])]
    projects = [{"title": TITLE, "start": {"year": 2014}}]
    siiu.match_projects(projects, recs)
    assert projects[0]["siiu"]["id"] == "2014-1" and projects[0]["siiu"]["also"] == ["2015-9"]


def test_executed_project_wins_over_rejected_proposal():
    recs = [_siiu("2021-2", TITLE, 2021, state="rechazado", duration=6), _siiu("2020-1", TITLE, 2020, stages=[(2020, 2024)])]
    projects = [{"title": TITLE, "start": {"year": 2021}}]
    siiu.match_projects(projects, recs)
    assert projects[0]["siiu"]["id"] == "2020-1" and projects[0]["siiu"]["also"] == ["2021-2"]


def test_short_name_needs_length():
    recs = [_siiu("2018-5", "Otro nombre completo distinto del proyecto", 2018, short="Materia oscura")]
    projects = [{"title": "Materia oscura", "start": {"year": 2018}}]
    assert siiu.match_projects(projects, recs) == 0


def test_enrich_uses_document_without_storing_it(monkeypatch):
    seen = {}

    def fake_get(path, key, **params):
        if path == "/scienti/author":
            return [{"NRO_DOCUMENTO_IDENT": "12.345.678"}]
        seen.update(params)
        return [_siiu("2014-1", TITLE, 2014)]

    monkeypatch.setattr(siiu, "get", fake_get)
    data = {"projects": [{"title": TITLE, "start": {"year": 2014}}]}
    assert siiu.enrich(data, "0000000001", "2024", "udea", "k", log=lambda m: None)
    assert seen == {"participant_id": "12345678"}
    assert data["siiu"]["projects_matched"] == 1 and data["siiu"]["not_on_page"] == []
    assert "12345678" not in repr(data)


def test_enrich_without_document_is_skipped(monkeypatch):
    monkeypatch.setattr(siiu, "get", lambda path, key, **p: [{}])
    msgs = []
    assert siiu.enrich({"projects": []}, "0000000001", "2024", "udea", "k", log=msgs.append) is False
    assert "skipped" in msgs[0]
    assert scienti.norm(TITLE)  # same normalization as Scienti
