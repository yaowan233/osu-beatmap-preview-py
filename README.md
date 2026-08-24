# osu-beatmap-preview-py

[`osu-beatmap-preview`](https://github.com/2710165659/osu-beatmap-preview) 的
Python 原生扩展。渲染器通过 PyO3 直接运行在 Python 进程内，不需要下载、配置或启动额外的
可执行文件。

> 当前为早期开发版本。依赖暂时固定到上游首次公开 Rust library API 的 commit；正式发布前，
> 应升级到包含该 API 的稳定上游版本。

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
)
print(result["preview-img"])
```

`generate_preview()` 是同步接口，适合脚本；NoneBot、FastAPI 等异步应用应使用
`generate_preview_async()`，避免阻塞事件循环。

`convert` 仅用于将 osu!standard 谱面转换成 `taiko`、`ctb` 或 `mania`。原生非 standard
谱面不要传入 `convert`。

### 异步取消与并发

上游 Rust API 当前是同步接口，没有提供取消令牌。取消 `generate_preview_async()` 所在的
Python task 不会中止已经开始的原生渲染；Bot 集成时应使用 semaphore 限制并发。若需要真正的
超时中止，应先在上游 library API 增加协作式取消能力。

## 本地开发

```bash
uv sync
uv run maturin develop
uv run pytest
```

## 发布

推送 `v*` tag 后，GitHub Actions 会构建 Windows、Linux 和 macOS wheel，并通过 PyPI
Trusted Publishing 发布。发布前需要：

1. 在 GitHub 创建名为 `pypi` 的 environment；
2. 在 PyPI 为该 GitHub 仓库配置 Trusted Publisher；
3. 确认对应版本已经同时写入 `Cargo.toml` 和 `pyproject.toml`。

## 许可证

本项目采用 MIT License。上游渲染器同样采用 MIT License，版权归其贡献者所有。
