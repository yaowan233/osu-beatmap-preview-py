use osu_beatmap_preview_core::PreviewOptions;
use pyo3::create_exception;
use pyo3::exceptions::{PyException, PyValueError};
use pyo3::prelude::*;

create_exception!(_core, PreviewError, PyException);

#[allow(clippy::too_many_arguments)]
#[pyfunction]
#[pyo3(signature = (
    bid,
    *,
    format = None,
    convert = None,
    mods = None,
    times = None,
    gif_clip = false,
    gif_clip_label = false,
    preview_30s = false,
    gap = None,
    no_cache = false,
    fps = None,
))]
fn generate_preview_json(
    py: Python<'_>,
    bid: String,
    format: Option<String>,
    convert: Option<String>,
    mods: Option<String>,
    times: Option<String>,
    gif_clip: bool,
    gif_clip_label: bool,
    preview_30s: bool,
    gap: Option<f64>,
    no_cache: bool,
    fps: Option<u32>,
) -> PyResult<String> {
    if bid.trim().is_empty() {
        return Err(PyValueError::new_err("bid must not be empty"));
    }

    let options = PreviewOptions {
        bid,
        convert,
        mods,
        format,
        times,
        gif_clip,
        gif_clip_label,
        preview_30s,
        gap,
        no_cache,
        fps,
    };

    let result = py
        .allow_threads(move || osu_beatmap_preview_core::generate_preview(options))
        .map_err(|error| PreviewError::new_err(error.to_string()))?;

    serde_json::to_string(&result)
        .map_err(|error| PreviewError::new_err(format!("failed to serialize result: {error}")))
}

#[pymodule]
fn _core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add("PreviewError", module.py().get_type::<PreviewError>())?;
    module.add_function(wrap_pyfunction!(generate_preview_json, module)?)?;
    module.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
