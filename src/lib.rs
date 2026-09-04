use osu_beatmap_preview_core::{parse_time_point, PreviewOptions, TimePoint};
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
    duration_time = None,
    config = None,
    scale = None,
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
    duration_time: Option<f64>,
    config: Option<String>,
    scale: Option<f64>,
) -> PyResult<String> {
    if bid.trim().is_empty() {
        return Err(PyValueError::new_err("bid must not be empty"));
    }

    if gif_clip || gif_clip_label {
        return Err(PyValueError::new_err(
            "gif_clip and gif_clip_label are no longer supported by the renderer",
        ));
    }

    let mods = parse_mod_tokens(mods.as_deref());
    let mut time_points = parse_time_points(times.as_deref())?;
    let mut duration_time = duration_time;

    if preview_30s {
        if format.as_deref() != Some("mp4") {
            return Err(PyValueError::new_err(
                "preview_30s is only valid for mp4 output",
            ));
        }
        if !time_points.is_empty() || duration_time.is_some() {
            return Err(PyValueError::new_err(
                "preview_30s cannot be combined with times or duration_time",
            ));
        }
        time_points.push(TimePoint::Preview);
        duration_time = Some(30.0);
    } else if format.as_deref() == Some("mp4") && time_points.len() == 2 {
        if duration_time.is_some() {
            return Err(PyValueError::new_err(
                "two-value mp4 times cannot be combined with duration_time",
            ));
        }
        let (TimePoint::Seconds(start), TimePoint::Seconds(end)) = (time_points[0], time_points[1])
        else {
            return Err(PyValueError::new_err(
                "two-value mp4 times must contain numeric seconds",
            ));
        };
        if end <= start {
            return Err(PyValueError::new_err(
                "two-value mp4 times must be in ascending order",
            ));
        }
        time_points.truncate(1);
        duration_time = Some(end - start);
    }

    let config = config_for_gap(config, gap)?;
    let mut options = PreviewOptions::new(bid);
    options.convert = convert;
    options.mods = mods;
    options.format = format;
    options.time_points = time_points;
    options.duration_time = duration_time;
    options.no_cache = no_cache;
    options.fps = fps;
    options.config = config;
    options.scale = scale;

    let result = py
        .allow_threads(move || osu_beatmap_preview_core::generate_preview(options))
        .map_err(|error| PreviewError::new_err(error.to_string()))?;

    serde_json::to_string(&result)
        .map_err(|error| PreviewError::new_err(format!("failed to serialize result: {error}")))
}

fn parse_mod_tokens(mods: Option<&str>) -> Vec<String> {
    mods.map(|value| {
        value
            .split('+')
            .map(str::trim)
            .filter(|token| !token.is_empty())
            .map(str::to_owned)
            .collect()
    })
    .unwrap_or_default()
}

fn parse_time_points(times: Option<&str>) -> PyResult<Vec<TimePoint>> {
    times
        .into_iter()
        .flat_map(|value| value.split('+'))
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(|value| {
            parse_time_point(value).map_err(|error| PyValueError::new_err(error.to_string()))
        })
        .collect()
}

fn config_for_gap(config: Option<String>, gap: Option<f64>) -> PyResult<Option<String>> {
    let Some(gap) = gap else {
        return Ok(config);
    };
    if !gap.is_finite() || gap <= 0.0 || gap >= 500.0 {
        return Err(PyValueError::new_err(
            "gap must be a finite number between 0 and 500",
        ));
    }
    if config.is_some() {
        return Err(PyValueError::new_err(
            "gap cannot be combined with a custom config",
        ));
    }
    Ok(Some(
        serde_json::json!({
            "layout": {"taiko": {"png": {"SPACING_PER_BPM": gap}}}
        })
        .to_string(),
    ))
}

#[pymodule]
fn _core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add("PreviewError", module.py().get_type::<PreviewError>())?;
    module.add_function(wrap_pyfunction!(generate_preview_json, module)?)?;
    module.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
