import io

from cvlac_json import extract, ror, scienti
from cvlac_json.cli import main
from cvlac_json.parser import stages
from cvlac_json.progress import Progress


class Tty(io.StringIO):
    encoding = "utf-8"

    def isatty(self):
        return True


def test_stage_names():
    assert stages(html=None, scienti="auto", ror=True)[0] == "CvLAC page"
    assert stages(html="<html>", scienti="off", ror=False) == ["Parsing", "Finishing"]
    assert "Scienti products" in stages(scienti="full") and "ROR" in stages()


def test_fraction_and_render():
    p = Progress(["a", "b", "c", "d"], stream=Tty(), enabled=True)
    p("c", 1, 2)  # half of the third stage
    assert p.fraction() == (2 + 0.5) / 4
    line = p.render(width=60)
    assert len(line) < 60 and "62%" in line and "3/4" in line and "c 1/2" in line


def test_ascii_fallback():
    class Ascii(Tty):
        encoding = "ascii"

    p = Progress(["a", "b"], stream=Ascii(), enabled=True)
    p("b")
    assert "#" in p.render(40) and "█" not in p.render(40)


def test_disabled_when_not_a_terminal():
    out = io.StringIO()  # isatty() is False
    with Progress(["a", "b"], stream=out) as p:
        p("b")
        p.write("a message")
    assert out.getvalue() == "a message\n"


def test_draws_and_clears_on_a_terminal():
    out = Tty()
    with Progress(["a", "b"], stream=out, interval=0.01) as p:
        p("b")
        p.write("log line")
    text = out.getvalue()
    assert "log line\n" in text and "2/2 b" in text
    assert text.endswith("\r\x1b[2K")  # the bar is erased at the end


def test_extract_reports_stages_in_order(page, monkeypatch):
    calls = []

    def fake_get(path, key, **params):
        if path == "/scienti/info":
            return [{"institution": "udea", "model_year": "2024"}]
        if path == "/scienti/product":
            return [{"COD_RH": "0000000001", "COD_PRODUCTO": "1", "TXT_NME_PROD": "Producto cualquiera de prueba sintética"}]
        return []

    monkeypatch.setattr(scienti, "get", fake_get)
    monkeypatch.setattr(ror, "lookup", lambda name, cache: None)
    extract(
        "1",
        html=page,
        scienti="auto",
        apikey="test-key",
        ror=True,
        log=lambda m: None,
        progress=lambda stage, done=None, total=None: calls.append(stage),
    )
    order = [s for i, s in enumerate(calls) if i == 0 or calls[i - 1] != s]
    assert order == stages(html=page, scienti="auto", ror=True)


def test_cli_no_progress_flag(tmp_path, capsys):
    html = tmp_path / "p.html"
    html.write_bytes((__import__("pathlib").Path(__file__).parent / "fixtures" / "cvlac_sintetico.html").read_bytes())
    assert (
        main(["1", "--html", str(html), "--scienti", "off", "--ror", "off", "--no-progress", "-o", str(tmp_path / "o.json")]) == 0
    )
    err = capsys.readouterr().err
    assert "\r" not in err and "wrote" in err
