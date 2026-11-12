from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import osu_beatmap_preview as preview
import pytest


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({}, "exactly one"),
        ({"osr_file": "a.osr", "score_id": 1}, "exactly one"),
        ({"score_id": 1, "user": "player"}, "exactly one"),
        ({"osr_file": "a.osr", "score_select": "recent"}, "only valid with user"),
        ({"score_id": 1, "mode": "mania"}, "only valid with user"),
        ({"osr_file": "a.osr", "include_fails": True}, "only valid with user"),
        ({"user": "player", "score_select": "pp"}, "score_select must"),
        ({"user": "player", "mode": "invalid"}, "mode must"),
        ({"osr_file": "a.osr", "times": "NaN"}, "finite"),
    ],
)
def test_replay_source_options_are_validated_before_loading(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        preview.generate_replay_preview(**kwargs)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"score_id": 0}, "score-id"),
        ({"user": ""}, "user"),
        ({"user": "player", "score_select": "best"}, "best"),
        ({"user": "player", "bid": 42, "include_fails": True}, "include-fails"),
        ({"osr_file": "a.osr", "bid": 42}, "bid"),
        ({"osr_file": "a.txt"}, "osr"),
        ({"osr_file": "a.osr", "osu_file": "a.txt"}, "osu"),
        ({"osr_file": "a.osr", "format": "webm"}, "fmt"),
        ({"osr_file": "a.osr", "fps": 0}, "fps"),
        ({"osr_file": "a.osr", "duration_time": 0}, "duration time"),
    ],
)
def test_replay_requests_use_upstream_validation(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(preview.PreviewError, match=message):
        preview.generate_replay_preview(**kwargs)


# 每个进程隔离上游配置；合成谱面和回放，确保测试完全离线。
RENDER_REPLAY = r"""
import asyncio
import hashlib
import io
import json
import lzma
import struct
import sys
import wave
import zipfile
from pathlib import Path

import osu_beatmap_preview as preview
from PIL import Image

root, mode, fmt = Path(sys.argv[1]).resolve(), int(sys.argv[2]), sys.argv[3]
osu = (
    'osu file format v14\n[General]\n'
    f'Mode:{mode}\nAudioFilename:audio.wav\nPreviewTime:1000\n'
    '[Metadata]\nTitle:Python replay test\nArtist:Test\nVersion:Test\nBeatmapID:42\n'
    '[Difficulty]\nCircleSize:4\nOverallDifficulty:5\nHPDrainRate:5\n'
    'ApproachRate:5\nSliderMultiplier:1.4\nSliderTickRate:1\n'
    '[TimingPoints]\n0,500,4,1,0,100,1,0\n'
    '[HitObjects]\n100,100,1000,1,0\n200,100,1500,1,0\n'
).encode()
osu_path, osr_path = root / 'map.osu', root / 'play.osr'
osu_path.write_bytes(osu)

def string(value):
    value = value.encode()
    assert len(value) < 128
    return b'\x0b' + bytes([len(value)]) + value if value else b'\x00'

frames = (
    '0|0|0|0,1000|1|0|0,1|0|0|0,499|2|0|0,1|0|0|0,999|0|0|0,'
    if mode == 3 else
    '0|100|100|0,1000|100|100|1,1|100|100|0,499|200|100|1,'
    '1|200|100|0,999|200|100|0,'
) + '-12345|0|0|1,'
compressed = lzma.compress(frames.encode(), format=lzma.FORMAT_ALONE)
osr_path.write_bytes(
    struct.pack('<Bi', mode, 20200101)
    + string(hashlib.md5(osu).hexdigest()) + string('Python test') + string('')
    + struct.pack('<6HiHBi', 2, 0, 0, 0, 0, 0, 200, 2, 1, 0)
    + string('') + struct.pack('<qi', 0, len(compressed))
    + compressed + struct.pack('<q', 0)
)
name = {0: 'standard', 1: 'taiko', 2: 'catch', 3: 'mania'}[mode]
config = json.dumps({
    'paths': {'CACHE_DIR': str(root / 'cache'), 'LOG_DIR': str(root / 'logs')},
    'render': {name: {'gif': {'structure': {'ROW_COUNT': 1, 'IMAGES_PER_ROW': 1}}}},
})
kwargs = dict(osu_file=osu_path, format=fmt, times='0', config=config,
              scale=0.25, output_dir=root / 'output')
if mode == 1 and fmt == 'png':
    config_file = root / 'config.json'
    config_file.write_text(config, encoding='utf-8')
    kwargs['config'] = config_file
if fmt in ('gif', 'mp4'):
    kwargs.update(fps=10, duration_time=0.5)
elif mode != 0:
    kwargs['duration_time'] = 0.5
if fmt == 'mp4':
    audio = io.BytesIO()
    with wave.open(audio, 'wb') as wav:
        wav.setparams((2, 2, 8000, 0, 'NONE', 'not compressed'))
        wav.writeframes(bytes(4 * 8000 * 4))
    archive = root / 'map.osz'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('map.osu', osu)
        z.writestr('audio.wav', audio.getvalue())
    kwargs['osz_file'] = archive

if mode == 3:
    result = asyncio.run(preview.generate_replay_preview_async(osr_path, **kwargs))
else:
    result = preview.generate_replay_preview(osr_path, **kwargs)
assert result['status'] == 'success', result
assert result['replay-info']['rulesetId'] == mode, result
assert result['replay-info']['player'] == 'Python test', result
state = result['replay-info']['state']
assert state['score'].endswith('/200'), state
assert state['max_combo'].endswith('/2'), state
assert state['statistics']['great'].endswith('/2'), state
assert state['accuracy'].endswith('/-') and state['rank'].endswith('/-'), state
assert result['replay-info']['cache-hit'] is False, result
output = Path(result['preview-img'])
assert output.is_file() and output.is_relative_to(root / 'output'), output
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
cached = preview.generate_replay_preview(osr_path, **kwargs)
assert cached['replay-info']['cache-hit'] is True, cached
if mode == 0 and fmt == 'png':
    fresh = preview.generate_replay_preview(osr_path, no_cache=True, **kwargs)
    assert fresh['replay-info']['cache-hit'] is False, fresh
    osu_path.write_bytes(osu + b'\n')
    try:
        preview.generate_replay_preview(osr_path, **kwargs)
    except preview.PreviewError as error:
        assert 'MD5' in str(error) or 'checksum' in str(error), str(error)
    else:
        raise AssertionError('mismatched beatmap must fail before a network fallback')
"""


@pytest.mark.parametrize("mode", [0, 1, 2, 3])
@pytest.mark.parametrize("format", ["png", "gif", "mp4"])
def test_local_replay_renders_offline(tmp_path: Path, mode: int, format: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", RENDER_REPLAY, str(tmp_path), str(mode), format],
        env={**os.environ, "TEMP": str(tmp_path), "TMP": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_online_sources_and_player_defaults_reach_authentication(tmp_path: Path) -> None:
    script = """
import json
import sys
from pathlib import Path
import osu_beatmap_preview as preview

root = Path(sys.argv[1])
config = json.dumps({
    'paths': {'LOG_DIR': str(root / 'logs'), 'CACHE_DIR': str(root / 'cache')},
    'download': {'auth': {'OSU_CLIENT_ID': '', 'OSU_CLIENT_SECRET': ''}},
})
for source in [
    {'score_id': 1},
    {'user': 1},
    {'user': 'player', 'bid': 42},
    {'user': 'player', 'score_select': 'recent', 'mode': 'ctb', 'include_fails': True},
]:
    try:
        preview.generate_replay_preview(config=config, **source)
    except preview.PreviewError as error:
        assert 'OSU_API_TOKEN' in str(error), str(error)
    else:
        raise AssertionError('online replay requests must require credentials')
"""
    env = {key: value for key, value in os.environ.items() if not key.startswith("OSU_")}
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
