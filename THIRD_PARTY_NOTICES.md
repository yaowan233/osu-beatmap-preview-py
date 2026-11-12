# Third-party notices

This package links to
[`osu-beatmap-preview`](https://github.com/2710165659/osu-beatmap-preview), distributed under
the MIT License:

> Copyright (c) 2026 xuan_yuan

The core and CLI crates are vendored from upstream v1.6.0
[`d42e1ffcb59678314cd0422b1ce8fdc02875d988`](https://github.com/2710165659/osu-beatmap-preview/commit/d42e1ffcb59678314cd0422b1ce8fdc02875d988),
with self-contained build assets and compatibility annotations
for the pinned Rust toolchain. The former rendering patches are included upstream.
Each crate includes its complete MIT license and
an `UPSTREAM.toml` provenance record in its respective `vendor/` directory.

Hidden fade timing follows the MIT-licensed osu!catch implementation:
https://github.com/ppy/osu/blob/master/osu.Game.Rulesets.Catch/Mods/CatchModHidden.cs

The default hyperdash outline colour follows the osu! skinning documentation:
https://github.com/ppy/osu-wiki/blob/master/wiki/Skinning/skin.ini/en.md#catchthebeat

Replay HUD assets retain their upstream licensing terms:

- Torus Bold font and atlas from ppy osu-resources: the original [licence notice](vendor/osu-beatmap-preview-core/assets/fonts/argon/LICENCE) states that distribution requires a commercial licence.
- Replay fallback sounds by ppy Pty Ltd (`combobreak.wav`, `failsound.wav`): [CC BY-NC 4.0](vendor/osu-beatmap-preview-core/assets/hitsound/replay/LICENCE.md).

The package's MIT licence does not replace these asset licences.
