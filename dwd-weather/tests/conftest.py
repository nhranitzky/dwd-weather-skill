import pytest


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    """Redirect the geocoding cache to a temp dir so tests don't pollute
    the real cache and are fully isolated from each other."""
    import scripts.utils as utils
    monkeypatch.setattr(utils, "CACHE_DIR", tmp_path / "cache")
