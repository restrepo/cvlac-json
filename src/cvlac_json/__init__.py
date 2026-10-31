"""cvlac-json: turn a public CvLAC page (Minciencias, Colombia) into one JSON document.

>>> from cvlac_json import extract
>>> data = extract("0000026549")            # downloads the page; Scienti ids if an apis.colav.co key is set
>>> data["profile"]["Nombre"], len(data["works"])
"""

from importlib.metadata import PackageNotFoundError, version

from .jsonld import to_jsonld
from .parser import build, extract, fetch, normalize_cod_rh

try:
    __version__ = version("cvlac-json")
except PackageNotFoundError:  # running from a source tree without installing
    __version__ = "0.0.0"

__all__ = ["__version__", "build", "extract", "fetch", "normalize_cod_rh", "to_jsonld"]
