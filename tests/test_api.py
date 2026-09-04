from __future__ import annotations

import json

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

    assert await preview.generate_preview_async(456, format="png") == {
        "preview-img": "preview.png"
    }


def test_native_extension_uses_updated_version() -> None:
    assert preview.__version__ == "0.1.5"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"format": "gif", "gif_clip": True}, "no longer supported"),
        ({"format": "gif", "times": "NaN"}, "finite"),
        ({"format": "gif", "preview_30s": True}, "mp4"),
        ({"format": "png", "gap": 120.0, "config": "{}"}, "custom config"),
    ],
)
def test_native_argument_compatibility_validation(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        preview.generate_preview(123, **kwargs)
