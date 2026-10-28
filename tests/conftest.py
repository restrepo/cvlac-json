import pathlib

import pytest

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def page():
    """Synthetic CvLAC page (fictitious researcher) with the real page's HTML structure."""
    return (FIXTURES / "cvlac_sintetico.html").read_text(encoding="latin-1")


@pytest.fixture(autouse=True)
def no_network(monkeypatch, tmp_path):
    """Fail any test that tries to reach the network, and keep caches and keys out of $HOME."""
    import urllib.request

    def blocked(*a, **k):
        raise AssertionError("tests must not use the network")

    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    from cvlac_json import ror, scienti

    monkeypatch.setattr(ror, "CACHE", str(tmp_path / "ror.json"))
    monkeypatch.setattr(scienti, "KEY_FILE", tmp_path / "apikey")
    monkeypatch.delenv("COLAV_APIKEY", raising=False)
