import os
import sys

import pytest

from audyum.downloads import heal_hf_cache


@pytest.mark.skipif(sys.platform == "win32", reason="richiede permessi per creare collegamenti")
def test_symlinks_become_real_files_without_extra_space(tmp_path):
    hub = tmp_path / "hub" / "models--a--b"
    blobs, snap = hub / "blobs", hub / "snapshots" / "abc" / "weights"
    blobs.mkdir(parents=True)
    snap.mkdir(parents=True)
    (blobs / "h1").write_bytes(b"pesi" * 1000)
    os.symlink(os.path.join("..", "..", "..", "blobs", "h1"), snap / "modello.pth")

    assert heal_hf_cache(tmp_path / "hub") == 1
    f = snap / "modello.pth"
    assert not f.is_symlink() and f.read_bytes() == b"pesi" * 1000
    assert os.stat(f).st_ino == os.stat(blobs / "h1").st_ino  # hardlink: nessuna copia
    assert heal_hf_cache(tmp_path / "hub") == 0  # seconda volta: niente da fare


def test_missing_cache_is_fine(tmp_path):
    assert heal_hf_cache(tmp_path / "non_esiste") == 0
