from __future__ import annotations

import json
from pathlib import Path

import osu_beatmap_preview as preview
import pytest
from PIL import Image, ImageChops


@pytest.fixture(scope="module")
def catch_render_config(tmp_path_factory: pytest.TempPathFactory) -> str:
    tmp_path = tmp_path_factory.mktemp("ctb-mods")
    cache = tmp_path / "cache" / "osu-download-cache"
    cache.mkdir(parents=True)
    for bid, mode in ((999900001, 2), (999900002, 0), (999900003, 2), (999900004, 0)):
        hit_objects = (
            "128,192,1000,1,0,0:0:0:0:\n480,192,1100,1,0,0:0:0:0:"
            if bid in (999900003, 999900004)
            else "128,192,1000,1,0,0:0:0:0:\n256,192,1500,1,0,0:0:0:0:\n384,192,2000,1,0,0:0:0:0:"
        )
        (cache / f"{bid}.osu").write_text(
            f"""osu file format v14

[General]
Mode:{mode}
PreviewTime:{250 if bid in (999900003, 999900004) else 1000}

[Metadata]
Title:Catch Hidden regression
Artist:Test
Creator:Test
Version:Test
BeatmapID:{bid}

[Difficulty]
HPDrainRate:5
CircleSize:5
OverallDifficulty:5
ApproachRate:5
SliderMultiplier:1.4
SliderTickRate:1

[TimingPoints]
0,500,4,1,0,100,1,0

[Colours]
Combo1:30,120,220

[HitObjects]
{hit_objects}
""",
            encoding="utf-8",
        )
    return json.dumps(
        {
            "paths": {
                "CACHE_DIR": (tmp_path / "cache").as_posix(),
                "OUTPUT_DIR": (tmp_path / "outputs").as_posix(),
                "LOG_DIR": (tmp_path / "logs").as_posix(),
            },
            "render": {
                "catch": {
                    "gif": {
                        "structure": {"ROW_COUNT": 1, "IMAGES_PER_ROW": 1},
                        "style": {"SHOW_TIME_LABEL": False},
                    }
                }
            },
        }
    )


@pytest.mark.parametrize("convert", [None, "ctb"])
@pytest.mark.parametrize("mods", ["hd", "hd+ez", "hd+hr", "hd+dt", "hd+ht"])
def test_catch_gif_supports_hidden_and_changes_visibility(
    catch_render_config: str, convert: preview.ConvertMode | None, mods: str
) -> None:
    bid = 999900001 if convert is None else 999900002
    frames = []
    for selected_mods in (mods, mods.removeprefix("hd").lstrip("+") or None):
        result = preview.generate_preview(
            bid,
            convert=convert,
            format="gif",
            mods=selected_mods,
            times="preview",
            duration_time=0.5,
            fps=20,
            config=catch_render_config,
        )
        output = Path(result["preview-img"])
        assert output.is_file()
        with Image.open(output) as image:
            assert image.format == "GIF"
            assert image.n_frames == 10
            frames.append(image.convert("RGB"))

    assert ImageChops.difference(*frames).getbbox() is not None


def test_catch_png_still_rejects_hidden(catch_render_config: str) -> None:
    with pytest.raises(preview.PreviewError, match="HD is not supported for catch PNG"):
        preview.generate_preview(999900001, format="png", mods="hd", config=catch_render_config)


@pytest.mark.parametrize("convert", [None, "ctb"])
@pytest.mark.parametrize("mods", [None, "hd"])
def test_catch_gif_default_hyperdash_outline_is_red(
    catch_render_config: str, convert: preview.ConvertMode | None, mods: str | None
) -> None:
    result = preview.generate_preview(
        999900003 if convert is None else 999900004,
        convert=convert,
        format="gif",
        mods=mods,
        times="preview",
        duration_time=0.1,
        fps=20,
        config=catch_render_config,
    )
    with Image.open(result["preview-img"]) as image:
        colors = image.convert("RGB").getcolors(image.width * image.height)
    assert colors is not None
    red_pixels = sum(count for count, (r, g, b) in colors if r >= 250 and g <= 5 and b <= 5)
    assert red_pixels >= 20, sorted(colors, reverse=True)[:12]
