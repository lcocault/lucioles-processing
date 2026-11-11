import json

import pytest

from lucioles_processing.adapters.download import download

BODY = b'{"type": "FeatureCollection", "features": []}'


@pytest.fixture
def server(http_server):
    http_server.files["/communes.geojson"] = BODY
    return http_server


def test_first_download(server, tmp_path):
    target = tmp_path / "c" / "communes.geojson"
    result = download(server.url("/communes.geojson"), target)
    assert result.status == "downloaded"
    assert target.read_bytes() == BODY
    assert result.path == target and result.origin == server.url("/communes.geojson")
    assert result.sha256 and result.version.startswith('"')  # l'ETag sert de version
    meta = json.loads((tmp_path / "c" / "communes.geojson.meta.json").read_text())
    assert meta["sha256"] == result.sha256 and meta["size"] == len(BODY)
    assert not list(tmp_path.rglob("*.part"))


def test_unchanged_file_is_not_downloaded_again(server, tmp_path):
    target = tmp_path / "communes.geojson"
    first = download(server.url("/communes.geojson"), target)
    second = download(server.url("/communes.geojson"), target)
    assert second.status == "unchanged"
    assert second.version == first.version and second.sha256 == first.sha256
    # la 2e requête était conditionnelle : le serveur a répondu 304, sans renvoyer le contenu
    assert "If-None-Match" in server.requests[1][1] and "If-Modified-Since" in server.requests[1][1]


def test_changed_file_is_replaced(server, tmp_path):
    target = tmp_path / "communes.geojson"
    first = download(server.url("/communes.geojson"), target)
    server.files["/communes.geojson"] = BODY + b" "
    second = download(server.url("/communes.geojson"), target)
    assert second.status == "downloaded"
    assert target.read_bytes() == BODY + b" "
    assert second.sha256 != first.sha256 and second.version != first.version


def test_server_without_validators_same_content_is_unchanged(server, tmp_path):
    server.etags = False
    target = tmp_path / "communes.geojson"
    assert download(server.url("/communes.geojson"), target).status == "downloaded"
    again = download(server.url("/communes.geojson"), target)
    assert again.status == "unchanged"  # retéléchargé mais contenu identique
    assert again.version  # repli sur l'empreinte
    assert server.requests[1][1] == {}


def test_refresh_never_uses_the_copy_without_network(server, tmp_path):
    target = tmp_path / "communes.geojson"
    download(server.url("/communes.geojson"), target)
    result = download(server.url("/communes.geojson"), target, refresh="never")
    assert result.status == "cached" and server.count("/communes.geojson") == 1


def test_refresh_never_still_downloads_when_missing(server, tmp_path):
    result = download(server.url("/communes.geojson"), tmp_path / "x.geojson", refresh="never")
    assert result.status == "downloaded"


def test_server_error_with_cached_copy_is_unverified(server, tmp_path):
    target = tmp_path / "communes.geojson"
    first = download(server.url("/communes.geojson"), target)
    server.status = 503
    result = download(server.url("/communes.geojson"), target)
    assert result.status == "unverified" and result.sha256 == first.sha256
    assert target.read_bytes() == BODY


def test_unreachable_server_with_cached_copy_is_unverified(server, tmp_path):
    target = tmp_path / "communes.geojson"
    url = server.url("/communes.geojson")
    download(url, target)
    server.close()
    assert download(url, target, timeout=2).status == "unverified"


def test_server_error_without_copy_raises(server, tmp_path):
    server.status = 503
    with pytest.raises(OSError):
        download(server.url("/communes.geojson"), tmp_path / "x.geojson")
    assert not (tmp_path / "x.geojson").exists()


def test_not_found_always_raises_even_with_a_copy(server, tmp_path):
    target = tmp_path / "communes.geojson"
    download(server.url("/communes.geojson"), target)
    with pytest.raises(OSError, match="404"):
        download(server.url("/absent.geojson"), target)
    assert target.read_bytes() == BODY


def test_truncated_download_is_rejected_and_keeps_the_previous_copy(server, tmp_path):
    target = tmp_path / "communes.geojson"
    download(server.url("/communes.geojson"), target)
    server.files["/communes.geojson"] = BODY + b"nouveau"
    server.truncate = True
    server.etags = False  # force le retéléchargement
    with pytest.raises(OSError):
        download(server.url("/communes.geojson"), target)
    assert target.read_bytes() == BODY
    assert not list(tmp_path.glob("*.part"))


def test_corrupt_metadata_triggers_a_download(server, tmp_path):
    target = tmp_path / "communes.geojson"
    download(server.url("/communes.geojson"), target)
    (tmp_path / "communes.geojson.meta.json").write_text("{pas du json")
    assert download(server.url("/communes.geojson"), target).status == "downloaded"


def test_unknown_refresh_mode(tmp_path):
    with pytest.raises(ValueError, match="refresh"):
        download("http://x", tmp_path / "a", refresh="parfois")
