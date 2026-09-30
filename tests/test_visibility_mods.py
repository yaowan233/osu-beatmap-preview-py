from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# 独立进程隔离原生配置，并验证公开 Python API 真的改变动画像素。
RENDER_VISIBILITY = r"""
import json
import sys
from pathlib import Path

import osu_beatmap_preview as preview
from PIL import Image

root, mode, convert, mods = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
cache = root / 'cache' / 'osu-download-cache'
cache.mkdir(parents=True)
objects = (
    '64,192,1000,1,0,0:0:0:0:\n'
    '192,192,1300,128,0,3200:0:0:0:0:\n'
    '320,192,1800,1,0,0:0:0:0:\n'
    '448,192,2200,1,0,0:0:0:0:\n'
    '64,192,2800,1,0,0:0:0:0:\n'
    '320,192,3400,1,0,0:0:0:0:'
    if mode == 3 else
    '80,96,1000,1,0,0:0:0:0:\n'
    '300,220,1300,1,8,0:0:0:0:\n'
    '180,300,1600,2,0,L|350:280,2,170\n'
    '400,80,2200,1,4,0:0:0:0:\n'
    '80,230,2600,1,8,0:0:0:0:\n'
    '320,160,3400,1,0,0:0:0:0:'
)
(cache / '999930001.osu').write_text(
    f'osu file format v14\n\n[General]\nMode:{mode}\nPreviewTime:1000\n'
    '[Metadata]\nTitle:Visibility mods\nArtist:Test\nCreator:Test\nVersion:Test\n'
    '[Difficulty]\nCircleSize:4\nApproachRate:6\nOverallDifficulty:6\n'
    'HPDrainRate:5\nSliderMultiplier:1.4\nSliderTickRate:1\n'
    '[TimingPoints]\n0,500,4,1,0,100,1,0\n750,-50,4,1,0,100,0,0\n'
    f'[HitObjects]\n{objects}\n', encoding='utf-8'
)
target = {'taiko': 1, 'ctb': 2, 'mania': 3}.get(convert, mode)
name = {0: 'standard', 1: 'taiko', 2: 'catch', 3: 'mania'}[target]
structure = {'ROW_COUNT': 1} if target == 1 else {'IMAGES_PER_ROW': 1}
if target in (0, 2):
    structure['ROW_COUNT'] = 1
config = json.dumps({
    'paths': {'CACHE_DIR': cache.parent.as_posix(), 'OUTPUT_DIR': (root / 'output').as_posix(),
              'LOG_DIR': (root / 'logs').as_posix()},
    'render': {name: {'gif': {'SCALE': 0.5, 'structure': structure,
                            'style': {'SHOW_TIME_LABEL': False}}}},
})
baseline = '+'.join(token for token in mods.split('+') if token not in ('hd', 'fl')) or None
frames = []
for selected in (baseline, mods, '+'.join(reversed(mods.split('+')))):
    result = preview.generate_preview(
        999930001, format='gif', convert=convert or None, mods=selected, times='preview',
        duration_time=1, fps=20, config=config
    )
    with Image.open(result['preview-img']) as image:
        assert image.format == 'GIF'
        assert image.n_frames == 20
        pixels = []
        duration = 0
        for index in range(image.n_frames):
            image.seek(index)
            image.load()
            duration += image.info['duration']
            pixels.append(image.convert('RGB').tobytes())
        assert duration == 1000
        frames.append(pixels)
assert frames[0] != frames[1], (mode, convert, mods, 'mod had no visual effect')
assert frames[1] == frames[2], (mode, convert, mods, 'mod order changed pixels')
if target == 3:
    try:
        preview.generate_preview(999930001, format='gif', convert=convert or None,
                                 mods='hd+fl', config=config)
    except preview.PreviewError as error:
        assert 'HD and FL cannot be used together for mania' in str(error)
    else:
        raise AssertionError('mania HD+FL must be rejected')
if target != 0:
    for token in ('hd', 'fl'):
        try:
            preview.generate_preview(999930001, format='png', convert=convert or None,
                                     mods=token, config=config)
        except preview.PreviewError as error:
            assert f'{token.upper()} is not supported' in str(error)
        else:
            raise AssertionError('static chart must reject visibility mods')
"""


@pytest.mark.parametrize(
    "mode,convert,mods",
    [
        (0, "", "fl"),
        (0, "", "hd+fl+hr+dt"),
        (1, "", "hd+hr+sw+cs+dt"),
        (1, "", "fl+ez+ht"),
        (1, "", "hd+fl+cs"),
        (0, "taiko", "hd+fl+hr+sw+dt"),
        (2, "", "fl+ez+ht"),
        (2, "", "hd+fl+hr+dt"),
        (0, "ctb", "hd+fl+dt"),
        (3, "", "hd+cs+ho+ht"),
        (3, "", "fl+cs+in+dt"),
        (0, "mania", "hd+4k+ds+cs+ht"),
        (0, "mania", "fl+4k+ds+in+dt"),
    ],
)
def test_visibility_mods_render_and_compose(
    tmp_path: Path, mode: int, convert: str, mods: str
) -> None:
    result = subprocess.run(
        [sys.executable, "-c", RENDER_VISIBILITY, str(tmp_path), str(mode), convert, mods],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
