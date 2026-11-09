# osu-beatmap-preview-py

[`osu-beatmap-preview`](https://github.com/2710165659/osu-beatmap-preview) 的
Python 原生扩展。渲染器通过 PyO3 直接运行在 Python 进程内，不需要下载、配置或启动额外的
可执行文件。

> 当前为早期开发版本。0.1.14 使用上游 v1.5.7 的固定提交
> [`a4c24e0`](https://github.com/2710165659/osu-beatmap-preview/commit/a4c24e0e447e249a2ea28cd03bc772719771257c)。
> core、CLI 和构建资源随仓库分发，确保各平台 wheel 使用相同的渲染行为。

## 安装

```bash
pip install osu-beatmap-preview-py
```

PyPI 发布后，pip 会为受支持的平台安装预编译 wheel，不要求用户安装 Rust。没有预编译 wheel
的平台从源码安装时仍需要 Rust 和 C++ 工具链。

## 使用

```python
from osu_beatmap_preview import generate_preview_async

result = await generate_preview_async(
    4498112,
    format="gif",
    mods="hd+hr",
    times="preview+60",
    duration_time=8,
    fps=30,
    scale=1.5,
)
print(result["preview-img"])
```

`generate_preview()` 是同步接口，适合脚本；NoneBot、FastAPI 等异步应用应使用
`generate_preview_async()`，避免阻塞事件循环。

`convert` 仅用于将 osu!standard 谱面转换成 `taiko`、`ctb` 或 `mania`。原生非 standard
谱面不要传入 `convert`。

`times` 使用 `+` 分隔多个秒数，也支持 `preview`；`duration_time` 控制 GIF 片段或 MP4
区间时长。`config` 可传配置文件路径或内联 JSON/YAML，`scale` 用于临时覆盖输出倍率。

### 用户上传的 `.osu` / `.osz`

Bot 先将上传附件保存到本地，再把文件路径传给现有的 `generate_preview()` 或
`generate_preview_async()`，无需上传到 osu! 或提供 API 凭据。路径参数接受字符串或 `pathlib.Path`，
原来的 `generate_preview_async(bid, ...)` 调用保持兼容。

```python
from pathlib import Path
from osu_beatmap_preview import generate_preview_async

result = await generate_preview_async(
    osu_file=Path("uploads/map.osu"),
    format="gif",
    times="0",
    duration_time=5,
    output_dir=Path("outputs/job-123"),
)
print(result["preview-img"])

# 单难度谱面包可省略 bid；多难度包用 bid 选择对应 BeatmapID。
result = await generate_preview_async(
    osz_file=Path("uploads/map.osz"),
    bid=4498112,
    format="mp4",
    times="0",
    duration_time=5,
    output_dir=Path("outputs/job-124"),
)
```

单独的 `.osu` 支持 PNG/GIF，也接受没有有效 BeatmapID 的本地谱面；MP4 需要 `.osz` 中的音频等
媒体资源。只有一个顶层 `.osu` 的 `.osz` 可省略 bid，多难度包必须提供 bid，按有效 BeatmapID
选择难度。传入 bid 与外部 `.osu` 的 ID 不一致时会报错。

也可同时提供 `osu_file` 和 `osz_file`：外部 `.osu` 用于渲染，`.osz` 提供媒体资源，包内必须有
相同 BeatmapID 的难度。`convert`、`mods`、时间区间、帧率、配置、缩放和缓存参数继续可用，
返回结构仍为 `preview-img` 与 `beatmap-info`。`output_dir` 可为每次 Bot 任务指定输出目录，
`config` 也支持 `pathlib.Path`。

### 回放预览

`generate_replay_preview()` 和 `generate_replay_preview_async()` 支持 Standard、Taiko、Catch、
Mania 的 PNG、GIF、MP4 回放预览。三种来源 `osr_file`、`score_id`、`user` 必须且只能选一种；
游戏模式和模组从回放读取，不传 `convert` 或 `mods`。

本地 PNG/GIF 只需 `.osr` 和与回放 MD5 匹配的原始 `.osu`，无需联网：

```python
from pathlib import Path
from osu_beatmap_preview import generate_replay_preview_async

result = await generate_replay_preview_async(
    Path("play.osr"),
    osu_file=Path("map.osu"),
    format="gif",
    times="0",
    duration_time=5,
    fps=30,
    output_dir=Path("previews"),
)
print(result["preview-img"])
print(result["replay-info"])  # 玩家、模式、判定状态、回放身份及缓存信息
```

MP4 还需要包含对应谱面与音频的 `.osz`，通过 `osz_file="map.osz"` 提供。
缺少本地资源时，上游会通过官方 API 查找并下载；PNG/GIF 不会从 `.osz` 提取谱面，离线使用时
需显式提供 `osu_file`。谱面 MD5 不匹配会立即报错，不会改用其他谱面。

在线来源示例：

```python
result = await generate_replay_preview_async(score_id=6086051920, format="png")
result = await generate_replay_preview_async(user="player", bid=4498112, format="gif")
result = await generate_replay_preview_async(
    user="player", score_select="recent", mode="mania", include_fails=True,
)
```

在线查询和资源下载需要环境变量 `OSU_API_TOKEN`，或 `OSU_CLIENT_ID` 与 `OSU_CLIENT_SECRET`；
OAuth 凭据也可通过 `config` 中的 `download.auth` 配置。目标成绩必须有可访问的回放。
玩家查询提供 `bid` 时默认取该难度最高分，不提供时默认取最近一次完成的成绩；
`score_select` 可选 `best`、`recent`，`best` 要求 `bid`。`mode`、`score_select` 和
`include_fails` 仅适用于 `user`，其中 `include_fails` 仅适用于 `recent`。
查询模式可用 `osu`、`taiko`、`fruits`、`mania`，也接受 `std`、`standard`、`fruit`、`ctb`、`catch`。

不指定 `format` 时，Standard 默认 GIF，其余模式默认 PNG。`times` 是相对于首个物件的秒数，
也支持 `preview`；GIF 和 Standard PNG 可通过 `+` 提供多个采样起点。
Taiko/Catch/Mania PNG 默认显示整谱判定概览，截取区间时必须同时提供一个 `times` 起点和
`duration_time`。MP4 只接受一个起点，`duration_time` 指定时长，省略起点及时长时导出完整回放。
输出沿用 `preview-img` 字段，
另有 `replay-info` 和 `beatmap-info`；`no_cache=True` 可跳过缓存。

### CTB GIF 模组

原生 CTB 和 standard 转 CTB 的 GIF 支持 `hd`、`ez`、`hr`、`dt`、`ht`。
HD 会让水果、水滴及香蕉在到达判定线前渐隐；支持 `hd+ez`、`hd+hr`、`hd+dt`、`hd+ht`。
`ez+hr` 和 `dt+ht` 是互斥组合。PNG 静态图支持 EZ、HR，不支持 HD、DT、HT。
Hyperdash（红果）的外圈默认使用红色 `#FF0000`，可通过 `skin.HYPER_DASH` 配置 RGB 颜色；
水果本体继续使用谱面 Combo 颜色，HD 渐隐同时作用于本体、白边和红圈。

```python
result = await generate_preview_async(
    3994408,
    format="gif",
    mods="hd+dt",
    times="preview",
    duration_time=3,
    fps=20,
)
```

### 四种模式的 GIF / MP4 模组

| 模式 | 支持的模组 |
| --- | --- |
| Standard | `EZ`、`HR`、`HD`、`FL`、`MR`、`TC`、`DA`、`DT`、`HT`、`NC`、`DC` |
| Taiko | `EZ`、`HR`、`HD`、`FL`、`SW`、`CS`、`DT`、`HT`、`NC`、`DC` |
| Catch | `EZ`、`HR`、`HD`、`FL`、`DT`、`HT`、`NC`、`DC` |
| Mania | `HD`、`FL`、`1K`–`10K`、`DS`、`IN`、`HO`、`MR`、`CS`、`DT`、`HT`、`NC`、`DC` |

组合中的每个模组都必须受当前模式支持；Mania 的 `HD+FL` 互斥，其余三种模式可组合使用。
`HD+TC`、`IN+HO`、`EZ+HR`、`DT+HT` 互斥；mania 的键数模组和 DS 只影响 standard 转谱。
GIF 和 MP4 使用相同的模组支持规则，GIF 在 15、30、60 fps 下也会保持请求的播放时长。

`DT`/`HT` 的 MP4 音乐保调变速，可用 `dt1.25`、`ht0.9` 指定倍速；`NC`/`DC` 默认以
1.5x / 0.75x 播放，也可指定倍速，音乐音高倍率固定为 1.5 / 0.75，`NC` 还叠加节拍鼓点。
速度模组不能混用。
`AT` 已移除。Standard 通过 `render.standard.<format>.style.SHOW_CURSOR` 显示自动光标；
Catch 的 GIF / MP4 通过 `render.catch.<format>.style.SHOW_CATCHER` 显示自动接盘。
太鼓 GIF / MP4 默认显示击打按键和音符击飞效果，可通过 `SHOW_KEY_OVERLAY`、`SHOW_HIT_EFFECTS` 控制。
自定义配置请以 [当前上游配置](vendor/osu-beatmap-preview-core/assets/shared_config.yml) 为准，旧版部分排版、配色字段已移除。
太鼓 PNG 转盘显示总击打数与时长，GIF 和 MP4 显示完整空心转盘、剩余击打数及完成淡出。
四模式 MP4 可通过
`render.<mode>.mp4.style.ENABLE_STORYBOARD` 和 `ENABLE_BACKGROUND_VIDEO` 启用故事板及背景视频，
两项默认关闭；`<mode>` 为 `standard`、`taiko`、`catch` 或 `mania`。

Taiko HD 隐藏普通音符和连打刻度，保留连打条与气球；Mania HD 让音符头、长按主体
在判定线附近渐隐，遮罩随连击扩大。HD 不会遮住 Mania 判定线、键道背景或 SV 提示。
Catch HD 在 Kiai 区段持续保留淡淡的物件轮廓，不随 BPM 闪烁；区段结束后恢复普通 HD。
圆形预览样式暂用约 30% 不透明度近似轮廓亮度，不逐像素复刻皮肤的 lighting 纹理。

FL 在 Standard 跟随自动光标（滑条期间额外暗化），在 Catch 跟随接盘，在 Taiko 固定于判定区；
Mania FL 只保留中部横向可视带。Standard、Taiko、Catch 在 100/200 combo 时缩小光圈。
谱面预览的轨迹用谱面物件之间的插值估算，连击按无 miss 进度计算；
Standard 的光圈跟随延迟使用连续阻尼近似，Catch 香蕉雨期间沿用相邻水果的插值路线。
Taiko、Catch、Mania 的 PNG 是静态概览，不支持 HD/FL；Standard 的 PNG 快照支持二者。

### 异步取消与并发

上游 Rust API 当前是同步接口，没有提供取消令牌。取消 `generate_preview_async()` 或
`generate_replay_preview_async()` 所在的
Python task 不会中止已经开始的原生渲染；Bot 集成时应使用 semaphore 限制并发。若需要真正的
超时中止，应先在上游 library API 增加协作式取消能力。

## 本地开发

```bash
uv sync
uv run maturin develop
uv run pytest
cargo test -p osu-beatmap-preview-core -p osu-beatmap-preview-cli
```

## 发布

推送 `v*` tag 后，GitHub Actions 会构建 Windows、Linux 和 macOS wheel，并通过 PyPI
Trusted Publishing 发布。发布前需要：

1. 在 GitHub 创建名为 `pypi` 的 environment；
2. 在 PyPI 为该 GitHub 仓库配置 Trusted Publisher；
3. 确认对应版本已经同时写入 `Cargo.toml` 和 `pyproject.toml`。

## 许可证

本项目采用 MIT License。上游渲染器同样采用 MIT License，版权归其贡献者所有。
