from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import osu_beatmap_preview as preview
import pytest


def test_generate_preview_decodes_renderer_result(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_generate(bid: str, **kwargs: object) -> str:
        captured.update({"bid": bid, **kwargs})
        return json.dumps({"preview-img": "/tmp/preview.gif"})

    monkeypatch.setattr(preview, "generate_preview_json", fake_generate)

    result = preview.generate_preview(
        123,
        format="gif",
        mods="hd+hr",
        times="preview+12.5",
        duration_time=8.0,
        fps=30,
        scale=1.5,
    )

    assert result == {"preview-img": "/tmp/preview.gif"}
    assert captured["bid"] == "123"
    assert captured["format"] == "gif"
    assert captured["mods"] == "hd+hr"
    assert captured["times"] == "preview+12.5"
    assert captured["duration_time"] == 8.0
    assert captured["fps"] == 30
    assert captured["scale"] == 1.5


def test_generate_preview_rejects_non_object_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(preview, "generate_preview_json", lambda *_args, **_kwargs: "[]")

    with pytest.raises(preview.PreviewError, match="non-object"):
        preview.generate_preview(123)


async def test_generate_preview_async_uses_same_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        preview,
        "generate_preview_json",
        lambda *_args, **_kwargs: '{"preview-img":"preview.png"}',
    )

    assert await preview.generate_preview_async(456, format="png") == {"preview-img": "preview.png"}


def test_native_extension_uses_updated_version() -> None:
    assert preview.__version__ == "0.1.15"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"format": "gif", "gif_clip": True}, "no longer supported"),
        ({"format": "gif", "times": "NaN"}, "finite"),
        ({"format": "gif", "preview_30s": True}, "mp4"),
        ({"format": "png", "gap": 120.0, "config": "{}"}, "custom config"),
    ],
)
def test_native_argument_compatibility_validation(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        preview.generate_preview(123, **kwargs)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"fps": 0}, "fps"),
        ({"duration_time": 0.0}, "duration time"),
        ({"scale": 0.0}, "scale"),
        ({"mods": "at"}, "AT"),
    ],
)
def test_native_request_forwards_options_to_renderer(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(preview.PreviewError, match=message):
        preview.generate_preview(123, **kwargs)


@pytest.mark.parametrize("spacing", [None, "most", "auto", "180BPM"])
def test_native_gap_renders_taiko_png(tmp_path: Path, spacing: str | None) -> None:
    # 独立进程及临时缓存隔离原生配置，验证 gap 映射到当前渲染器配置。
    script = """
import sys
import json
from pathlib import Path
import osu_beatmap_preview as preview
from PIL import Image

cache = Path(sys.argv[1]) / 'osu-beatmap-preview' / 'osu-download-cache'
cache.mkdir(parents=True)
(cache / '999940001.osu').write_text(
    'osu file format v14\\n[General]\\nMode:1\\n'
    '[Difficulty]\\nOverallDifficulty:5\\nHPDrainRate:5\\n'
    'SliderMultiplier:1.4\\nSliderTickRate:1\\n'
    '[TimingPoints]\\n0,500,4,1,0,100,1,0\\n'
    '[HitObjects]\\n0,0,1000,1,0\\n0,0,1500,1,2\\n', encoding='utf-8'
)
spacing = json.loads(sys.argv[2])
options = (
    {'gap': 120} if spacing is None else
    {'config': json.dumps({'render': {'taiko': {'png': {'style': {'SPACING_PER_BPM': spacing}}}}})}
)
result = preview.generate_preview(999940001, format='png', scale=0.25, **options)
with Image.open(result['preview-img']) as image:
    assert image.format == 'PNG'
    assert image.width > 0 and image.height > 0
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path), json.dumps(spacing)],
        env={**os.environ, "TEMP": str(tmp_path), "TMP": str(tmp_path), "TMPDIR": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
