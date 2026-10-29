"""Add SIIU project codes (UdeA's research information system, via apis.colav.co) to CvLAC projects.

The owner's SIIU projects are found by the identity document in their Scienti author record
(that number is used only for the query; it is never printed or stored). A CvLAC project matches a
SIIU project when the normalized title equals its full or short name (short names need
MIN_TITLE characters and MIN_WORDS words) and the CvLAC start year is compatible: inside the SIIU
span (registration year, stage start years and approval year to the last stage end, or registration
plus duration), with YEAR_SLACK years of slack on each side. When several SIIU projects share the
title (resubmissions), executed projects come before proposals (rejected, in evaluation...), then the
closest start year wins; the others go to "also".
"""

import re

from .scienti import get, long_enough, norm, year_of

YEAR_SLACK = 1
RUN = {"aprobado", "en_ejecucion", "atrasado", "finalizado", "liquidado"}  # states of executed projects


def owner_document(key, cod_rh, model_year, institution):
    """Identity document number from the Scienti author record, or None."""
    try:
        recs = get("/scienti/author", key, COD_RH=cod_rh, model_year=model_year, institution=institution)
    except RuntimeError:
        return None
    rec = recs[0] if isinstance(recs, list) and recs else recs if isinstance(recs, dict) else {}
    doc = re.sub(r"\D", "", str(rec.get("NRO_DOCUMENTO_IDENT") or ""))
    return doc or None


def span(p):
    """(first, last) years of a SIIU project, from its registration, approval and stages."""
    starts = [year_of(p.get("FECHA_REGISTRO"))] + [year_of(s.get("INICIO_VIGENCIA")) for s in p.get("project_stage") or []]
    starts = [y for y in starts if y]
    ends = [year_of(s.get("FIN_VIGENCIA")) for s in p.get("project_stage") or []] + [year_of(p.get("FECHA_APROBACION_RECHAZO"))]
    if starts and p.get("DURACION"):
        ends.append(min(starts) + (int(p["DURACION"]) - 1) // 12)
    ends = [y for y in ends + starts if y]
    return (min(starts), max(ends)) if starts else (None, None)


def distance(year, sp):
    """0 inside the span, else the years outside it."""
    lo, hi = sp
    return 0 if lo <= year <= hi else (lo - year if year < lo else year - hi)


def match_projects(projects, records):
    """Tag projects[] with the SIIU code of the same-title, compatible-year SIIU project. Returns the count."""
    index = {}
    for r in records:
        names = {norm(r.get("NOMBRE_COMPLETO"))}
        if long_enough(norm(r.get("NOMBRE_CORTO"))):
            names.add(norm(r.get("NOMBRE_CORTO")))
        for t in names - {""}:
            index.setdefault(t, []).append(r)
    used, n = set(), 0
    for p in projects:
        t, y = norm(p.get("title")), (p.get("start") or {}).get("year")
        if not t or not y:
            continue
        cands = []
        for r in index.get(t, []):
            sp = span(r)
            if sp[0] and distance(y, sp) <= YEAR_SLACK:
                cands.append((distance(y, sp), r.get("ESTADO") not in RUN, abs(y - sp[0]), r["CODIGO"] in used, r, sp))
        if not cands:
            continue
        cands.sort(key=lambda c: c[:4])
        r, sp = cands[0][4], cands[0][5]
        p["siiu"] = {
            "id": r["CODIGO"],
            "by": "title",
            "evidence": ["year"],
            "shared": r["CODIGO"] in used,
            "siiu_title": r.get("NOMBRE_COMPLETO"),
            "siiu_years": list(sp),
            "status": r.get("ESTADO"),
            "also": [c[4]["CODIGO"] for c in cands[1:]],
        }
        p.setdefault("external_ids", []).append({"provenance": "siiu", "source": "siiu", "id": r["CODIGO"]})
        used.add(r["CODIGO"])
        n += 1
    return n


def enrich(data, cod_rh, model_year, institution, key, log=print, progress=None):
    """Fetch the owner's SIIU projects and tag the matching CvLAC projects."""
    (progress or (lambda stage, done=None, total=None: None))("SIIU projects")
    doc = owner_document(key, cod_rh, model_year, institution)
    if not doc:
        log("siiu: no identity document in the Scienti author record; skipped")
        return False
    try:
        records = get("/siiu/project", key, participant_id=doc)
    except RuntimeError as e:
        log(f"siiu: skipped ({e})")
        return False
    records = [r for r in records if isinstance(r, dict) and r.get("CODIGO")] if isinstance(records, list) else []
    n = match_projects(data["projects"], records)
    found = {p["siiu"]["id"] for p in data["projects"] if p.get("siiu")}
    for p in data["projects"]:
        found.update((p.get("siiu") or {}).get("also") or [])
    data["siiu"] = {
        "source": "apis.colav.co",
        "projects": len(records),
        "projects_matched": n,
        "not_on_page": sorted(r["CODIGO"] for r in records if r["CODIGO"] not in found),
        "rules": "exact normalized title (full name, or short name of >= 25 chars and 4 words) and the CvLAC start "
        f"year inside the SIIU span (registration/stages/approval) with {YEAR_SLACK} year of slack; "
        "executed projects first, then the closest start year",
    }
    log(f"siiu: projects {n}/{len(records)} matched")
    return True
