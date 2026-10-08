# Third-party notices

This package links to
[`osu-beatmap-preview`](https://github.com/2710165659/osu-beatmap-preview), distributed under
the MIT License:

> Copyright (c) 2026 xuan_yuan

The core and CLI crates are vendored from upstream main commit
[`0045d40cdf5a0a6b5cfb7da502668b845fcd3024`](https://github.com/2710165659/osu-beatmap-preview/commit/0045d40cdf5a0a6b5cfb7da502668b845fcd3024)
(after v1.4.0), with self-contained build assets and compatibility annotations
for the pinned Rust toolchain. The former rendering patches are included upstream.
Each crate includes its complete MIT license and
an `UPSTREAM.toml` provenance record in its respective `vendor/` directory.

Hidden fade timing follows the MIT-licensed osu!catch implementation:
https://github.com/ppy/osu/blob/master/osu.Game.Rulesets.Catch/Mods/CatchModHidden.cs

The default hyperdash outline colour follows the osu! skinning documentation:
https://github.com/ppy/osu-wiki/blob/master/wiki/Skinning/skin.ini/en.md#catchthebeat
