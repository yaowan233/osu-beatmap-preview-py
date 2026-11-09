from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import osu_beatmap_preview as preview
import pytest


@pytest.mark.parametrize("bid", [None, "", "  "])
def test_preview_requires_a_source(bid: str | None) -> None:
    with pytest.raises(ValueError, match="provide bid|bid must not be empty"):
        preview.generate_preview(bid)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"osu_file": "map.txt"}, "osu-file"),
        ({"osz_file": "map.zip"}, "osz-file"),
        ({"osu_file": ""}, "must not be empty"),
        ({"osz_file": ""}, "must not be empty"),
        ({"osu_file": "map.osu", "format": "mp4"}, "local .osu input"),
        ({"osu_file": "map.osu", "output_dir": ""}, "output-dir"),
    ],
)
def test_local_source_options_use_upstream_validation(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(preview.PreviewError, match=message):
        preview.generate_preview(**kwargs)


# 独立进程隔离原生配置，并使用本地谱面、压缩包和 PCM 音频验证完整链路。
RENDER_LOCAL = r"""
import asyncio
import io
import json
import sys
import wave
import zipfile
from pathlib import Path

import osu_beatmap_preview as preview
from PIL import Image

root, case = Path(sys.argv[1]).resolve(), sys.argv[2]
root = root / '上传 [谱面]'
root.mkdir()
cases = {
    'osu_png': (0, 'png', 'osu'),
    'osu_gif': (3, 'gif', 'osu'),
    'osu_convert_gif': (0, 'gif', 'osu'),
    'osz_png': (1, 'png', 'osz'),
    'osz_gif': (2, 'gif', 'osz'),
    'osz_mp4': (0, 'mp4', 'osz'),
    'combined_mp4': (0, 'mp4', 'combined'),
    'difficulty_selection': (0, 'png', 'osz'),
}
mode, fmt, source = cases[case]

def beatmap(bid, title):
    metadata_id = f'BeatmapID:{bid}\n' if bid is not None else ''
    return (
        f'osu file format v14\n[General]\nMode:{mode}\n'
        'AudioFilename:audio.wav\nPreviewTime:1000\n'
        f'[Metadata]\nTitle:{title}\nArtist:Test\nVersion:Normal\n{metadata_id}'
        '[Difficulty]\nCircleSize:4\nOverallDifficulty:5\nHPDrainRate:5\n'
        'ApproachRate:5\nSliderMultiplier:1.4\nSliderTickRate:1\n'
        '[TimingPoints]\n0,500,4,1,0,100,1,0\n'
        '[HitObjects]\n100,100,1000,1,0\n200,100,1500,1,0\n'
    )

local = root / '本地谱面.osu'
local.write_text(beatmap(None if case == 'osu_png' else 42, 'External'), encoding='utf-8')
audio = io.BytesIO()
with wave.open(audio, 'wb') as wav:
    wav.setparams((2, 2, 8000, 0, 'NONE', 'not compressed'))
    wav.writeframes(bytes(4 * 8000 * 4))
archive = root / '本地谱面包.OSZ'
with zipfile.ZipFile(archive, 'w') as z:
    z.writestr('first.OSU', beatmap(None if case == 'osz_mp4' else 42, 'First'))
    if case == 'difficulty_selection':
        z.writestr('second.osu', beatmap(43, 'Second'))
    z.writestr('audio.wav', audio.getvalue())
config = json.dumps({
    'paths': {'CACHE_DIR': str(root/'cache'), 'LOG_DIR': str(root/'logs')},
    'render': {name: {'gif': {'structure': {'ROW_COUNT': 1, 'IMAGES_PER_ROW': 1}}}
               for name in ('standard', 'taiko', 'catch', 'mania')},
})
kwargs = dict(format=fmt, scale=0.25, config=config, output_dir=root/'output')
if source in ('osu', 'combined'):
    kwargs['osu_file'] = local
if source in ('osz', 'combined'):
    kwargs['osz_file'] = archive

if case == 'difficulty_selection':
    def fails(expected, **source):
        try:
            preview.generate_preview(format='png', scale=0.25, config=config,
                                     output_dir=root/'output', **source)
        except preview.PreviewError as error:
            assert expected in str(error), str(error)
        else:
            raise AssertionError('invalid difficulty selection must fail')

    fails('bid', osz_file=archive)
    for bid, title in [(42, 'First'), (43, 'Second')]:
        result = preview.generate_preview(bid, **kwargs)
        assert result['beatmap-info']['meta-data']['title'] == title, result
        assert Path(result['preview-img']).is_file()
    fails('not found', bid=99, osz_file=archive)
    fails('does not match', bid=43, osu_file=local)
    local.write_text(beatmap(99, 'Wrong archive'), encoding='utf-8')
    fails('not found', osu_file=local, osz_file=archive)
    raise SystemExit(0)

if fmt in ('gif', 'mp4'):
    kwargs.update(times='0', duration_time=0.5, fps=10)
if case == 'osu_convert_gif':
    kwargs.update(convert='ctb', mods='hd')
if case == 'osu_gif':
    kwargs['mods'] = 'mr'
if case == 'osz_mp4':
    kwargs['times'] = '0+0.5'
    del kwargs['duration_time']
if case == 'osu_png':
    kwargs['times'] = '0'
    config_file = root / 'config.json'
    config_file.write_text(config, encoding='utf-8')
    kwargs['config'] = config_file

if case in ('osu_gif', 'osz_mp4'):
    result = asyncio.run(preview.generate_preview_async(**kwargs))
else:
    result = preview.generate_preview(**kwargs)
assert result['status'] == 'success', result
expected_title = 'External' if source in ('osu', 'combined') else 'First'
assert result['beatmap-info']['meta-data']['title'] == expected_title, result
output = Path(result['preview-img'])
assert output.is_file() and output.is_relative_to(root/'output'), output
if fmt == 'mp4':
    assert output.read_bytes()[4:8] == b'ftyp'
else:
    with Image.open(output) as image:
        assert image.format == fmt.upper()
        assert image.width > 0 and image.height > 0
        if fmt == 'gif':
            assert image.n_frames == 5
            image.seek(image.n_frames - 1)
            image.load()
"""


@pytest.mark.parametrize(
    "case",
    [
        "osu_png",
        "osu_gif",
        "osu_convert_gif",
        "osz_png",
        "osz_gif",
        "osz_mp4",
        "combined_mp4",
        "difficulty_selection",
    ],
)
def test_uploaded_beatmap_files_render_offline(tmp_path: Path, case: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", RENDER_LOCAL, str(tmp_path), case],
        env={**os.environ, "TEMP": str(tmp_path), "TMP": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
