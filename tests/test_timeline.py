import numpy as np
import pytest

from audyum.timeline import finalize, fit_length, plan_windows, stitch


@pytest.mark.parametrize("duration", [0.7, 5.0, 8.0, 8.01, 15.0, 15.5, 23.96, 61.3, 600.0])
def test_windows_cover_video_with_overlap(duration):
    w = plan_windows(duration, 8, 1)
    assert w[0][0] == 0
    assert w[-1][0] + w[-1][1] == pytest.approx(duration)
    for s, d in w:
        assert s == int(s) and 0 < d <= 8
    for (s1, d1), (s2, _) in zip(w, w[1:], strict=False):
        assert s2 > s1 and s1 + d1 - s2 >= 1


def test_windows_do_not_leave_short_tail():
    assert plan_windows(15.5, 8, 1) == [(0.0, 8.0), (4.0, 8.0), (8.0, 7.5)]
    assert plan_windows(15.0, 8, 1) == [(0.0, 8.0), (7.0, 8.0)]


def test_stitch_length_and_no_gaps():
    sr = 1000
    segs = [(s, np.full((1, int(d * sr)), 0.5, np.float32)) for s, d in plan_windows(20.0, 8, 1)]
    out = stitch(segs, sr, 20.0)
    assert out.shape == (1, 20000)
    assert np.all(out > 0.49)  # nessun buco; la dissolvenza a potenza costante può salire fino a 0.5*sqrt(2)
    assert out.max() <= 0.5 * np.sqrt(2) + 1e-4


def test_stitch_matches_level_of_next_segment():
    sr = 1000
    a = np.full((1, 8000), 0.4, np.float32)
    b = np.full((1, 8000), 0.1, np.float32)  # 12 dB più basso: il guadagno si ferma a +6 dB
    out = stitch([(0.0, a), (7.0, b)], sr, 15.0)
    assert out[0, -1] == pytest.approx(0.2)


def test_finalize_peak_and_fades():
    sr = 1000
    x = np.full((1, 2000), 0.5, np.float32)
    y = finalize(x, sr, normalize=True)
    assert y[0, 0] == 0 and y[0, -1] == 0
    assert np.max(np.abs(y)) == pytest.approx(10 ** (-1 / 20), rel=1e-4)
    quiet = finalize(np.full((1, 2000), 0.2, np.float32), sr, normalize=False)
    assert np.max(quiet) == pytest.approx(0.2)


def test_fit_length():
    x = np.ones((1, 100), np.float32)
    assert fit_length(x, 100, 0.5).shape == (1, 50)
    assert fit_length(x, 100, 1.5).shape == (1, 150)
