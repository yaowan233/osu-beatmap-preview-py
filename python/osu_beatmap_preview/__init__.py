"""In-process Python bindings for osu-beatmap-preview."""

from __future__ import annotations

import asyncio
import json
from os import PathLike, fspath
from typing import Any, Literal

from ._core import (
    PreviewError,
    __version__,
    generate_preview_json,
    generate_replay_preview_json,
)

PreviewFormat = Literal["png", "gif", "mp4"]
ConvertMode = Literal["taiko", "ctb", "mania"]
ReplayMode = Literal["osu", "std", "standard", "taiko", "fruits", "fruit", "ctb", "catch", "mania"]
ScoreSelection = Literal["best", "recent"]

__all__ = [
    "ConvertMode",
    "PreviewError",
    "PreviewFormat",
    "ReplayMode",
    "ScoreSelection",
    "__version__",
    "generate_preview",
    "generate_preview_async",
    "generate_replay_preview",
    "generate_replay_preview_async",
]


def generate_preview(
    bid: int | str,
    *,
    format: PreviewFormat | None = None,
    convert: ConvertMode | None = None,
    mods: str | None = None,
    times: str | None = None,
    gif_clip: bool = False,
    gif_clip_label: bool = False,
    preview_30s: bool = False,
    gap: float | None = None,
    no_cache: bool = False,
    fps: int | None = None,
    duration_time: float | None = None,
    config: str | None = None,
    scale: float | None = None,
) -> dict[str, Any]:
    """Render a beatmap preview and return the renderer result.

    This function performs network and CPU-heavy work. Async applications should
    call :func:`generate_preview_async` instead.
    """
    raw = generate_preview_json(
        str(bid),
        format=format,
        convert=convert,
        mods=mods,
        times=times,
        gif_clip=gif_clip,
        gif_clip_label=gif_clip_label,
        preview_30s=preview_30s,
        gap=gap,
        no_cache=no_cache,
        fps=fps,
        duration_time=duration_time,
        config=config,
        scale=scale,
    )
    return _decode_result(raw)


async def generate_preview_async(
    bid: int | str,
    *,
    format: PreviewFormat | None = None,
    convert: ConvertMode | None = None,
    mods: str | None = None,
    times: str | None = None,
    gif_clip: bool = False,
    gif_clip_label: bool = False,
    preview_30s: bool = False,
    gap: float | None = None,
    no_cache: bool = False,
    fps: int | None = None,
    duration_time: float | None = None,
    config: str | None = None,
    scale: float | None = None,
) -> dict[str, Any]:
    """Render without blocking the caller's asyncio event loop."""
    return await asyncio.to_thread(
        generate_preview,
        bid,
        format=format,
        convert=convert,
        mods=mods,
        times=times,
        gif_clip=gif_clip,
        gif_clip_label=gif_clip_label,
        preview_30s=preview_30s,
        gap=gap,
        no_cache=no_cache,
        fps=fps,
        duration_time=duration_time,
        config=config,
        scale=scale,
    )


def generate_replay_preview(
    osr_file: str | PathLike[str] | None = None,
    *,
    score_id: int | str | None = None,
    user: int | str | None = None,
    bid: int | str | None = None,
    score_select: ScoreSelection | None = None,
    mode: ReplayMode | None = None,
    include_fails: bool = False,
    osu_file: str | PathLike[str] | None = None,
    osz_file: str | PathLike[str] | None = None,
    format: PreviewFormat | None = None,
    times: str | None = None,
    no_cache: bool = False,
    fps: int | None = None,
    duration_time: float | None = None,
    config: str | PathLike[str] | None = None,
    scale: float | None = None,
    output_dir: str | PathLike[str] | None = None,
) -> dict[str, Any]:
    """Render a replay from exactly one of osr_file, score_id, or user.

    Local PNG/GIF rendering needs a matching osu_file. MP4 also needs an osz_file
    containing the beatmap and audio. Missing resources and online replay sources
    use the upstream official API and require osu! credentials.

    Player queries default to best on bid, or recent when bid is omitted. mode,
    score_select, and include_fails apply only to player queries. Ruleset and mods
    come from the replay. MP4 accepts one start time and duration_time in seconds.
    Taiko/Catch/Mania PNG accepts either no range or both times and duration_time.
    """
    raw = generate_replay_preview_json(
        fspath(osr_file) if osr_file is not None else None,
        score_id=str(score_id) if score_id is not None else None,
        user=str(user) if user is not None else None,
        bid=str(bid) if bid is not None else None,
        score_select=score_select,
        mode=mode,
        include_fails=include_fails,
        osu_file=fspath(osu_file) if osu_file is not None else None,
        osz_file=fspath(osz_file) if osz_file is not None else None,
        format=format,
        times=times,
        no_cache=no_cache,
        fps=fps,
        duration_time=duration_time,
        config=fspath(config) if config is not None else None,
        scale=scale,
        output_dir=fspath(output_dir) if output_dir is not None else None,
    )
    return _decode_result(raw)


async def generate_replay_preview_async(
    osr_file: str | PathLike[str] | None = None,
    *,
    score_id: int | str | None = None,
    user: int | str | None = None,
    bid: int | str | None = None,
    score_select: ScoreSelection | None = None,
    mode: ReplayMode | None = None,
    include_fails: bool = False,
    osu_file: str | PathLike[str] | None = None,
    osz_file: str | PathLike[str] | None = None,
    format: PreviewFormat | None = None,
    times: str | None = None,
    no_cache: bool = False,
    fps: int | None = None,
    duration_time: float | None = None,
    config: str | PathLike[str] | None = None,
    scale: float | None = None,
    output_dir: str | PathLike[str] | None = None,
) -> dict[str, Any]:
    """Render a replay without blocking the caller's asyncio event loop.

    Cancelling the await does not stop native rendering already in progress.
    """
    return await asyncio.to_thread(
        generate_replay_preview,
        osr_file,
        score_id=score_id,
        user=user,
        bid=bid,
        score_select=score_select,
        mode=mode,
        include_fails=include_fails,
        osu_file=osu_file,
        osz_file=osz_file,
        format=format,
        times=times,
        no_cache=no_cache,
        fps=fps,
        duration_time=duration_time,
        config=config,
        scale=scale,
        output_dir=output_dir,
    )


def _decode_result(raw: str) -> dict[str, Any]:
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise PreviewError("renderer returned a non-object JSON value")
    return result
