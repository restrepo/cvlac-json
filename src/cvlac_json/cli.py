"""Command line: ``cvlac-json COD_RH [-o OUT.json] ...``."""

import argparse
import json
import sys

from . import __version__
from .parser import extract, fetch, normalize_cod_rh, stages
from .progress import Progress


def build_parser():
    ap = argparse.ArgumentParser(
        prog="cvlac-json",
        description="Build a complete JSON from a researcher's public CvLAC page (Minciencias, Colombia).",
    )
    ap.add_argument("cod_rh", help="10-digit SCIENTI/CvLAC id (leading zeros are added if missing)")
    ap.add_argument("-o", "--output", help="output JSON (default cvlac_<COD_RH>.json; '-' for standard output)")
    ap.add_argument("--html", help="parse this saved page instead of downloading it")
    ap.add_argument("--save-html", help="also save the downloaded page here")
    ap.add_argument(
        "--scienti",
        choices=["auto", "full", "off"],
        default="auto",
        help="auto (default): add the Scienti ids of matching entries when an apis.colav.co key is available; "
        "full: also add the Scienti records missing from the page; off: public page only",
    )
    ap.add_argument("--institution", help="Scienti dump (udea, univalle, uec, unaula; default: first that has the COD_RH)")
    ap.add_argument("--model-year", help="Scienti model year (default: the latest of that institution)")
    ap.add_argument(
        "--apikey",
        help="apis.colav.co key for this run, overriding $COLAV_APIKEY and ~/.config/colav/apikey "
        '(it stays in the shell history; prefer --apikey "$(cat FILE)")',
    )
    ap.add_argument(
        "--siiu",
        choices=["auto", "off"],
        default="auto",
        help="with Scienti on, add the SIIU code of projects with the same title and a compatible year (default auto)",
    )
    ap.add_argument("--ror", choices=["auto", "off"], default="auto", help="look institutions up in the ROR API (default auto)")
    ap.add_argument(
        "--no-progress",
        action="store_true",
        help="do not show the progress bar (it is shown only when standard error is a terminal)",
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        cod = normalize_cod_rh(a.cod_rh)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    page = None
    if a.html:
        with open(a.html, encoding="latin-1") as fh:
            page = fh.read()
    ror = a.ror == "auto"
    names = stages(html=page, scienti=a.scienti, ror=ror, siiu=a.siiu == "auto")
    bar = Progress(names, stream=sys.stderr, enabled=False if a.no_progress else None)
    with bar:
        if page is None and a.save_html:  # download here to keep a copy; extract() then parses it
            bar("CvLAC page")
            page = fetch(cod)
            with open(a.save_html, "w", encoding="latin-1", errors="replace") as fh:
                fh.write(page)
        data = extract(
            cod,
            html=page,
            scienti=a.scienti,
            institution=a.institution,
            model_year=a.model_year,
            apikey=a.apikey,
            ror=ror,
            siiu=a.siiu == "auto",
            log=bar.write,
            progress=bar,
        )
    out = a.output or f"cvlac_{cod}.json"
    text = json.dumps(data, ensure_ascii=False, indent=1)
    if out == "-":
        sys.stdout.write(text + "\n")
    else:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
    c = data["counts"]
    print(
        f"wrote {out}: {data['profile'].get('Nombre') or '?'} | works {c['works']} (endorsed {c['endorsed_works']}), "
        f"projects {c['projects']}, events {c['events']}, other sections {len(data['sections'])}",
        file=sys.stderr,
    )
    return 0
