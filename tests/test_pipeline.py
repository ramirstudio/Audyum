import threading

import av
import numpy as np
import pytest

from audyum.media import Cancelled, probe, sample_frames
from audyum.pipeline import JobSettings, run_job
from conftest import make_video


def test_sample_frames_rates(tmp_path, tone_engine):
    video = make_video(tmp_path / "in.mp4", 10.36)
    sampled = sample_frames(video, tone_engine.frame_specs)
    clip, sync = sampled.streams
    assert clip.shape[1:] == (32, 32, 3) and sync.shape[1:] == (24, 24, 3)
    assert len(clip) == 83 and len(sync) == 259  # istanti k/fps fino all'ultimo fotogramma (10.32 s)
    assert sampled.video_duration == pytest.approx(10.36)
    first = sampled.window(7.0, 3.0)
    assert len(first[0]) == 24 and len(first[1]) == 75


def test_end_to_end_with_two_variants(tmp_path, tone_engine):
    video = make_video(tmp_path / "clip.mp4", 17.2)
    messages = []
    results = run_job(video, tone_engine, JobSettings(variants=2, seed=10), tmp_path / "out",
                      lambda m, f: messages.append((m, f)))
    assert [r.seed for r in results] == [10, 11]
    assert len(tone_engine.calls) == 3  # 17.2 s → finestre 0-8, 5-13, 10-17.2
    for r in results:
        assert r.video.suffix == ".mp4" and r.wav.exists()
        with av.open(str(r.video)) as c:
            assert len(c.streams.video) == 1 and len(c.streams.audio) == 1
            a = c.streams.audio[0]
            assert a.codec_context.name == "aac" and a.rate == tone_engine.sample_rate
            samples = sum(f.samples for f in c.decode(audio=0))
            assert abs(samples / a.rate - 17.2) < 0.1
        with av.open(str(r.video)) as c, av.open(str(video)) as src:
            assert sum(1 for p in c.demux(video=0) if p.size) == sum(1 for p in src.demux(video=0) if p.size)
        with av.open(str(r.wav)) as c:
            pcm = np.concatenate([f.to_ndarray() for f in c.decode(audio=0)], axis=1)
            assert c.streams.audio[0].codec_context.name == "pcm_s24le"
            assert pcm.shape[1] == int(round(17.2 * tone_engine.sample_rate))
    assert messages[-1] == ("Fatto", 1.0)


def test_non_mp4_codec_goes_to_mkv(tmp_path, tone_engine):
    video = make_video(tmp_path / "clip.mkv", 3.0, codec="ffv1")
    (r,) = run_job(video, tone_engine, JobSettings(seed=1), tmp_path, lambda m, f: None)
    assert r.video.suffix == ".mkv"
    assert probe(r.video).has_audio


def test_cancel_stops_reading(tmp_path, tone_engine):
    video = make_video(tmp_path / "c.mp4", 4.0)
    ev = threading.Event()
    ev.set()
    with pytest.raises(Cancelled):
        sample_frames(video, tone_engine.frame_specs, cancel=ev)
