import numpy as np
import pytest

from audyum.media import FrameSpec, probe, sample_frames
from conftest import make_asym_video, set_mp4_rotation

SPEC = [FrameSpec(8.0, 32, "squash")]


def first_frame(path):
    return sample_frames(path, SPEC).streams[0][0].astype(int)


def test_unrotated_video(tmp_path):
    v = make_asym_video(tmp_path / "a.mp4")
    info = probe(v)
    assert (info.width, info.height, info.rotation) == (96, 64, 0)


@pytest.mark.parametrize("degrees,k", [(90, 1), (180, 2), (270, 3)])
def test_rotation_is_read_and_applied(tmp_path, degrees, k):
    plain = make_asym_video(tmp_path / "plain.mp4")
    rotated = make_asym_video(tmp_path / "rot.mp4")
    set_mp4_rotation(rotated, degrees)

    info = probe(rotated)
    assert info.rotation == degrees
    assert (info.width, info.height) == ((64, 96) if degrees in (90, 270) else (96, 64))

    expected = np.rot90(first_frame(plain), k)  # antiorario, come un lettore video
    assert np.abs(first_frame(rotated) - expected).max() == 0
