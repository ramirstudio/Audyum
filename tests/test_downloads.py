import hashlib
import http.server
import threading

import pytest

from audyum.downloads import NotEnoughSpace, URLFile, describe_path, fetch_url

DATA = bytes(range(256)) * 4000


class Handler(http.server.BaseHTTPRequestHandler):
    hits = 0
    cut_first = False  # al primo tentativo chiude la connessione a metà, come una rete instabile

    def do_GET(self):
        cls = type(self)
        cls.hits += 1
        start = 0
        rng = self.headers.get("Range")
        if rng:
            start = int(rng.split("=")[1].split("-")[0])
        body = DATA[start:]
        self.send_response(206 if rng else 200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if cls.cut_first and cls.hits == 1:
            self.wfile.write(body[: len(body) // 3])
            self.wfile.flush()
            self.connection.close()
            return
        self.wfile.write(body)

    def log_message(self, *a):
        pass


@pytest.fixture
def server():
    Handler.hits, Handler.cut_first = 0, False
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


def test_interrupted_download_resumes_by_itself(tmp_path, server, monkeypatch):
    Handler.cut_first = True
    monkeypatch.setattr(threading.Event, "wait", lambda self, timeout=None: False)  # niente attese vere
    cancel = threading.Event()
    item = URLFile(server, tmp_path / "f.bin", "prova", hashlib.md5(DATA).hexdigest())
    msgs = []
    assert fetch_url(item, lambda m, f: msgs.append(m), cancel).read_bytes() == DATA
    assert Handler.hits == 2
    assert any("riprovo" in m for m in msgs)


def test_wrong_md5_is_rejected_and_removed(tmp_path, server):
    item = URLFile(server, tmp_path / "f.bin", "prova", "0" * 32)
    with pytest.raises(RuntimeError, match="corrotto"):
        fetch_url(item, lambda m, f: None)
    assert not (tmp_path / "f.bin").exists() and not (tmp_path / "f.bin.part").exists()


def test_without_md5_size_is_checked(tmp_path, server):
    item = URLFile(server, tmp_path / "f.bin", "prova")
    assert fetch_url(item, lambda m, f: None).stat().st_size == len(DATA)


def test_not_enough_space_is_explained(tmp_path, server, monkeypatch):
    import shutil
    from collections import namedtuple

    usage = namedtuple("usage", "total used free")
    monkeypatch.setattr(shutil, "disk_usage", lambda p: usage(10, 10, 1000))
    with pytest.raises(NotEnoughSpace, match="Spazio insufficiente"):
        fetch_url(URLFile(server, tmp_path / "f.bin", "prova"), lambda m, f: None)


def test_describe_path_reports_each_level(tmp_path):
    f = tmp_path / "a" / "b.txt"
    f.parent.mkdir()
    f.write_text("x")
    out = describe_path(f)
    assert "b.txt" in out and out.count("reparse=") >= 3
