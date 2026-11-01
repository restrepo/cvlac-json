"""Structured fields for the items of the other CvLAC sections (`sections`, apart from supervised theses).

Each item keeps `type`, `endorsed`, `text`, `fields`, `keywords`, `areas`, `sectors` and `year`, and gains, when the
text has them:
  title, authors[] (each person listed before the title; the owner gets the COD_RH), country, city, institution,
  publisher, date (YYYY-MM-DD, YYYY-MM or YYYY), duration ({value, unit}), pages, role, purpose,
  identifiers[] ({source, id}: contract/registration, patent, NIT, register numbers, accession, DOI, ISBN, ISSN)
  and links[] (URLs written in the text, besides any <a> link).
`fields` values that ran into the next, unlabeled part of the text (". En: Colombia, ,2017, 0 meses p.") are cut.

Authors come from the page layout: the CvLAC writes each person on its own source line, ending in a comma and a run
of spaces, before the title line.
"""

import re

from .parser import clean, find_doi, month_year, norm, text

AUTHOR_LINE = re.compile(r"^[ \t]*([^<>\n]*?[^\s,<>]),[ \t]{6,}\r?$", re.M)
URL_RE = re.compile(r"(?:https?://|www\.)[^\s,;<>\"']+", re.I)
ISO_DATE = re.compile(r"\b((?:19|20)\d\d)-(\d\d)-(\d\d)(?:[ T]\d\d:\d\d:\d\d(?:\.\d+)?)?")
YEAR = r"(?:19|20)\d\d"
# where a title ends when nothing labels it
TITLE_END = re.compile(
    r",\s*(?:Nombre comercial|Finalidad|Ciclo|Nit\b|Fecha de obtención|Institución:)"
    r"|\s*\.?\s*En:\s"
    r"|,\s*En\s+[A-ZÁÉÍÓÚ]"
    r"|,\s*,\s*" + YEAR + r"|\.\s*Institución solicitante|\s+en:(?:\s|$)|\s*\n"
)
TITLE_FIELDS = (
    "Nombre del producto",
    "Nombre del evento",
    "Nombre del taller",
    "Nombre de la red",
    "Nombre de la empresa creativa",
    "Nombre del espacio o evento",
    "Titulo",
    "Título",
)
DATE_FIELDS = (
    "Fecha de presentación",
    "Fecha de inicio",
    "Fecha de creación",
    "Fecha de obtención del registro del INVIMA",
    "Registrado ante la c´mara el",
    "Fecha de registro ante la camara de comercio",
    "Fecha de otorgamiento de la licencia",
)
ID_FIELDS = {
    "contrato/registro": "contract/registration",
    "Número de registro": "registration",
    "Nit": "nit",
    "Nit o codigo de registro": "nit",
    "Número consecutivo del concepto": "concept number",
    "Gaceta Industrial de Publicación": "gazette",
}
EMPTY = {"", "n/a", "na", "no aplica", "ninguno", "null", "0", "-"}
# words that appear in titles but not in names
NOT_NAME = {"EN", "PARA", "Y", "EL", "CON", "POR", "A", "UN", "UNA", "SOBRE", "SU", "AL", "QUE", "THE", "OF", "AND"}


def _flat(s):
    return re.sub(r"\s+", " ", s or "").strip()


def author_lines(bq):
    """Names on their own source lines ('NAME,' + spaces) at the start of the item."""
    body = re.split(r"<br>\s*<b>|<i>", bq, maxsplit=1)[0]
    names = []
    for ln in body.splitlines():
        if not ln.strip():
            continue
        m = AUTHOR_LINE.match(ln)
        if not m:
            break
        n = clean(text(m.group(1)))
        if not n or len(n) > 80 or re.search(r"\d|:", n) or set(n.upper().split()) & NOT_NAME:
            break
        names.append(n)
    return names


def _is_owner(name, owner):
    na = norm(name)
    on = norm(owner.get("name")), norm(owner.get("citation_name"))
    return bool(na) and (na in on or bool(on[1] and set(na.split()) == set(on[1].split())))


def _person(name, owner, typ=None):
    own = _is_owner(name, owner)
    p = {
        "full_name": name,
        "id": owner["cod_rh"] if own else None,
        "external_ids": [{"provenance": "cvlac", "source": "scienti", "id": owner["cod_rh"]}] if own else [],
    }
    if typ:
        p["type"] = typ
    return p


def _date(s):
    """'2020-12-07 00:00:00.0' / 'Julio - 2015' / '2023 - Diciembre' / 'Julio de 2025' / '2015, Agosto' -> ISO."""
    s = s or ""
    m = ISO_DATE.search(s)
    if m:
        return "-".join(m.groups())
    my = month_year(s)
    if my and my["year"]:
        return f"{my['year']}-{my['month']:02d}" if my["month"] else str(my["year"])
    return None


def _url(u):
    u = u.rstrip(".,;:)]")
    return "http://" + u if u.lower().startswith("www.") else u


def _cut(v):
    """Field value that ran into the unlabeled tail: 'X, . En: Colombia, ,2017, 0 meses p' -> 'X'."""
    if v is None:
        return None
    v = re.split(r"\s*,?\s*\.?\s*\bEn:\s|\s+En\s+[A-ZÁÉÍÓÚ][a-záéíóú]+,", v)[0]
    v = clean(v)
    return None if v is None or v.lower() in EMPTY else v


def _add_id(ids, source, value):
    value = clean(value)
    if value and value.lower() not in EMPTY and not any(i["id"] == value and i["source"] == source for i in ids):
        ids.append({"source": source, "id": value})


def structure(it, bq, owner):
    """Add the structured fields to one generic section item (see the module docstring)."""
    flat = _flat(it.get("text"))
    f = dict(it.get("fields") or {})
    ids, out = [], {}

    # people listed before the title
    names = author_lines(bq)
    body = flat
    if names:
        prefix = ", ".join(names) + ","
        body = flat[len(prefix) :].strip() if flat.startswith(prefix) else flat
        out["authors"] = [_person(n, owner) for n in names]

    # labeled values that ran on into the tail
    for k in list(f):
        if k in (
            "contrato/registro",
            "Finalidad",
            "finalidad",
            "Vía de solicitud",
            "Institución solicitante",
            "Nombre comercial",
        ):
            f[k] = _cut(f[k])
        if re.fullmatch(YEAR, k):  # Signos distintivos: '2021': 'Registro:13778, Titular: ...'
            f.pop(k)
    for k in ("Nombre del taller", "Fecha de inicio", "Fecha de finalización", "Lugar de realización", "Ámbito", "Ciudad"):
        m = re.search(re.escape(k) + r":\s*([^,\n]+?)\s*(?:,\s*[A-ZÁÉÍÓÚ][\w ]*:|\n|$)", it.get("text") or "")
        if k not in f and m and clean(m.group(1)) not in (None, "null"):
            f[k] = clean(m.group(1))
    if f.get("Institución") and "Ciudad:" in f["Institución"]:  # Asesorías: 'X,Ciudad: Y'
        f["Institución"] = clean(f["Institución"].split("Ciudad:")[0])
    md = re.search(r"Medio de divulgación\s*:?\s*([^.]+)", flat)
    if "Medio de divulgación" in f and md:
        f["Medio de divulgación"] = clean(md.group(1))

    # title
    title = next((clean(f[k]) for k in TITLE_FIELDS if f.get(k)), None)
    m_pat = re.match(r"(\S+)\s+-\s+(.+?),\s*Institución:", flat)  # Patentes: 'NC2020/0015295 - TITLE, Institución:'
    m_quote = re.match(r'"+(.+?)"\s*Fecha de presentación', body)  # Boletines
    if not title and m_pat:
        title = clean(m_pat.group(2))
        _add_id(ids, "patent", m_pat.group(1))
    elif not title and m_quote:
        title = clean(m_quote.group(1))
    elif not title and (names or TITLE_END.search(body)):
        title = clean(TITLE_END.split(body, maxsplit=1)[0])
    if not title and it.get("type") and " - " not in it["type"] and not names:  # Asesorías, Secretos: name in the header
        title = clean(it["type"])
    if title:
        out["title"] = title

    # place
    for v in re.findall(r"\bEn:\s*([^,.:\n]+?)\s*(?=[,.\n]|$|Nombre de base|\s+Base de datos)", flat):
        v = clean(v)
        if not v or month_year(v):
            continue
        if v.isupper():
            out.setdefault("city", v)
        else:
            out.setdefault("country", v)
    m = re.search(r",\s*En\s+([A-ZÁÉÍÓÚ][a-záéíóú]+(?: [A-Za-záéíóú]+)*),\s*" + YEAR, flat)  # Signos distintivos
    if m:
        out.setdefault("country", m.group(1))
    if f.get("Ciudad"):
        out["city"] = clean(f["Ciudad"].split("-")[0])
    m = re.search(r"\ben\s+([^,]+?)\s+con\b", flat)  # Redes: 'Creada el: ..., en Amberes con participantes'
    if m and "Nombre de la red" in f:
        out["city"] = clean(m.group(1))
    if f.get("Lugar de realización"):  # Talleres creativos: a venue or a city
        out["place"] = clean(f["Lugar de realización"])

    # institution / publisher
    inst = f.get("Institución") or f.get("Institución que emite el registro") or f.get("en") or f.get("Titular del registro")
    if f.get("Institución solicitante"):
        inst = f["Institución solicitante"]
    m = re.search(r",\s*" + YEAR + r",\s*,\s*([^.]+?)\.\s*participación", flat)  # Cursos de corta duración
    if m:
        inst = m.group(1)
    if f.get("Revista") or f.get("Editorial"):  # Par evaluador
        out["venue"] = clean(re.sub(r",\s*" + YEAR + r".*$", "", f.get("Revista") or f.get("Editorial")))
    if inst:
        out["institution"] = clean(re.sub(r",\s*" + YEAR + r".*$", "", inst))
    m = re.search(r"\bEn:\s*[^,]+,\s*,\s*" + YEAR + r",\s*([^,]*?[A-Za-z][^,]*?)\s+p\.\s*\d*\s*$", flat)  # Ediciones
    if m and not re.search(r"\bmeses\b", m.group(1)):
        out["publisher"] = clean(m.group(1))

    # date, duration, pages, role, purpose
    date = next((_date(f[k]) for k in DATE_FIELDS if f.get(k)), None)
    if not date:
        m = re.search(r"Creada el:\s*(\S+)", flat) or re.search(r"\bEn:\s*([A-Za-zé]+\s*-\s*" + YEAR + ")", flat)
        m = m or re.search(r"\bEn:\s*[^,]+,\s*,\s*(" + YEAR + r"-\d\d-\d\d)", flat)  # Patentes
        m = m or re.search(r"Fecha solicitud:\s*([A-Za-z]+\s*-\s*" + YEAR + ")", flat)
        m = m or re.search(r"(" + YEAR + r",\s*[A-Z][a-z]+)\s*$", flat)  # Par evaluador: '2015, Agosto'
        date = _date(m.group(1)) if m else None
    if date:
        out["date"] = date
    m = re.search(r"(\d+)\s*(meses|semanas|horas|días|dias)\b", flat)
    if m and int(m.group(1)):
        out["duration"] = {"value": int(m.group(1)), "unit": {"dias": "días"}.get(m.group(2), m.group(2))}
    m = re.search(r"\bp\.\s*(\d+)\b", flat)
    if m and int(m.group(1)):
        out["pages"] = int(m.group(1))
    m = re.search(r"participación:\s*([^,]+)", flat)
    if m:
        out["role"] = clean(m.group(1))
    purpose = f.get("Finalidad") or f.get("finalidad")
    if purpose:
        out["purpose"] = purpose

    # people of other kinds
    if "Titulo" in f:  # Jurado en comités de evaluación: 'OWNER, Titulo: ... Nombre del orientado: A, B'
        jury = names or [n for n in (clean(x) for x in flat.split(", Titulo:")[0].split(",")) if n] if ", Titulo:" in flat else []
        out["authors"] = [_person(n, owner, "jury") for n in jury or [owner.get("name") or ""]] + [
            _person(n, owner, "student")
            for n in (clean(x) for x in re.split(r"[,;]|\s+[yY]\s+", f.get("Nombre del orientado") or ""))
            if n
        ]
        out["program"] = clean(f.get("programa académico"))
    for k, key in (("plataforma", "platform"), ("ambiente", "environment")):  # Softwares
        m = re.search(r"\b" + k + r":\s*([^,]+?)\s*,", flat)
        if m and clean(m.group(1)):
            out[key] = clean(m.group(1))
    m = re.search(r"Nombre del solicitante de la patente:\s*([^,]+?)\s*,", flat)
    if m and clean(m.group(1)):
        out["holder"] = clean(m.group(1))

    # identifiers
    for k, src in ID_FIELDS.items():
        if f.get(k):
            _add_id(ids, src, f[k])
    m = re.search(r"Registro:\s*([\w./-]+)", flat)  # Signos distintivos
    if m:
        _add_id(ids, "registration", m.group(1))
    m = re.search(r"Titular:\s*(.+)$", flat)
    if m:
        out["holder"] = clean(m.group(1))
    m = re.search(r"Nacional de Derechos de Autor:\s*([\w-]+)", flat)
    if m:
        _add_id(ids, "copyright registration", m.group(1))
    m = re.match(r"(.+?)\s+-\s+([\w./-]*\d[\w./-]*)\s*,\s*Nombre del titular", flat)  # Secretos: 'COMPANY - CODE ,'
    if m:
        out["holder"] = clean(f.get("Nombre del titular")) or clean(m.group(1))
        _add_id(ids, "trade secret", m.group(2))
    m = re.search(r"Gaceta Industrial de Publicación:\s*(\d+)", flat)
    if m:
        _add_id(ids, "gazette", m.group(1))
    db = f.get("Base de datos donde está incluido el registro") or f.get(
        "Nombre de base de datos donde está incluido el registro"
    )
    if db:
        out["database"] = clean(db)
        for k in it.get("keywords") or []:
            if re.fullmatch(r"[A-Z]{1,6}_?[A-Z]{0,4}\d{5,9}(?:\.\d+)?", k.strip()):
                _add_id(ids, "accession", k.strip())
    doi = find_doi(flat)
    if doi:
        _add_id(ids, "doi", doi)
    for v in re.findall(r"ISBN:?\s*([\dXx-]{10,17})", flat):
        _add_id(ids, "isbn", v)
    for v in re.findall(r"ISSN:?\s*(\d{4}-?\d{3}[\dXx])", flat):
        _add_id(ids, "issn", v)
    if ids:
        out["identifiers"] = ids

    # links written in the text
    lk = list(it.get("links") or [])
    seen = {x["url"] for x in lk}
    for u in URL_RE.findall(flat):
        u = _url(u)
        if u not in seen and len(u) > 10:
            seen.add(u)
            lk.append({"url": u, "label": None})
    if lk:
        out["links"] = lk

    new = {k: it[k] for k in ("type", "endorsed") if k in it}
    new.update(out)
    new.update({k: v for k, v in it.items() if k not in new})
    new["fields"] = {k: v for k, v in f.items() if v is not None} or None
    return new
