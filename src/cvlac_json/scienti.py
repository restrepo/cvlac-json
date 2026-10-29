"""Add Scienti identifiers (apis.colav.co) to a CvLAC JSON built by cvlac_json.py.

Ids follow ImpactU: products COD_RH-COD_PRODUCTO, projects COD_RH-COD_PROYECTO,
events COD_RH-COD_EVENTO, networks COD_RH-COD_RED.
A CvLAC entry matches a Scienti record by DOI, or by an exact (normalized) title of
at least MIN_TITLE characters and MIN_WORDS words plus one more piece of evidence:
same year, ISSN, ISBN, journal/book/event name, or patent number. Scienti truncates long
titles, so a title that is a prefix of the other (both >= MIN_PREFIX characters) also counts
("title prefix"), but only with the same year.
The API key is the one passed to enrich(key=...) (cvlac_json.py --apikey), else $COLAV_APIKEY,
else ~/.config/colav/apikey; it is never printed.
"""

import copy
import json
import os
import pathlib
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://apis.colav.co"
KEY_FILE = pathlib.Path.home() / ".config" / "colav" / "apikey"
INSTITUTIONS = ["udea", "univalle", "uec", "unaula"]
MIN_TITLE, MIN_WORDS, MIN_PREFIX = 25, 4, 40


def apikey(explicit=None):
    """--apikey value, else $COLAV_APIKEY, else ~/.config/colav/apikey."""
    key = (
        (explicit or "").strip() or os.environ.get("COLAV_APIKEY") or (KEY_FILE.read_text().strip() if KEY_FILE.exists() else "")
    )
    return key or None


def get(path, key, **params):
    url = BASE + path + "?" + urllib.parse.urlencode({"apikey": key, **params})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "cvlac-json"}), timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403, 404):
                raise RuntimeError(f"HTTP {e.code} for {path}") from None
            err = f"HTTP {e.code}"
        except Exception as e:  # network errors: message may contain the URL, so redact the key
            err = str(e).replace(key, "***")
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{path}: {err}")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def ndoi(s):
    s = (s or "").strip().lower()
    s = re.sub(r"^(https?://)?(dx\.)?doi\.org/|^doi:\s*", "", s)
    return s if re.match(r"10\.\d{4,9}/\S+", s) else None


def digits(s):
    return re.sub(r"[^\dx]", "", (s or "").lower())


def long_enough(t):
    return len(t) >= MIN_TITLE and len(t.split()) >= MIN_WORDS


def year_of(s):
    m = re.search(r"(1[89]\d\d|20\d\d)", str(s or ""))
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------- Scienti records
def detail(p, kind):
    for d in p.get("details") or []:
        if d.get(kind):
            return d[kind][0]
    return {}


def root_type(p):
    t = (p.get("product_type") or [{}])[0]
    while t.get("product_type"):
        t = t["product_type"][0]
    return t.get("TXT_NME_TIPO_PRODUCTO")


def index_products(products, patents):
    pat_no = {str(x.get("COD_PRODUCTO")): x.get("TXT_NRO_PATENTE") for x in patents if x.get("COD_PRODUCTO")}
    out = []
    for p in products:
        art, ch, bk, mem = detail(p, "article"), detail(p, "book_chapter"), detail(p, "book"), detail(p, "memory_chapter")
        jr = (art.get("journal") or [{}])[0]
        bo = (ch.get("book_other") or [{}])[0]
        issn = {digits(x) for x in (jr.get("TXT_ISSN_SEP"), jr.get("TXT_ISSN_REF_SEP")) if x}
        isbn = {digits(x) for x in (bk.get("TXT_ISBN"), bo.get("TXT_ISBN")) if x}
        venues = {
            norm(x)
            for x in (jr.get("TXT_NME_REVISTA"), bo.get("TXT_NME_LIBRO"), mem.get("TXT_NME_EVENTO"))
            if x and len(norm(x)) >= 8
        }
        cp = str(p["COD_PRODUCTO"])
        out.append(
            {
                "id": f"{p['COD_RH']}-{cp}",
                "title": norm(p.get("TXT_NME_PROD")),
                "raw_title": p.get("TXT_NME_PROD"),
                "year": p.get("NRO_ANO_PRESENTA"),
                "doi": ndoi(p.get("TXT_DOI")),
                "issn": issn - {""},
                "isbn": isbn - {""},
                "venues": venues,
                "patent": digits(pat_no.get(cp)) or None,
                "type": root_type(p),
                "code": p.get("COD_TIPO_PRODUCTO"),
            }
        )
    return out


def evidence(c, year, issn, isbn, venue, text):
    ev = []
    if year and c["year"] and int(year) == int(c["year"]):
        ev.append("year")
    if issn & c["issn"]:
        ev.append("issn")
    if isbn & c["isbn"]:
        ev.append("isbn")
    if venue and any(venue == v or (len(venue) >= 8 and (venue in v or v in venue)) for v in c["venues"]):
        ev.append("venue")
    if c.get("patent") and len(c["patent"]) >= 6 and c["patent"] in digits(text):
        ev.append("patent number")
    return ev


def best(cands, used):
    """Pick the strongest candidate, preferring records not yet given to another CvLAC entry."""
    if not cands:
        return None
    cands.sort(key=lambda x: (x[0]["id"] in used, -x[1]))
    return cands[0]


def match_entry(index, used, title=None, text="", year=None, doi=None, issn=(), isbn=(), venue=None):
    issn, isbn = {digits(x) for x in issn if x}, {digits(x) for x in isbn if x}
    venue = norm(venue) if venue else None
    d = ndoi(doi)
    if d:
        c = best([(c, 10 + len(evidence(c, year, issn, isbn, venue, text))) for c in index if c["doi"] == d], used)
        if c:
            return c[0], "doi", evidence(c[0], year, issn, isbn, venue, text)
    t, nt = norm(title), norm(text)
    cands = []
    for c in index:
        if not long_enough(c["title"]):
            continue
        ev = None
        if (t and t == c["title"]) or (not t and f" {c['title']} " in f" {nt} "):
            ev, by = evidence(c, year, issn, isbn, venue, text), "title"
        elif (
            t
            and min(len(t), len(c["title"])) >= MIN_PREFIX
            and (t.startswith(c["title"] + " ") or c["title"].startswith(t + " "))
        ):
            ev, by = evidence(c, year, issn, isbn, venue, text), "title prefix"  # Scienti truncates long titles
            if "year" not in ev:
                ev = None
        if ev:
            cands.append((c, len(ev) + (by == "title"), by))
    c = best(cands, used)
    return (c[0], c[2], evidence(c[0], year, issn, isbn, venue, text)) if c else (None, None, None)


def tag(entry_list, key_of, records, rec_id, rec_title, rec_year, min_title=MIN_TITLE):
    """Match projects / events / networks by exact normalized name and the same year."""
    used, n = set(), 0
    for e in entry_list:
        t, y = norm(key_of(e)[0]), key_of(e)[1]
        if not t:
            continue
        cands = [
            r
            for r in records
            if norm(rec_title(r)) == t
            and (len(t) >= min_title or y)
            and (y is None or rec_year(r) is None or int(rec_year(r)) == int(y))
        ]
        if len(t) < min_title:  # short names need the year as extra evidence
            cands = [r for r in cands if y and rec_year(r) and int(rec_year(r)) == int(y)]
        if not cands:
            continue
        r = sorted(cands, key=lambda r: rec_id(r) in used)[0]
        e["scienti"] = {
            "id": rec_id(r),
            "by": "title",
            "evidence": ["year"] if y and rec_year(r) else [],
            "shared": rec_id(r) in used,
            "scienti_title": rec_title(r),
            "scienti_year": rec_year(r),
        }
        used.add(rec_id(r))
        n += 1
    return n


# ---------------------------------------------------------------- Scienti-only records -> their CvLAC section
WORK_SECTION = {
    "Artículo": "Artículos",
    "Otro artículo publicado": "Textos en publicaciones no científicas",
    "Trabajos en eventos (Capítulos de memoria)": "Trabajos en eventos",
    "Otra producción bibliográfica": "Otra producción blibliográfica",
}


def type_chain(p):
    """Scienti product_type (leaf first, nested to the root) -> [(name, code), ...] root first."""
    out, t = [], (p.get("product_type") or [{}])[0]
    while t:
        out.append((t.get("TXT_NME_TIPO_PRODUCTO"), t.get("COD_TIPO_PRODUCTO")))
        t = (t.get("product_type") or [None])[0]
    return out[::-1]


def scienti_authors(p, owner_id, owner_name):
    """Ordered authors from re_author_others (names only); COD_RH_OTRO '0' is the CV owner."""
    rows = sorted(p.get("re_author_others") or [], key=lambda r: r.get("NRO_IMPORTANCIA") or 0)
    out = []
    for r in rows:
        for a in r.get("author_others") or []:
            name = a.get("TXT_TOTAL_NAMES") or " ".join(
                x for x in (a.get("TXT_NME_RH"), a.get("TXT_PRIM_APELL"), a.get("TXT_SEG_APELL")) if x
            )
            own = str(a.get("COD_RH_OTRO")) == "0"
            cid = owner_id if own else (r.get("COD_RH_COAUTOR") or "")
            out.append(
                {
                    "full_name": name,
                    "id": cid,
                    "external_ids": [{"provenance": "scienti", "source": "scienti", "id": cid}] if cid else [],
                    "affiliations": [],
                }
            )
    return out or [
        {
            "full_name": owner_name,
            "id": owner_id,
            "external_ids": [{"provenance": "scienti", "source": "scienti", "id": owner_id}],
            "affiliations": [],
        }
    ]


def work_from_scienti(p, pid, chain, section, owner_id, owner_name):
    art, ch, bk, mem = detail(p, "article"), detail(p, "book_chapter"), detail(p, "book"), detail(p, "memory_chapter")
    jr, bo = (art.get("journal") or [{}])[0], (ch.get("book_other") or [{}])[0]
    ed = (bk.get("editorial") or [{}])[0]
    doi = ndoi(p.get("TXT_DOI"))
    ext = [{"provenance": "scienti", "source": "scienti", "id": pid}]
    if doi:
        ext.insert(0, {"provenance": "scienti", "source": "doi", "id": doi})
    if bk.get("TXT_ISBN"):
        ext.append({"provenance": "scienti", "source": "isbn", "id": bk["TXT_ISBN"]})
    if jr:
        src = {
            "name": jr.get("TXT_NME_REVISTA"),
            "external_ids": [{"source": "issn", "id": x} for x in (jr.get("TXT_ISSN_SEP"), jr.get("TXT_ISSN_REF_SEP")) if x],
        }
    elif bo:
        src = {
            "name": bo.get("TXT_NME_LIBRO"),
            "external_ids": [{"source": "isbn", "id": bo["TXT_ISBN"]}] if bo.get("TXT_ISBN") else [],
        }
    elif mem:
        src = {"name": (mem.get("TXT_NME_EVENTO") or "").strip() or None, "external_ids": []}
    else:
        src = {"name": None, "external_ids": []}
    if ed.get("TXT_NME_EDITORIAL"):
        src["publisher"] = {"name": ed["TXT_NME_EDITORIAL"]}
    d = art or ch
    authors = scienti_authors(p, owner_id, owner_name)
    kw = [
        k["TXT_NME_PALABRA_CLAVE"]
        for x in p.get("details") or []
        for k in x.get("keywords") or []
        if k.get("TXT_NME_PALABRA_CLAVE")
    ]
    return {
        "id": f"scienti:{pid}",
        "title": p.get("TXT_NME_PROD"),
        "titles": [
            {
                "title": p.get("TXT_NME_PROD"),
                "lang": (p.get("SGL_IDIOMA") or "").lower(),
                "source": "scienti",
                "provenance": "scienti",
            }
        ],
        "types": [
            {"provenance": "scienti", "source": "scienti", "type": n, "level": i, "code": c} for i, (n, c) in enumerate(chain)
        ],
        "product_types": [{"name": chain[-1][0], "source": "scienti"}],
        "authors": authors,
        "authors_count": len(authors),
        "year_published": p.get("NRO_ANO_PRESENTA"),
        "doi": f"https://doi.org/{doi}" if doi else None,
        "external_ids": ext,
        "external_urls": [{"provenance": "scienti", "source": "scienti", "url": p["TXT_WEB_PRODUCTO"]}]
        if p.get("TXT_WEB_PRODUCTO")
        else [],
        "source": src,
        "bibliographic_info": {
            k: v
            for k, v in {
                "volume": d.get("TXT_VOLUMEN_REVISTA"),
                "issue": d.get("TXT_FASCICULO_REVISTA"),
                "start_page": d.get("TXT_PAGINA_INICIAL"),
                "end_page": d.get("TXT_PAGINA_FINAL"),
                "pages": bk.get("TXT_NRO_PAGINAS"),
            }.items()
            if v
        },
        "keywords": kw,
        "origin": "scienti",
        "cvlac": {
            "section": section,
            "scienti": {
                "id": pid,
                "by": "not on the CvLAC page",
                "scienti_title": p.get("TXT_NME_PROD"),
                "scienti_year": p.get("NRO_ANO_PRESENTA"),
            },
        },
    }


def item_from_scienti(p, pid, chain):
    tech, th, mem = detail(p, "technical"), detail(p, "oriented_thesis"), detail(p, "memory_chapter")
    inst = (th.get("institution") or [{}])[0]
    fields = {
        k: v
        for k, v in {
            "Finalidad": tech.get("TXT_FINALIDAD"),
            "Persona(s) orientada(s)": th.get("TXT_NME_ORIENTADOS"),
            "Institución": inst.get("NME_INST"),
            "Evento": (mem.get("TXT_NME_EVENTO") or "").strip() or None,
            "Resumen": p.get("TXT_RESUMEN_PROD"),
            "Observaciones": p.get("TXT_OBSERV_PROD"),
        }.items()
        if v
    }
    year = p.get("NRO_ANO_PRESENTA")
    return {
        "type": " - ".join(n for n, _ in chain),
        "title": p.get("TXT_NME_PROD"),
        "year": year,
        "text": ", ".join(str(x) for x in (p.get("TXT_NME_PROD"), year) if x),
        "fields": fields,
        "origin": "scienti",
        "scienti": {"id": pid, "by": "not on the CvLAC page", "scienti_title": p.get("TXT_NME_PROD"), "scienti_year": year},
    }


def item_section(data, chain):
    """CvLAC section whose items share the Scienti type path (longest common prefix), else a section named after it."""
    names = [norm(n) for n, _ in chain]
    need = min(2, len(names))  # the root alone ("Producción técnica") is not enough
    best, score = None, need - 1
    for sec, items in data["sections"].items():
        for it in items:
            if it.get("origin") == "scienti":
                continue
            t = [norm(x) for x in (it.get("type") or "").split(" - ")]
            k = next((i for i, (a, b) in enumerate(zip(names, t, strict=False)) if a != b), min(len(names), len(t)))
            if k > score:
                best, score = sec, k
    if best:
        return best
    return chain[1][0] if len(chain) > 1 and norm(chain[1][0]) != names[0] else chain[0][0]


def work_section(data, chain):
    lv = [n for n, _ in chain]
    for w in data["works"]:
        t = [x["type"] for x in w["types"]]
        if t[1:] == lv[1:] and w.get("origin") != "scienti":
            return w["cvlac"]["section"]
    l1, l2 = ([*lv, "", ""])[1], ([*lv, "", "", ""])[2]
    if l1 == "Libro":
        return (
            "Capitulos de libro"
            if "capítulo" in l2.lower()
            else ("Manuales y guías especializadas" if "manual" in l2.lower() else "Libros")
        )
    return WORK_SECTION.get(l1, l1 or lv[0])


def add_from_scienti(data, products, used, projects, events, networks, owner_id):
    """Put every Scienti record that no CvLAC entry matched into the section it belongs to (origin: 'scienti')."""
    owner_name = (data.get("profile") or {}).get("Nombre") or owner_id
    added = {"works": 0, "sections": {}, "projects": 0, "events": 0, "networks": 0}
    for p in products:
        pid = f"{p['COD_RH']}-{p['COD_PRODUCTO']}"
        if pid in used:
            continue
        chain = type_chain(p)
        if chain and chain[0][0] == "Producción bibliográfica":
            w = work_from_scienti(p, pid, chain, work_section(data, chain), owner_id, owner_name)
            data["works"].append(w)
            added["works"] += 1
        else:
            sec = item_section(data, chain) if chain else "Otros productos (Scienti)"
            data["sections"].setdefault(sec, []).append(item_from_scienti(p, pid, chain))
            added["sections"][sec] = added["sections"].get(sec, 0) + 1
    tagged = lambda lst: {e["scienti"]["id"] for e in lst if e.get("scienti")}
    have = tagged(data["projects"])
    for r in projects:
        rid = f"{r['COD_RH']}-{r['COD_PROYECTO']}"
        if rid in have:
            continue
        ym = lambda y, m: {"year": y, "month": m} if y else None
        data["projects"].append(
            {
                "type": None,
                "title": r.get("TXT_NME_PROYECTO"),
                "start": ym(r.get("NRO_ANO_INICIO"), r.get("NRO_MES_INICIO")),
                "end": ym(r.get("NRO_ANO_FIN"), r.get("NRO_MES_FIN")),
                "summary": r.get("TXT_RESUMEN_PROYECTO"),
                "origin": "scienti",
                "scienti": {
                    "id": rid,
                    "by": "not on the CvLAC page",
                    "scienti_title": r.get("TXT_NME_PROYECTO"),
                    "scienti_year": year_of(r.get("NRO_ANO_INICIO")),
                },
            }
        )
        added["projects"] += 1
    have = tagged(data["events"])
    for r in events:
        rid = f"{r['COD_RH']}-{r['COD_EVENTO']}"
        if rid in have:
            continue
        data["events"].append(
            {
                "name": r.get("TXT_NME_EVENTO"),
                "start": (r.get("DTA_INICIO") or "")[:10] or None,
                "origin": "scienti",
                "scienti": {
                    "id": rid,
                    "by": "not on the CvLAC page",
                    "scienti_title": r.get("TXT_NME_EVENTO"),
                    "scienti_year": r.get("NRO_ANO_REALIZACION") or year_of(r.get("DTA_INICIO")),
                },
            }
        )
        added["events"] += 1
    nets = data["sections"].get("Redes de conocimiento especializado", [])
    have = tagged(nets)
    for r in networks:
        rid = f"{r['COD_RH']}-{r['COD_RED']}"
        if rid in have:
            continue
        data["sections"].setdefault("Redes de conocimiento especializado", []).append(
            {
                "type": "Redes de conocimiento especializado",
                "title": r.get("TXT_NME_RED"),
                "year": year_of(r.get("DTA_FECHA_INI")),
                "origin": "scienti",
                "scienti": {
                    "id": rid,
                    "by": "not on the CvLAC page",
                    "scienti_title": r.get("TXT_NME_RED"),
                    "scienti_year": year_of(r.get("DTA_FECHA_INI")),
                },
            }
        )
        added["networks"] += 1
    return added


# ---------------------------------------------------------------- main entry
def enrich(data, cod_rh, institution=None, model_year=None, add_records=False, key=None, log=print, progress=None, siiu=True):
    progress = progress or (lambda stage, done=None, total=None: None)
    key = apikey(key)
    if not key:
        log("scienti: no API key ($COLAV_APIKEY or ~/.config/colav/apikey); skipped")
        return False
    progress("Scienti info")
    info = {x["institution"]: x["model_year"] for x in get("/scienti/info", key, get="resume")}
    order = [institution] if institution else [i for i in INSTITUTIONS if i in info] + [i for i in info if i not in INSTITUTIONS]
    products, inst = [], None
    for n, i in enumerate(order, 1):
        if len(order) > 1:  # several dumps to try: show which one
            progress("Scienti products", n - 1, len(order))
        else:
            progress("Scienti products")
        my = model_year or info.get(i)
        try:
            products = get("/scienti/product", key, COD_RH=cod_rh, model_year=my, institution=i)
        except RuntimeError as e:
            log(f"scienti: {i} {my}: {e}")
            continue
        if products:
            inst = i
            break
    if not inst:
        log(f"scienti: no products for {cod_rh} in {', '.join(order)}")
        data["scienti"] = {
            "institution": None,
            "model_year": None,
            "products": 0,
            "note": "COD_RH not found in the Scienti dumps",
        }
        return False
    my = model_year or info[inst]

    def fetch(ep, stage):
        progress(stage)
        d = get(f"/scienti/{ep}", key, COD_RH=cod_rh, model_year=my, institution=inst)
        return d if isinstance(d, list) else []

    projects = fetch("project", "Scienti projects")
    events = fetch("event", "Scienti events")
    networks = fetch("network", "Scienti networks")
    patents = fetch("patent", "Scienti patents")
    progress("Scienti matching")
    index = index_products(products, patents)

    used = set()

    def mark(entry, holder, by_key):
        c, by, ev = by_key
        if c:
            holder["scienti"] = {
                "id": c["id"],
                "by": by,
                "evidence": ev,
                "shared": c["id"] in used,
                "scienti_title": c["raw_title"],
                "scienti_year": c["year"],
            }
            used.add(c["id"])
            return c["id"]

    n_works = 0
    for w in data["works"]:
        ids = [x["id"] for x in w["source"].get("external_ids", []) if x["source"] in ("issn", "isbn")]
        ids += [x["id"] for x in w["external_ids"] if x["source"] == "isbn"]
        res = match_entry(
            index,
            used,
            title=w["title"],
            text=w["cvlac"]["text"],
            year=w["year_published"],
            doi=w["doi"],
            issn=[i for i in ids if len(digits(i)) == 8],
            isbn=[i for i in ids if len(digits(i)) >= 10],
            venue=w["source"].get("name"),
        )
        pid = mark(w, w["cvlac"], res)
        if pid:
            n_works += 1
            w["external_ids"].append({"provenance": "scienti", "source": "scienti", "id": pid})
    n_items = 0
    for _sec, items in data["sections"].items():
        for it in items:
            txt = it.get("text", "")
            res = match_entry(
                index,
                used,
                text=txt,
                year=it.get("year"),
                isbn=re.findall(r"ISBN:?\s*([\dXx-]{10,17})", txt),
                issn=re.findall(r"ISSN:?\s*([\dXx-]{8,9})", txt),
            )
            if mark(it, it, res):
                n_items += 1
    n_proj = tag(
        data["projects"],
        lambda p: (p.get("title"), (p.get("start") or {}).get("year")),
        projects,
        lambda r: f"{r['COD_RH']}-{r['COD_PROYECTO']}",
        lambda r: r.get("TXT_NME_PROYECTO"),
        lambda r: year_of(r.get("NRO_ANO_INICIO")),
    )
    n_ev = tag(
        data["events"],
        lambda e: (e.get("name"), year_of(e.get("start"))),
        events,
        lambda r: f"{r['COD_RH']}-{r['COD_EVENTO']}",
        lambda r: r.get("TXT_NME_EVENTO"),
        lambda r: r.get("NRO_ANO_REALIZACION") or year_of(r.get("DTA_INICIO")),
    )
    nets = data["sections"].get("Redes de conocimiento especializado", [])
    for it in nets:  # name and creation year from the generic item
        it["_name"] = (it.get("fields") or {}).get("Nombre de la red")
    n_net = tag(
        nets,
        lambda it: (it.get("_name"), it.get("year")),
        networks,
        lambda r: f"{r['COD_RH']}-{r['COD_RED']}",
        lambda r: r.get("TXT_NME_RED"),
        lambda r: year_of(r.get("DTA_FECHA_INI")),
        min_title=5,
    )
    for it in nets:
        it.pop("_name", None)
    n_used = len(used)
    # Scienti records no CvLAC entry matched: counted always, added to the JSON only with add_records
    added = add_from_scienti(
        data if add_records else copy.deepcopy(data), products, set(used), projects, events, networks, cod_rh
    )
    data["scienti"] = {
        "institution": inst,
        "model_year": my,
        "source": "apis.colav.co",
        "products": len(index),
        "products_matched": n_used,
        "matched": {"works": n_works, "section_items": n_items, "projects": n_proj, "events": n_ev, "networks": n_net},
        "records": {"projects": len(projects), "events": len(events), "networks": len(networks), "patents": len(patents)},
        "rules": f"DOI, or exact normalized title (>= {MIN_TITLE} chars and {MIN_WORDS} words) "
        "plus year, ISSN, ISBN, venue or patent number, "
        f"or a truncated title (prefix, >= {MIN_PREFIX} chars) plus the same year; "
        "projects/events/networks: exact normalized name plus the same year",
        ("added_from_scienti" if add_records else "not_on_page"): added,
        "not_on_page_note": (
            "Scienti records no CvLAC entry matched were added to the section they belong to, with origin 'scienti'"
            if add_records
            else "Scienti records no CvLAC entry matched, by the section they would belong to; "
            "not included (use --scienti full to add them)"
        ),
    }
    for p in data["projects"]:  # project ids as external ids, as in works
        if (p.get("scienti") or {}).get("id"):
            p.setdefault("external_ids", []).append({"provenance": "scienti", "source": "scienti", "id": p["scienti"]["id"]})
    log(
        f"scienti ({inst} {my}): products {n_used}/{len(index)} matched (works {n_works}, other items {n_items}); "
        f"projects {n_proj}/{len(projects)}, events {n_ev}/{len(events)}, networks {n_net}/{len(networks)}; "
        f"{'added from' if add_records else 'only in'} Scienti: works {added['works']}, "
        f"section items {sum(added['sections'].values())}, projects {added['projects']}, "
        f"events {added['events']}, networks {added['networks']}"
    )
    if siiu:
        from . import siiu as siiu_match

        siiu_match.enrich(data, cod_rh, my, inst, key, log=log, progress=progress)
    return True
