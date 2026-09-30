import hashlib
import http.server
import threading

import pytest

from audyum.downloads import URLFile, describe_path, fetch_url

DATA = bytes(range(256)) * 4000


class Handler(http.server.BaseHTTPRequestHandler):
    hits = 0

    def do_GET(self):
        type(self).hits += 1
        self.send_response(200)
        self.send_header("Content-Length", str(len(DATA)))
        self.end_headers()
        self.wfile.write(DATA)

    def log_message(self, *a):
        pass


@pytest.fixture
def server():
    Handler.hits = 0
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/file.bin"
    srv.shutdown()


def test_download_verifies_and_is_not_repeated(tmp_path, server):
    item = URLFile(server, tmp_path / "sub" / "f.bin", "prova", hashlib.md5(DATA).hexdigest())
    msgs = []
    assert fetch_url(item, lambda m, f: msgs.append(f)).read_bytes() == DATA
    assert msgs and msgs[-1] == 1.0
    fetch_url(item, lambda m, f: None)
    assert Handler.hits == 1  # il secondo giro riconosce il file già completo


def test_wrong_md5_is_rejected_and_removed(tmp_path, server):
    item = URLFile(server, tmp_path / "f.bin", "prova", "0" * 32)
    with pytest.raises(RuntimeError, match="corrotto"):
        fetch_url(item, lambda m, f: None)
    assert not (tmp_path / "f.bin").exists() and not (tmp_path / "f.bin.part").exists()


def test_without_md5_size_is_checked(tmp_path, server):
    item = URLFile(server, tmp_path / "f.bin", "prova")
    assert fetch_url(item, lambda m, f: None).stat().st_size == len(DATA)


def test_describe_path_reports_each_level(tmp_path):
    f = tmp_path / "a" / "b.txt"
    f.parent.mkdir()
    f.write_text("x")
    out = describe_path(f)
    assert "b.txt" in out and out.count("reparse=") >= 3
