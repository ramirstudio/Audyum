import dataclasses
import json

from audyum import ui_settings as u


def test_color_helpers():
    assert u.mix("#000000", "#FFFFFF", 0.5) == "#808080"
    assert u.lighten("#000000", 1) == "#FFFFFF"
    assert u.darken("#FFFFFF", 1) == "#000000"
    assert u.rgb_to_hex(300, -5, 12.4) == "#FF000C"


def test_roundtrip(tmp_path):
    p = tmp_path / "s.json"
    ui = dataclasses.replace(u.PRESETS["oceano"], bg_angle=45, accent1="#112233")
    u.save(ui, p)
    assert u.load(p) == ui


def test_missing_or_corrupt_file_gives_defaults(tmp_path):
    assert u.load(tmp_path / "nope.json") == u.UISettings()
    bad = tmp_path / "bad.json"
    bad.write_text("{non json", encoding="utf-8")
    assert u.load(bad) == u.UISettings()


def test_invalid_values_fall_back(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"bg_mode": "boh", "accent1": "rosso", "bg_angle": 725, "glow": 0,
                             "campo_sconosciuto": 1, "bg_mode2": "x"}), encoding="utf-8")
    ui = u.load(p)
    assert ui.bg_mode == "reference" and ui.accent1 == u.UISettings().accent1
    assert ui.bg_angle == 5 and ui.glow is False


def test_image_mode_without_file_falls_back(tmp_path):
    ui = u.UISettings(bg_mode="image", bg_image=str(tmp_path / "manca.png")).validated()
    assert ui.bg_mode == "reference"
    img = tmp_path / "f.png"
    img.write_bytes(b"x")
    assert u.UISettings(bg_mode="image", bg_image=str(img)).validated().bg_mode == "image"


def test_presets_are_valid_and_named():
    assert set(u.PRESETS) == set(u.PRESET_NAMES)
    for key, ui in u.PRESETS.items():
        assert ui.preset == key and ui.validated() == ui


def test_base_and_accent_end():
    assert u.PRESETS["grafite"].base() == "#17171A"
    assert u.PRESETS["grafite"].accent_end() == u.PRESETS["grafite"].accent1
    assert u.PRESETS["oceano"].accent_end() == "#3B8FD6"
