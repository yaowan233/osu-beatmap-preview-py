from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# 原生配置在进程中只初始化一次，每个场景用独立进程验证完整的 Python 到 GIF 链路。
RENDER_TIMING = """
import json
import sys
from pathlib import Path

import osu_beatmap_preview as preview
from PIL import Image

root, mode, mods, fps = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
cache = root / 'cache' / 'osu-download-cache'
cache.mkdir(parents=True)
objects = (
    '64,192,1000,1,0,0:0:0:0:\\n'
    '192,192,1250,128,0,1900:0:0:0:0:\\n'
    '64,192,1750,1,0,0:0:0:0:\\n'
    '192,192,2250,1,0,0:0:0:0:\\n'
    '64,192,2750,1,0,0:0:0:0:\\n'
    '192,192,3250,1,0,0:0:0:0:'
    if mode == 3 else
    '128,96,1000,1,0,0:0:0:0:\\n'
    '300,220,1250,1,8,0:0:0:0:\\n'
    '180,300,1500,2,0,L|350:280,1,140\\n'
    '400,80,1750,1,0,0:0:0:0:\\n'
    '80,230,2000,1,8,0:0:0:0:\\n'
    '320,160,2500,1,0,0:0:0:0:'
)
(cache / '999920001.osu').write_text(
    f'osu file format v14\\n\\n[General]\\nMode:{mode}\\nPreviewTime:1000\\n'
    '[Metadata]\\nTitle:Timing regression\\nArtist:Test\\nCreator:Test\\nVersion:Test\\n'
    '[Difficulty]\\nCircleSize:4\\nApproachRate:6\\nOverallDifficulty:6\\n'
    'HPDrainRate:5\\nSliderMultiplier:1.4\\nSliderTickRate:1\\n'
    '[TimingPoints]\\n0,500,4,1,0,100,1,0\\n750,-50,4,1,0,100,0,0\\n'
    f'[HitObjects]\\n{objects}\\n', encoding='utf-8'
)
name = {0: 'standard', 1: 'taiko', 3: 'mania'}[mode]
structure = {'ROW_COUNT': 1} if mode == 1 else {'IMAGES_PER_ROW': 1}
if mode == 0:
    structure['ROW_COUNT'] = 1
config = json.dumps({
    'paths': {'CACHE_DIR': cache.parent.as_posix(), 'OUTPUT_DIR': (root / 'output').as_posix(),
              'LOG_DIR': (root / 'logs').as_posix()},
    'render': {name: {'gif': {'SCALE': 0.5, 'structure': structure,
                            'style': {'SHOW_TIME_LABEL': False}}}},
})
result = preview.generate_preview(
    999920001, format='gif', mods=mods, times='preview', duration_time=1, fps=fps, config=config
)
with Image.open(result['preview-img']) as image:
    assert image.format == 'GIF'
    assert image.n_frames == fps
    elapsed = 0
    for index in range(image.n_frames):
        image.seek(index)
        image.load()
        elapsed += image.info['duration']
        expected = (index + 1) * 1000 / fps
        assert abs(elapsed - expected) <= 5.01, (mode, mods, fps, index, elapsed, expected)
    assert elapsed == 1000, (mode, mods, fps, elapsed)
"""


@pytest.mark.parametrize(
    "mode,mods",
    [
        (0, "hd+hr+dt"),
        (1, "sw+hr+cs+dt"),
        (3, "in+cs+ht"),
        (0, "at+nc"),
        (1, "hd+dc"),
        (3, "fl+nc"),
    ],
)
@pytest.mark.parametrize("fps", [15, 30, 60])
def test_mod_combinations_preserve_gif_playback_duration(
    tmp_path: Path, mode: int, mods: str, fps: int
) -> None:
    result = subprocess.run(
        [sys.executable, "-c", RENDER_TIMING, str(tmp_path), str(mode), mods, str(fps)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
