import time

from searchpaper.cache import Cache


def test_cache_set_get(tmp_path):
    db = tmp_path / "cache.db"
    cache = Cache(str(db))
    cache.set("s2", "search", {"q": "foo"}, None, {"result": "bar"})
    val, meta = cache.get("s2", "search", {"q": "foo"}, None)
    assert val == {"result": "bar"}
    assert meta["from_cache"] is True


def test_cache_ttl_expiry(tmp_path):
    db = tmp_path / "cache.db"
    cache = Cache(str(db), default_ttl_seconds=1)
    cache.set("s2", "search", {"q": "foo"}, None, {"result": "bar"})
    time.sleep(1.1)
    val, meta = cache.get("s2", "search", {"q": "foo"}, None)
    assert val is None
    assert meta["from_cache"] is False


def test_cache_key_includes_fields(tmp_path):
    db = tmp_path / "cache.db"
    cache = Cache(str(db))
    cache.set("s2", "search", {"q": "foo"}, ["title"], {"result": "titles"})
    cache.set("s2", "search", {"q": "foo"}, ["abstract"], {"result": "abstracts"})
    v1, _ = cache.get("s2", "search", {"q": "foo"}, ["title"])
    v2, _ = cache.get("s2", "search", {"q": "foo"}, ["abstract"])
    assert v1 != v2
