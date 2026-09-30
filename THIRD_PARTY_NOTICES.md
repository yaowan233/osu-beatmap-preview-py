# Third-party notices

This package links to
[`osu-beatmap-preview`](https://github.com/2710165659/osu-beatmap-preview), distributed under
the MIT License:

> Copyright (c) 2026 xuan_yuan

The core and CLI crates are vendored from commit `73b4b9c0ce4d125e614eb38f106e2d0d80a9cb0c`
with CTB Hidden rendering, corrected default hyperdash outline colours, and
self-contained build assets. Each crate includes its complete MIT license and
an `UPSTREAM.toml` provenance record in its respective `vendor/` directory.

Hidden fade timing follows the MIT-licensed osu!catch implementation:
https://github.com/ppy/osu/blob/master/osu.Game.Rulesets.Catch/Mods/CatchModHidden.cs

The default hyperdash outline colour follows the osu! skinning documentation:
https://github.com/ppy/osu-wiki/blob/master/wiki/Skinning/skin.ini/en.md#catchthebeat
