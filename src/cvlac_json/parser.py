"""Parse a public CvLAC page (Minciencias, Colombia) into one JSON document.

Reads https://scienti.minciencias.gov.co/cvlac/visualizador/generarCurriculoCv.do?cod_rh=COD_RH
(or a saved copy with --html) and writes one JSON with:
  profile, identifiers, academic_networks, education, experience, areas, languages,
  research_lines, awards, works (bibliographic production in the ImpactU work schema),
  projects, events, sections (every other section as generic items), counts.
With an apis.colav.co key (--apikey, else $COLAV_APIKEY, else ~/.config/colav/apikey) it also adds the Scienti ids
(COD_RH-COD_PRODUCTO, -COD_PROYECTO, -COD_EVENTO, -COD_RED) of matching entries (scienti.py);
--scienti full also adds the Scienti records missing from the page.
Experience institutions are resolved to ROR ids and added as the owner's affiliations on every work
whose year falls in the experience period (ror.py).
Standard library only.
"""

import datetime as dt
import html as H
import re
import unicodedata
import urllib.request

URL = "https://scienti.minciencias.gov.co/cvlac/visualizador/generarCurriculoCv.do?cod_rh={}"
MONTHS = {
    m: i + 1
    for i, m in enumerate(
        [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]
    )
}
# Sections whose items are bibliographic works (mapped to the ImpactU work schema)
BIBLIO = {
    "artículos",
    "libros",
    "capitulos de libro",
    "capítulos de libro",
    "textos en publicaciones no científicas",
    "otra producción blibliográfica",
    "otra producción bibliográfica",
    "libro de formación",
    "libros de formación",
    "manuales y guías especializadas",
    "traducciones",
    "notas científicas",
    "libros de divulgación",
    "libros de creación",
    "libro de creación",
    "trabajos en eventos",
    "documentos de trabajo",
    "publicaciones editoriales no especializadas",
}


# ---------------------------------------------------------------- helpers
def fetch(cod_rh):
    req = urllib.request.Request(URL.format(cod_rh), headers={"User-Agent": "Mozilla/5.0 (cvlac-json)"})
    with urllib.request.urlopen(req, timeout=180) as r:
        raw = r.read()
    enc = re.search(rb"charset=([\w-]+)", raw[:3000])
    return raw.decode(enc.group(1).decode() if enc else "latin-1", errors="replace")


def text(s, keep_lines=False):
    """HTML fragment -> clean text (optionally keeping <br>/<li> as line breaks)."""
    if s is None:
        return ""
    if keep_lines:
        s = re.sub(r"<br\s*/?>|</?li[^>]*>|</tr>", "\n", re.sub(r"[\r\n]+", " ", s), flags=re.I)
    s = H.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")
    if keep_lines:
        lines = [re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in s.split("\n")]
        return "\n".join(ln for ln in lines if ln)
    return re.sub(r"\s+", " ", s).strip()


def clean(v):
    v = (v or "").strip(" ,.;:-\n\t")
    return v or None


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def year_of(s):
    ys = re.findall(r"(?<!\d)(1[89]\d\d|20\d\d)(?!\d)", s or "")
    return int(ys[-1]) if ys else None


def month_year(s):
    """'Enerode2008' / 'Enero  2007' / 'Septiembre de 1998' / '2016 - Enero' -> {'year':.., 'month':..}"""
    s = (s or "").strip()
    words = [norm(w) for w in re.findall(r"[A-Za-zÁÉÍÓÚáéíóú]+", s)]
    month = next((MONTHS[m] for w in words for m in MONTHS if w == m or w == m + "de"), None)
    year = year_of(s)
    if not month and not year:
        return None
    return {"year": year, "month": month}


def split_list(block):
    """'a, b, c, ' -> ['a','b','c'] (areas use ' -- ' inside items, so split on ', ' only)."""
    return [x.strip() for x in re.split(r",\s+(?=\S)|,\s*$", block or "") if x and x.strip()]


def trailing_blocks(frag):
    """Extract <b>Palabras|Areas|Sectores: </b> lists and return (rest_of_html, dict)."""
    out = {}
    parts = re.split(r"<b>\s*(Palabras|Areas|Áreas|Sectores)\s*:\s*</b>", frag, flags=re.I)
    rest = parts[0]
    for name, block in zip(parts[1::2], parts[2::2], strict=False):
        key = {"palabras": "keywords", "areas": "areas", "áreas": "areas", "sectores": "sectors"}[name.lower()]
        out[key] = split_list(text(block))
    return rest, out


def labeled_fields(frag):
    """<i>Label: </i> value ... -> {label: value}. Value runs until the next <i>, <b> or <br>."""
    out = {}
    for m in re.finditer(
        r"<i>\s*(?:<b>)?\s*([^<:]{1,60}?)\s*:?\s*(?:</b>)?\s*</i>(.*?)(?=<i>|<b>|<br|$)", frag, flags=re.I | re.S
    ):
        k = clean(text(m.group(1)))
        v = clean(text(m.group(2)))
        if k and k not in out:
            out[k] = v
    return out


def links(frag):
    return [
        {"url": H.unescape(u), "label": clean(text(lbl))}
        for u, lbl in re.findall(r'<a[^>]+href="([^"#][^"]*)"[^>]*>(.*?)</a>', frag, flags=re.I | re.S)
    ]


# ---------------------------------------------------------------- page structure
def sections(page):
    """[(title, html)] split at each <h3> section header."""
    starts = [m.start() for m in re.finditer(r"<h3[^>]*>", page, flags=re.I)]
    out = []
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else len(page)
        frag = page[s:e]
        title = text(re.search(r"<h3[^>]*>(.*?)</h3>", frag, flags=re.I | re.S).group(1))
        out.append((title, frag.split("</h3>", 1)[1]))
    return out


ITEM_RE = re.compile(
    r"(?P<hdr>(?:<li>|<td>)\s*(?P<img><img[^>]*>)?\s*<b>(?P<h>(?:(?!</?b>).)*?)</b>\s*(?:</li>|</td>))"
    r"|<blockquote[^>]*>(?P<bq>.*?)</blockquote>",
    flags=re.I | re.S,
)


def items(frag):
    """Sequence of (header, endorsed, blockquote_html); each blockquote takes the last header seen."""
    hdr, endorsed, out = None, False, []
    for m in ITEM_RE.finditer(frag):
        if m.group("hdr"):
            hdr, endorsed = clean(text(m.group("h"))), bool(m.group("img") and "chulo" in m.group("img"))
        else:
            out.append((hdr, endorsed, m.group("bq")))
    return out


def generic(hdr, endorsed, bq):
    rest, extra = trailing_blocks(bq)
    it = {"type": hdr, "endorsed": endorsed, "text": text(rest, keep_lines=True)}
    f = labeled_fields(rest)
    if f:
        it["fields"] = f
    lk = links(bq)
    if lk:
        it["links"] = lk
    it.update(extra)
    it["year"] = year_of(text(rest))
    return it


# ---------------------------------------------------------------- specific sections
def parse_profile(frag):
    prof, notes = {}, []
    for row in re.findall(r"<tr[^>]*>((?:(?!<tr|<table).)*?)</tr>", frag, flags=re.I | re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.I | re.S)
        if len(tds) == 2 and "<table" not in row:
            k, v = clean(text(tds[0])), clean(text(tds[1]))
            if k:
                prof[k] = v
        elif len(tds) == 1 and "<table" not in row and clean(text(tds[0])):
            notes.append(clean(text(tds[0])))
    if notes:
        prof["notes"] = notes
    return prof


# Nationalities whose names usually carry two surnames (paternal + maternal)
TWO_SURNAMES = {
    "colombiana",
    "colombiano",
    "española",
    "español",
    "mexicana",
    "mexicano",
    "venezolana",
    "venezolano",
    "peruana",
    "peruano",
    "ecuatoriana",
    "ecuatoriano",
    "chilena",
    "chileno",
    "argentina",
    "argentino",
    "boliviana",
    "boliviano",
    "cubana",
    "cubano",
    "uruguaya",
    "uruguayo",
    "paraguaya",
    "paraguayo",
    "costarricense",
    "panameña",
    "panameño",
    "hondureña",
    "hondureño",
    "salvadoreña",
    "salvadoreño",
    "guatemalteca",
    "guatemalteco",
    "nicaragüense",
    "dominicana",
    "dominicano",
    "puertorriqueña",
    "puertorriqueño",
}
PARTICLES = {"de", "del", "la", "las", "los", "y", "da", "das", "do", "dos", "van", "von", "der", "di", "le"}


def split_name(raw_frag, prof):
    """{full_name, first_names, last_names, name_split_by} for the profile, as in ImpactU's person record.

    The page writes the name as 'NAMES&nbsp;SURNAME1&nbsp;SURNAME2'. Those parts are used when they agree with
    'Nombre en citaciones' ('SURNAME1 SURNAME2, NAMES'); else the citation name decides how many words are
    surnames; else the nationality (two surnames for Hispanic nationalities, one otherwise).
    """
    full = prof.get("Nombre")
    if not full:
        return {}
    words = full.split()
    cit = prof.get("Nombre en citaciones") or ""
    cit_last = norm(cit.split(",", 1)[0]) if "," in cit else ""
    parts = None
    m = re.search(r"<td[^>]*>\s*Nombre\s*</td>\s*<td[^>]*>(.*?)</td>", raw_frag or "", flags=re.I | re.S)
    if m:
        parts = [p for p in (clean(text(x)) for x in re.split(r"&nbsp;|&#160;|\xa0", m.group(1))) if p]
    if parts and len(parts) >= 2 and (not cit_last or norm(" ".join(parts[1:])) == cit_last):
        first, last, by = parts[0].split(), parts[1:], "page"
    elif cit_last and norm(" ".join(words)).endswith(cit_last):
        k = len(cit_last.split())
        first, last, by = words[:-k], [" ".join(words[-k:])], "citation name"
    else:
        n = 2 if norm(prof.get("Nacionalidad")) in {norm(x) for x in TWO_SURNAMES} else 1
        idx, count = len(words), 0
        while idx > 1 and count < n:  # take surnames from the end, keeping particles ('de la Cruz') with them
            idx -= 1
            while idx > 1 and words[idx - 1].lower() in PARTICLES:
                idx -= 1
            count += 1
        first, last, by = words[:idx], [" ".join(words[idx:])] if n == 1 else _surnames(words[idx:]), "nationality"
    if by == "citation name" and len(cit_last.split()) >= 2:
        last = _surnames(last[0].split())
    return {"full_name": " ".join(words), "first_names": first, "last_names": last, "name_split_by": by}


def _surnames(ws):
    """['de', 'la', 'Cruz', 'Pérez'] -> ['de la Cruz', 'Pérez'] (particles stay with the next word)."""
    out, cur = [], []
    for w in ws:
        cur.append(w)
        if w.lower() not in PARTICLES:
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return out


def parse_links(frag):
    out = []
    for lk in links(frag):
        it = {"name": lk["label"], "url": lk["url"]}
        m = re.search(r"orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", lk["url"])
        if m:
            it["id"], it["source"] = m.group(1), "orcid"
        m = re.search(r"authorId=(\d+)", lk["url"])
        if m:
            it["id"], it["source"] = m.group(1), "scopus"
        m = re.search(r"[?&]user=([\w-]+)", lk["url"])
        if m and "scholar" in lk["url"]:
            it["id"], it["source"] = m.group(1), "scholar"
        m = re.search(r"researcherid\.com/rid/([\w-]+)|publons\.com/researcher/(\d+)", lk["url"])
        if m:
            it["id"], it["source"] = m.group(1) or m.group(2), "researcherid"
        out.append(it)
    return out


def parse_dates_range(s):
    a, _, b = (s or "").partition(" - ")
    return month_year(a), month_year(b)


def parse_education(frag):
    out = []
    for row in re.findall(r"<td[^>]*>\s*<b>(.*?)</b>(.*?)</td>", frag, flags=re.I | re.S):
        level = clean(text(row[0]))
        lines = text(row[1], keep_lines=True).split("\n")
        inst = lines[0] if lines else None
        program = lines[1] if len(lines) > 1 else None
        start, end = parse_dates_range(lines[2]) if len(lines) > 2 else (None, None)
        out.append(
            {
                "level": level,
                "institution": clean(inst),
                "program": clean(program),
                "start": start,
                "end": end,
                "thesis": clean(" ".join(lines[3:])) if len(lines) > 3 else None,
                "dates_text": lines[2] if len(lines) > 2 else None,
            }
        )
    return out


def parse_experience(frag):
    out = []
    for blk in re.split(r"<td[^>]*>\s*<b>", frag)[1:]:
        inst, _, body = blk.partition("</b>")
        lines = text(body, keep_lines=True).split("\n")
        it = {"institution": clean(text(inst)), "dedication": None, "period": None, "activities": []}
        cur = None
        for ln in lines:
            if ln.startswith("Dedicación:"):
                m = re.match(r"Dedicación:\s*(.*?horas\s*\w*)\s*(.*)", ln)
                it["dedication"] = clean(m.group(1)) if m else clean(ln[11:])
                it["period"] = clean(m.group(2)) if m else None
            elif ln.startswith("Actividades de"):
                cur = {"type": ln, "items": []}
                it["activities"].append(cur)
            elif ln.startswith("-") and cur is not None:
                v = clean(ln.lstrip("- "))
                if v:
                    cur["items"].append(v)
        out.append(it)
    return out


def parse_li_list(frag):
    return [clean(text(x)) for x in re.findall(r"<li[^>]*>(.*?)</li>", frag, flags=re.I | re.S) if clean(text(x))]


def parse_languages(frag):
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", frag, flags=re.I | re.S):
        lang = re.search(r"<li[^>]*>(.*?)</li>", row, flags=re.I | re.S)
        tds = [clean(text(x)) for x in re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.I | re.S)]
        if lang and len(tds) >= 5:
            out.append(
                {
                    "language": clean(text(lang.group(1))),
                    "speaks": tds[-4],
                    "writes": tds[-3],
                    "reads": tds[-2],
                    "understands": tds[-1],
                }
            )
    return out


def parse_lines(frag):
    out = []
    for x in parse_li_list(frag):
        m = re.match(r"(.*?),?\s*Activa:\s*(\w+)", x)
        out.append({"name": clean(m.group(1)) if m else x, "active": (m.group(2).lower().startswith("s")) if m else None})
    return out


def parse_awards(frag):
    out = []
    for x in parse_li_list(frag):
        if x.startswith("Los ítems de producción"):
            continue
        m = re.match(r"(.*),(.*?)\s+-\s+(.*)$", x)
        out.append(
            {"name": clean(m.group(1)), "institution": clean(m.group(2)), "date": month_year(m.group(3)), "text": x}
            if m
            else {"text": x}
        )
    return out


def parse_projects(frag):
    out = []
    for _, _, bq in items(frag):
        lines = text(bq, keep_lines=True).split("\n")
        f = labeled_fields(bq)
        title = next((ln for ln in lines[1:] if not re.match(r"(Inicio|Fin|Duración|Resumen)\b", ln)), None)
        res = re.search(r"<b>\s*Resumen\s*</b>(.*)", bq, flags=re.I | re.S)
        out.append(
            {
                "type": f.get("Tipo de proyecto"),
                "title": clean(title),
                "start": month_year(f.get("Inicio")),
                "projected_end": month_year(f.get("Fin proyectado")),
                "end": month_year(f.get("Fin")),
                "duration_months": int(f["Duración"]) if (f.get("Duración") or "").isdigit() else None,
                "summary": clean(text(res.group(1))) if res else None,
            }
        )
    return out


def parse_events(frag):
    out = []
    blocks = re.split(r"(<img[^>]*>)?\s*<b>\s*\d+\s*</b>\s*(?=<i>\s*<b>\s*Nombre del evento)", frag)
    for img, b in zip(blocks[1::2], blocks[2::2], strict=False):
        head, *rest = re.split(r"<b>\s*(Productos asociados|Instituciones asociadas|Participantes)\s*</b>", b)
        f = labeled_fields(head)
        ev = {
            "name": f.get("Nombre del evento"),
            "type": f.get("Tipo de evento"),
            "scope": f.get("Ámbito"),
            "endorsed": bool(img and "chulo" in img),
        }
        m = re.search(r"Realizado el:\s*([\d-]+)[^,]*,\s*([\d-]*)[^e]*en\s+(.*)", text(head))
        if m:
            ev.update(start=m.group(1) or None, end=m.group(2) or None, place=clean(m.group(3)))
        ev.update(products=[], institutions=[], participants=[])
        for name, blk in zip(rest[0::2], rest[1::2], strict=False):
            for li in re.findall(r"<li[^>]*>(.*?)</li>", blk, flags=re.I | re.S):
                g = labeled_fields(li + "<br>")
                if name.startswith("Productos"):
                    ev["products"].append({"name": g.get("Nombre del producto"), "type": g.get("Tipo de producto")})
                elif name.startswith("Instituciones"):
                    m2 = re.search(r"Tipo de vinculaci(?:ó|&oacute;)n\s*</i>(.*)", li, flags=re.S)
                    ev["institutions"].append(
                        {"name": g.get("Nombre de la institución"), "link": clean(text(m2.group(1))) if m2 else None}
                    )
                else:
                    ev["participants"].append({"name": g.get("Nombre"), "role": g.get("Rol en el evento")})
        out.append(ev)
    return out


# ---------------------------------------------------------------- supervised theses (Trabajos dirigidos/tutorías)
THESIS_STATUS = {"tesis concluida": "completed", "tesis en curso": "ongoing"}
ROLE_TYPE = {"tutor principal": "advisor"}


def parse_thesis(it, raw, owner):
    """Add title, authors (advisor / co-advisor / student), institution, status and program to a thesis item.
    The page separates 'OWNER, Title' / institution / 'Estado: ...' / program / 'YEAR. Dirigió como: ROLE' /
    'Persona(s) orientada(s):' / students / 'N meses' / 'Tutor(es)/Cotutor(es): ...' with &nbsp;."""
    _, _, bq = raw
    rest = re.split(r"<br>\s*<b>(?:Palabras|Areas|Sectores)", bq)[0]
    segs = [x for x in (text(x) for x in re.split(r"&nbsp;|&#160;", rest)) if x]
    i_st = next((i for i, x in enumerate(segs) if x.startswith("Estado:")), None)
    i_dir = next((i for i, x in enumerate(segs) if "Dirigió como" in x), None)
    if i_st is None or i_st < 2:
        return it
    head = " ".join(segs[: i_st - 1])
    on = {norm(owner.get("name")), norm(owner.get("citation_name"))} - {""}
    m = re.match(r"(.+?),\s*(.*)", head)
    owner_text, title = (m.group(1), m.group(2)) if m and norm(m.group(1)) in on else (None, head)
    title = clean(re.sub(r"\.$", "", title.strip()))
    status_txt = clean(segs[i_st][len("Estado:") :])
    program = clean(" ".join(segs[i_st + 1 : i_dir])) if i_dir else None
    role = None
    if i_dir is not None:
        mr = re.search(r"Dirigió como:\s*([^,]+)", segs[i_dir])
        role = clean(mr.group(1)) if mr else None
        my = re.match(r"((?:19|20)\d\d)", segs[i_dir])
        if my:
            it["year"] = int(my.group(1))
    tail = " | ".join(segs[(i_dir or i_st) + 1 :])
    tail = re.sub(r"Persona\(s\) orientada\(s\):", "", tail)
    tutors_txt = ""
    mt = re.search(r"Tutor\(es\)/Cotutor\(es\):(.*)$", tail)
    if mt:
        tutors_txt, tail = mt.group(1), tail[: mt.start()]
    md = re.search(r"(\d+)\s*meses", tail)
    duration = int(md.group(1)) if md else None
    tail = re.sub(r"\d+\s*meses,?", "", tail)
    split = lambda t: [n for n in (clean(x) for x in re.split(r"[,|]", t)) if n]
    students = split(tail)
    own_type = ROLE_TYPE.get(norm(role).replace("coturor", "cotutor"), "co-advisor" if role else "advisor")
    people = [
        {
            "full_name": owner_text or owner.get("name"),
            "type": own_type,
            "id": owner["cod_rh"],
            "external_ids": [{"provenance": "cvlac", "source": "scienti", "id": owner["cod_rh"]}],
            "affiliations": [],
        }
    ]
    seen = on | {norm(x) for x in students}
    for n in split(tutors_txt):
        if norm(n) not in seen:
            seen.add(norm(n))
            people.append({"full_name": n, "type": "co-advisor", "id": None, "external_ids": [], "affiliations": []})
    people += [{"full_name": n, "type": "student", "id": None, "external_ids": [], "affiliations": []} for n in students]
    inst = clean(segs[i_st - 1])
    out = {
        "type": it.get("type"),
        "title": title,
        "titles": [{"title": title, "source": "cvlac", "provenance": "cvlac"}] if title else [],
        "authors": people,
        "institution": {"name": inst} if inst else None,
        "status": THESIS_STATUS.get(norm(status_txt), status_txt),
        "status_text": status_txt,
        "program": program,
        "role": role,
        "duration_months": duration,
    }
    out.update({k: v for k, v in it.items() if k not in out})
    f = {k: v for k, v in (out.get("fields") or {}).items() if k not in ("Dirigió como", "Persona(s) orientada(s)")}
    out["fields"] = f or None  # those two are now role / authors
    return out


# ---------------------------------------------------------------- bibliographic works -> ImpactU schema
DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s<>\"{}|\\^`\[\]]+", re.I)  # same pattern as Yuku's cvlac_related_works


def find_doi(*texts):
    """First DOI found in texts, tried in order.

    The CvLAC writes the DOI as a bare DOI, as a URL (https://doi.org/..., dx.doi.org) or after junk
    ('Rev. Acad. ... Nahttp://dx.doi.org/10...'). Trailing punctuation and slashes are dropped; a closing
    parenthesis is kept only when it is balanced, as in 10.1016/0002-9149(83)90004-X.
    """
    for s in texts:
        for m in DOI_RE.finditer(s or ""):
            d = m.group(0)
            while d and (d[-1] in ".,;:/]}" or (d[-1] == ")" and d.count("(") < d.count(")"))):
                d = d[:-1]
            if re.fullmatch(r"10\.\d{4,9}/\S+", d):
                return d.lower()
    return None


def split_authors(s):
    s = re.sub(r"Tipo:\s*[^,\n]*?(?=\n|$)", "", s)  # chapters repeat 'Tipo: ...' after each author
    return [a for a in (clean(x) for x in re.split(r",\s*\n?|\n", s)) if a and not a.lower().startswith("tipo")]


def work_from_item(sec, hdr, endorsed, bq, owner, n):
    rest, extra = trailing_blocks(bq)
    t = text(rest, keep_lines=True)
    flat = re.sub(r"\s+", " ", t)
    f = labeled_fields(rest)
    m_tipo = re.match(r"\s*Tipo:\s*([^\n]+)\n", t)
    hier = [clean(x) for x in (hdr or "").split(" - ") if clean(x)]
    if not hier:
        hier = ["Producción bibliográfica", sec]
    if m_tipo:
        hier = ["Producción bibliográfica", "Capítulo de libro", clean(m_tipo.group(1))]
        t = t[m_tipo.end() :]
        flat = re.sub(r"\s+", " ", t)
    title = authors = None
    after = flat
    q1 = flat.find('"')
    if q1 >= 0:
        en = re.search(r'"\s*[^"]*?(?:\.\s*)?En:', flat[q1 + 1 :])
        q2 = q1 + 1 + en.start() if en else flat.rfind('"')
        if q2 > q1:
            title, authors, after = flat[q1 + 1 : q2].strip(), split_authors(t[: t.find('"')]), flat[q2 + 1 :]
    if title is None:  # labeled formats (Libro de formación, Manuales, ...)
        title = f.get("Nombre del libro") or f.get("Nombre del producto") or f.get("Titulo") or f.get("Título")
        authors = []
        if not title:  # 'AUTHOR, AUTHOR, Title . En: ...'
            m = re.match(r"(.*?)(?:\s\.\s|\s\.?\s*En:)", flat)
            parts = [p.strip() for p in (m.group(1) if m else flat).split(",")]
            caps = [p for p in parts if p and p == p.upper() and len(p.split()) >= 2]
            authors, title = caps, clean(", ".join(parts[len(caps) :]))
    g = lambda pat, s=after: (lambda m: clean(m.group(1)) if m else None)(re.search(pat, s, flags=re.I))
    mc = re.search(r"En:\s*([^\n]+)", t)
    country = clean(re.split(r"\.|\s(?:19|20)\d\d|ISBN|ISSN|,", mc.group(1))[0]) if mc else None
    country = country or f.get("Lugar de publicación")
    issn, isbn = g(r"ISSN:\s*([\dXx-]{8,9})"), g(r"ISBN:\s*([\dXx-]{10,17})") or f.get("Isbn")
    m_doi = re.search(r"DOI:\s*(.*)", after, flags=re.I)
    doi = find_doi(m_doi.group(1) if m_doi else "", flat, *(lk["url"] for lk in links(bq)))
    pub = g(r"ed:\s*([^<\n]*?)(?:\s{2,}|\s+v\.|\s+ISBN|\s*,\s*v\.|$)") or f.get("Editorial")
    vol = g(r"\bv\.\s*([\w-]+)")
    issue = g(r"fasc\.\s*(?!p\.)([\w/-]+)")
    vol, issue = (None if (x or "").upper() in ("N/A", "NA", "") else x for x in (vol, issue))
    pages = re.search(r"\bp\.\s*([\w]+)\s*-\s*([\w]+)", after)
    npages = g(r"pags\.\s*(\d+)")
    # Labeled formats carry the date in its own field; their free text holds the title ('... al año 2050').
    year = year_of(f.get("Fecha de presentación"))
    m = None
    if not year:
        m = (
            re.search(r",\s*((?:19|20)\d\d)\s*,?", after)
            or re.search(r"En:[^.]*?\s((?:19|20)\d\d)\b", after)
            or re.search(r"\b((?:19|20)\d\d)\b", after)
        )
    if m:
        year = int(m.group(1))
    source_name = None
    if hier[1:2] == ["Artículo"] or sec.lower() == "artículos":
        source_name = g(r"(?:<br>|\n)?\s*([^\n]+?)\s+ISSN:", t[t.find('"', t.find('"') + 1) + 1 :] if title else t)
        if source_name:
            source_name = clean(re.sub(r"^\.?\s*En:\s*[^\n]*\n?", "", source_name))
    elif "Capítulo" in " ".join(hier) or sec.lower().startswith("capitulos"):
        source_name = clean(re.split(r"\.\s*En:|\sEn:", after)[0])
    elif sec.lower().startswith("textos en publicaciones"):
        source_name = g(r"(?:19|20)\d\d\.\s*([^.]+?)\.\s*ISSN") or g(r"(?:19|20)\d\d\.\s*([^.]+?)\.")
    names = authors or []
    on = norm(owner.get("name")), norm(owner.get("citation_name"))

    def is_owner(a):
        na = norm(a)
        return bool(na) and (na == on[0] or na == on[1] or (on[1] and set(na.split()) == set(on[1].split())))

    inferred = False
    if not names and owner.get("name"):  # labeled formats list no authors: the CV owner is the author
        names, inferred = [owner["name"]], True
    authors_out = []
    for a in names:
        own = inferred or is_owner(a)
        authors_out.append(
            {
                "full_name": a,
                "id": owner["cod_rh"] if own else "",
                "external_ids": [{"provenance": "cvlac", "source": "scienti", "id": owner["cod_rh"]}] if own else [],
                "affiliations": [],
            }
        )
    ext = []
    if doi:
        ext.append({"provenance": "cvlac", "source": "doi", "id": doi})
    if isbn:
        ext.append({"provenance": "cvlac", "source": "isbn", "id": isbn})
    src_ids = (
        [{"source": "issn", "id": issn}]
        if issn
        else ([{"source": "isbn", "id": isbn}] if isbn and "Capítulo" in " ".join(hier) else [])
    )
    subjects = []
    for a in extra.get("areas", []):
        lv = [x.strip() for x in a.split("--")]
        subjects += [{"name": x, "level": i} for i, x in enumerate(lv) if x]
    work = {
        "id": f"cvlac:{owner['cod_rh']}:{n}",
        "title": clean(title),
        "titles": [{"title": clean(title), "lang": "", "source": "cvlac", "provenance": "cvlac"}] if clean(title) else [],
        "types": [{"provenance": "cvlac", "source": "cvlac", "type": x, "level": i} for i, x in enumerate(hier)],
        "product_types": [{"name": hier[-1], "source": "cvlac"}],
        "authors": authors_out,
        "authors_count": len(authors_out),
        "year_published": year,
        "doi": f"https://doi.org/{doi}" if doi else None,
        "external_ids": ext,
        "external_urls": [{"provenance": "cvlac", "source": "cvlac", "url": lk["url"]} for lk in links(bq)]
        + (
            [{"provenance": "cvlac", "source": "medio de verificación", "url": f["Medio de verificación"]}]
            if f.get("Medio de verificación")
            else []
        ),
        "source": {
            "name": source_name,
            "external_ids": src_ids,
            "publisher": {"name": clean(pub), "country": clean(country)} if (pub or country) else {},
        },
        "bibliographic_info": {
            k: v
            for k, v in {
                "volume": vol,
                "issue": issue,
                "start_page": pages.group(1) if pages else None,
                "end_page": pages.group(2) if pages else None,
                "pages": npages,
            }.items()
            if v
        },
        "keywords": extra.get("keywords", []),
        "subjects": [{"source": "cvlac", "subjects": subjects}] if subjects else [],
        "cvlac": {
            "section": sec,
            "endorsed": endorsed,
            "country": clean(country),
            "authors_inferred": inferred,
            "sectors": extra.get("sectors", []),
            "areas": extra.get("areas", []),
            "fields": f,
            "text": t.strip(),
        },
    }
    return work


# ---------------------------------------------------------------- main
def build(page, cod_rh):
    raw_secs = dict(sections(page))  # with &nbsp; kept: it separates the thesis fields
    page = re.sub(r"&nbsp;|&#160;", " ", page)
    secs = sections(page)
    out = {
        "cod_rh": cod_rh,
        "url": URL.format(cod_rh),
        "retrieved": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "profile": {},
        "identifiers": [],
        "academic_networks": [],
        "education": {"academic": [], "complementary": []},
        "experience": [],
        "areas": [],
        "languages": [],
        "research_lines": [],
        "awards": [],
        "works": [],
        "projects": [],
        "events": [],
        "sections": {},
        "counts": {},
    }
    if not secs:
        raise SystemExit(f"error: no CvLAC sections found for {cod_rh} (wrong COD_RH or the page changed)")
    for title, frag in secs:
        low = title.lower()
        if low == "hoja de vida":
            out["profile"] = parse_profile(frag)
            out["profile"].update(split_name(raw_secs.get(title), out["profile"]))
        elif low.startswith("identificadores"):
            out["identifiers"] = parse_links(frag)
        elif low.startswith("redes sociales"):
            out["academic_networks"] = parse_links(frag)
        elif low == "formación académica":
            out["education"]["academic"] = parse_education(frag)
        elif low == "formación complementaria":
            out["education"]["complementary"] = parse_education(frag)
        elif low == "experiencia profesional":
            out["experience"] = parse_experience(frag)
        elif low == "áreas de actuación":
            out["areas"] = parse_li_list(frag)
        elif low == "idiomas":
            out["languages"] = parse_languages(frag)
        elif low == "líneas de investigación":
            out["research_lines"] = parse_lines(frag)
        elif low == "reconocimientos":
            out["awards"] = parse_awards(frag)
        elif low == "proyectos":
            out["projects"] = parse_projects(frag)
        elif low == "eventos científicos":
            out["events"] = parse_events(frag)
        else:
            its = items(frag)
            if low in BIBLIO or any((h or "").startswith("Producción bibliográfica") for h, _, _ in its):
                continue  # handled below, after the profile is known
            out["sections"][title] = [generic(*i) for i in its]
    p = out["profile"]
    owner = {"cod_rh": cod_rh, "name": p.get("Nombre"), "citation_name": p.get("Nombre en citaciones")}
    for title in list(out["sections"]):
        if title.lower().startswith("trabajos dirigidos") and title in raw_secs:
            raw_items = items(raw_secs[title])
            if len(raw_items) == len(out["sections"][title]):
                out["sections"][title] = [
                    parse_thesis(it, raw, owner) for it, raw in zip(out["sections"][title], raw_items, strict=False)
                ]
        else:
            from .other_sections import structure

            bqs = [bq for _, _, bq in items(dict(secs)[title])]
            if len(bqs) == len(out["sections"][title]):
                out["sections"][title] = [structure(it, bq, owner) for it, bq in zip(out["sections"][title], bqs, strict=True)]
    for title, frag in secs:
        its = items(frag)
        if title.lower() in BIBLIO or any((h or "").startswith("Producción bibliográfica") for h, _, _ in its):
            for hdr, endorsed, bq in its:
                out["works"].append(work_from_item(title, hdr, endorsed, bq, owner, len(out["works"]) + 1))
    count(out)
    return out


def count(out):
    old = out.get("counts", {})
    c = {
        "works": len(out["works"]),
        "projects": len(out["projects"]),
        "events": len(out["events"]),
        "education": len(out["education"]["academic"]) + len(out["education"]["complementary"]),
    }
    for w in out["works"]:
        k = "works:" + w["cvlac"]["section"]
        c[k] = c.get(k, 0) + 1
    c.update({k: len(v) for k, v in out["sections"].items()})
    c["endorsed_works"] = sum(bool(w["cvlac"].get("endorsed")) for w in out["works"])
    for k in ("works", "projects", "events"):
        n = sum(x.get("origin") == "scienti" for x in out[k])
        if n:
            c[f"{k}_only_in_scienti"] = n
    n = sum(it.get("origin") == "scienti" for v in out["sections"].values() for it in v)
    if n:
        c["section_items_only_in_scienti"] = n
    if "works_with_affiliation" in old:
        c["works_with_affiliation"] = old["works_with_affiliation"]
    out["counts"] = c


def empty_like(v):
    return [] if isinstance(v, list) else None


def harmonize(records):
    """Give every record of one collection the same keys: a key that has a value in any record is kept in
    all of them, with an empty value ([] or null) where that record has none. Keys empty in every record
    are dropped. Nested dicts and lists of dicts are harmonized the same way across the collection."""
    records = [r for r in records if isinstance(r, dict)]
    keys = []
    for r in records:
        keys += [k for k in r if k not in keys]
    for k in keys:
        vals = [r.get(k) for r in records]
        if all(v in (None, "", [], {}) for v in vals):
            for r in records:
                r.pop(k, None)
            continue
        sample = next(v for v in vals if v not in (None, "", [], {}))
        if isinstance(sample, dict):
            harmonize([v for v in vals if isinstance(v, dict) and v])
        elif isinstance(sample, list) and any(isinstance(x, dict) for x in sample):
            harmonize([x for v in vals if isinstance(v, list) for x in v])
        for r in records:
            if r.get(k) in (None, "", [], {}):
                r[k] = empty_like(sample)


def tidy(data):
    """Same keys for every record of a section (works, projects, events, each `sections` list...)."""
    recs = [x for k in ("works", "projects", "events") for x in data[k]] + [x for v in data["sections"].values() for x in v]
    if any(x.get("origin") == "scienti" for x in recs):  # only with --scienti full
        for x in recs:
            x.setdefault("origin", "cvlac")
    for k, v in data.items():
        if isinstance(v, list):
            harmonize(v)
        elif k in ("education", "sections"):
            for x in v.values():
                harmonize(x)
    return data


SCIENTI_STAGES = [
    "Scienti info",
    "Scienti products",
    "Scienti projects",
    "Scienti events",
    "Scienti networks",
    "Scienti patents",
    "Scienti matching",
]


def stages(html=None, scienti="auto", ror=True, siiu=True):
    """Names of the progress stages extract() reports, in order."""
    out = [] if html is not None else ["CvLAC page"]
    out.append("Parsing")
    if scienti != "off":
        out += SCIENTI_STAGES
        if siiu:
            out.append("SIIU projects")
    if ror:
        out.append("ROR")
    return [*out, "Finishing"]


def extract(
    cod_rh,
    html=None,
    scienti="auto",
    institution=None,
    model_year=None,
    apikey=None,
    ror=True,
    log=print,
    progress=None,
    siiu=True,
):
    """Build the CvLAC JSON for COD_RH.

    html: the page's HTML (str) instead of downloading it. scienti: "auto" (Scienti ids of matching
    entries when an apis.colav.co key is available), "full" (also the Scienti records missing from
    the page) or "off". ror: look experience and thesis institutions up in the ROR API.
    siiu: with Scienti on, also add the SIIU code (UdeA) of the projects whose title and year match.
    progress: optional callable progress(stage, done=None, total=None), called with the names from
    stages(); the command line passes a cvlac_json.progress.Progress bar.
    """
    from . import ror as ror_affiliations
    from . import scienti as scienti_match

    progress = progress or (lambda stage, done=None, total=None: None)
    cod = normalize_cod_rh(cod_rh)
    if html is None:
        progress("CvLAC page")
    page = html if html is not None else fetch(cod)
    progress("Parsing")
    data = build(page, cod)
    if scienti != "off":  # first, so works added from Scienti get affiliations too
        try:
            scienti_match.enrich(
                data,
                cod,
                institution,
                model_year,
                add_records=scienti == "full",
                key=apikey,
                log=log,
                progress=progress,
                siiu=siiu,
            )
        except RuntimeError as e:
            log(f"scienti: skipped ({e})")
    ror_affiliations.enrich(data, ror=ror, progress=progress)
    progress("Finishing")
    count(data)
    tidy(data)
    return data


def normalize_cod_rh(cod_rh):
    """'26549' -> '0000026549'; raises ValueError unless it is up to 10 digits."""
    cod = str(cod_rh).strip().zfill(10)
    if not cod.isdigit() or len(cod) != 10:
        raise ValueError("COD_RH must be up to 10 digits")
    return cod
