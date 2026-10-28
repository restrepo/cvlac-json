#!/usr/bin/env python3
"""Resolve CvLAC experience institutions to ROR and add them as affiliations of the CV owner's works.

    from cvlac_json import ror; ror.enrich(data)        # data = cvlac_json.parser.build(...)

For each experience entry: parse the period into start_year / end_year (open periods such as
'Febrero de 1995 de' or '... de Actual' end in the current year and get open_end: true) and look the institution up in
the ROR API (https://api.ror.org/v2/organizations?affiliation=...). A ROR record is accepted only
when one of its names, aliases, labels or acronyms equals the CvLAC name (accents and case
ignored), or one name is a word prefix of the other (e.g. 'UNIVERSIDAD NACIONAL DE COLOMBIA SEDE
MANIZALES' -> Universidad Nacional de Colombia); ROR's own 'chosen' flag is not trusted. Units such
as 'FACULTAD DE ...' usually get no ROR. Answers are cached in ~/.cache/cvlac-json/ror.json.

Then every work gets, on the owner's author entry, one affiliation per institution (merged by ROR
id, else by name) whose experience period contains the work's year_published, in the ImpactU
affiliation shape: {id, name, types, external_ids, addresses, years, cvlac}.
Standard library only.
"""

import datetime as dt
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request

ROR_API = "https://api.ror.org/v2/organizations?affiliation={}"
CACHE = os.path.expanduser("~/.cache/cvlac-json/ror.json")
YEAR = r"(?<!\d)(1[89]\d\d|20\d\d)(?!\d)"


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def period_years(period, now=None):
    """'Noviembre de 1995 Marzo de 2001' -> (1995, 2001); 'Febrero de 1995 de' / '... de Actual' -> (1995, now)."""
    now = now or dt.date.today().year
    ys = [int(y) for y in re.findall(YEAR, period or "")]
    if not ys:
        return None, None
    return ys[0], (ys[1] if len(ys) > 1 else now)


def _load_cache():
    try:
        return json.load(open(CACHE, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_cache(c):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as fh:
        json.dump(c, fh, ensure_ascii=False, indent=1)


def _names(org):
    return [n["value"] for n in org.get("names", [])]


def _display(org):
    return next((n["value"] for n in org.get("names", []) if "ror_display" in n.get("types", [])), _names(org)[0])


def _accept(name, items):
    """Pick the ROR item whose names match the CvLAC name; return (org, how) or (None, None)."""
    nn = norm(name)
    best = None
    for it in items:
        org = it["organization"]
        for v in _names(org):
            nv = norm(v)
            if not nv:
                continue
            how = (
                "name"
                if nv == nn
                else (
                    "prefix"
                    if len(nv) >= 8 and (nn.startswith(nv + " ") or nv.startswith(nn + " ")) and it["score"] >= 0.9
                    else None
                )
            )
            if how:
                co = any(loc.get("geonames_details", {}).get("country_code") == "CO" for loc in org.get("locations", []))
                key = (how == "name", co, it["score"])
                if best is None or key > best[0]:
                    best = (key, org, how)
                break
    return (best[1], best[2]) if best else (None, None)


def lookup(name, cache):
    """CvLAC institution name -> cached ROR summary dict or None."""
    k = norm(name)
    if not k:
        return None
    if k in cache:
        return cache[k]
    req = urllib.request.Request(ROR_API.format(urllib.parse.quote(name)), headers={"User-Agent": "cvlac-json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        items = json.load(r).get("items", [])
    time.sleep(0.3)
    org, how = _accept(name, items)
    if org is None:
        cache[k] = None
        return None
    loc = (org.get("locations") or [{}])[0].get("geonames_details", {})
    ext = [{"provenance": "ror", "source": "ror", "id": org["id"]}]
    for e in org.get("external_ids", []):
        v = e.get("preferred") or (e.get("all") or [None])[0]
        if v:
            ext.append({"provenance": "ror", "source": e["type"], "id": v})
    cache[k] = {
        "id": org["id"].rsplit("/", 1)[-1],
        "name": _display(org),
        "match": how,
        "types": [{"source": "ror", "type": t} for t in org.get("types", [])],
        "external_ids": ext,
        "addresses": [{"city": loc.get("name"), "country": loc.get("country_name"), "country_code": loc.get("country_code")}]
        if loc
        else [],
    }
    return cache[k]


def thesis_affiliations(data, cache, ror=True, lookup=lookup):
    """Supervised theses: the institution after the title goes, with its ROR id, to the advisor and the student(s)."""
    n = 0
    for _title, items in data.get("sections", {}).items():
        for it in items:
            inst = it.get("institution")
            if not (isinstance(inst, dict) and inst.get("name") and it.get("authors")):
                continue
            r = None
            if ror:
                try:
                    r = lookup(inst["name"], cache)
                except OSError:
                    r = None
            inst.update(
                {"id": r["id"] if r else None, "ror_name": r["name"] if r else None, "ror_match": r["match"] if r else None}
            )
            aff = {
                "id": r["id"] if r else "",
                "name": r["name"] if r else inst["name"],
                "types": r["types"] if r else [],
                "external_ids": r["external_ids"] if r else [],
                "addresses": r["addresses"] if r else [],
                "years": [it["year"]] if it.get("year") else [],
                "cvlac": {"provenance": "cvlac thesis", "names": [inst["name"]], "ror_match": r["match"] if r else None},
            }
            for a in it["authors"]:
                if a.get("type") in ("advisor", "student"):
                    a["affiliations"] = [json.loads(json.dumps(aff))]
            n += 1
    return n


def enrich(data, ror=True, progress=None):
    """Add start_year/end_year/ror to data['experience'] and owner affiliations to data['works']."""
    cache = _load_cache() if ror else {}
    progress = progress or (lambda stage, done=None, total=None: None)
    names = {norm(e.get("institution")) for e in data.get("experience", []) if e.get("institution")}
    names |= {
        norm(it["institution"]["name"])
        for v in data.get("sections", {}).values()
        for it in v
        if isinstance(it.get("institution"), dict) and it["institution"].get("name")
    }
    names.discard("")
    seen = set()

    def counted_lookup(name, cache):
        seen.add(norm(name))
        progress("ROR", len(seen), len(names))
        return lookup(name, cache)

    if ror:
        progress("ROR", 0, len(names))
    exp = data.get("experience", [])
    errors = 0
    for e in exp:
        e["start_year"], e["end_year"] = period_years(e.get("period"))
        e["open_end"] = bool(e["start_year"]) and len(re.findall(YEAR, e.get("period") or "")) < 2
        r = None
        if ror and e.get("institution"):
            try:
                r = counted_lookup(e["institution"], cache)
            except OSError:
                errors += 1
        e["ror"] = {"id": r["id"], "name": r["name"], "match": r["match"]} if r else None
    if ror:
        _save_cache(cache)

    cod = data["cod_rh"]
    n_aff = 0
    for w in data.get("works", []):
        y = w.get("year_published")
        if not y:
            continue
        affs = {}
        for e in exp:
            if not e["start_year"] or not (e["start_year"] <= y <= e["end_year"]):
                continue
            r = cache.get(norm(e["institution"])) if e["ror"] else None
            key = r["id"] if r else norm(e["institution"])
            a = affs.get(key)
            if a is None:
                a = affs[key] = {
                    "id": r["id"] if r else "",
                    "name": r["name"] if r else e["institution"],
                    "types": r["types"] if r else [],
                    "external_ids": r["external_ids"] if r else [],
                    "addresses": r["addresses"] if r else [],
                    "years": [],
                    "cvlac": {
                        "provenance": "cvlac experience",
                        "names": [],
                        "periods": [],
                        "ror_match": r["match"] if r else None,
                    },
                }
            a["years"] = sorted(set(a["years"]) | set(range(e["start_year"], e["end_year"] + 1)))
            if e["institution"] not in a["cvlac"]["names"]:
                a["cvlac"]["names"].append(e["institution"])
            a["cvlac"]["periods"].append({"period": e.get("period"), "dedication": e.get("dedication")})
        for au in w.get("authors", []):
            if au.get("id") == cod:
                au["affiliations"] = list(affs.values())
                n_aff += bool(affs)
    data["counts"]["works_with_affiliation"] = n_aff
    n_th = thesis_affiliations(data, cache if ror else {}, ror, lookup=counted_lookup)
    if ror:
        _save_cache(cache)
    found = sum(1 for e in exp if e.get("ror"))
    data["affiliations_from_experience"] = {
        "ror_api": "https://api.ror.org/v2" if ror else None,
        "experience_with_ror": found,
        "experience": len(exp),
        "works_with_affiliation": n_aff,
        "theses_with_affiliation": n_th,
        "lookup_errors": errors,
    }
    return data
