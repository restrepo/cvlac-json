import json

import pytest

from cvlac_json import __version__
from cvlac_json.cli import main


def test_cli_writes_json(tmp_path, capsys):
    html = tmp_path / "page.html"
    html.write_bytes((__import__("pathlib").Path(__file__).parent / "fixtures" / "cvlac_sintetico.html").read_bytes())
    out = tmp_path / "out.json"
    assert main(["1", "--html", str(html), "--scienti", "off", "--ror", "off", "-o", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["cod_rh"] == "0000000001" and len(data["works"]) == 2
    assert "wrote" in capsys.readouterr().err


def test_cli_stdout(tmp_path, capsys):
    html = __import__("pathlib").Path(__file__).parent / "fixtures" / "cvlac_sintetico.html"
    assert main(["1", "--html", str(html), "--scienti", "off", "--ror", "off", "-o", "-"]) == 0
    assert json.loads(capsys.readouterr().out)["profile"]["Sexo"] == "Femenino"


def test_cli_bad_cod_rh(capsys):
    assert main(["12x"]) == 2
    assert "COD_RH" in capsys.readouterr().err


def test_cli_version(capsys):
    with pytest.raises(SystemExit):
        main(["--version"])
    assert __version__ in capsys.readouterr().out
