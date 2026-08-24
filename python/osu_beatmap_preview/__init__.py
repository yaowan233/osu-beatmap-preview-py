"""In-process Python bindings for osu-beatmap-preview."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Literal

from ._core import PreviewError, __version__, generate_preview_json

PreviewFormat = Literal["png", "gif", "mp4"]
ConvertMode = Literal["taiko", "ctb", "mania"]

__all__ = [
    "ConvertMode",
    "PreviewError",
    "PreviewFormat",
    "__version__",
    "generate_preview",
    "generate_preview_async",
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
    )
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise PreviewError("renderer returned a non-object JSON value")
    return result


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
    )

