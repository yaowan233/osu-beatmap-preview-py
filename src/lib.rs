use osu_beatmap_preview_cli::{
    parse_time_point, RenderRequest, ReplayMode, ReplaySource, RequestKind, ScoreSelection,
};
use osu_beatmap_preview_core::processing::validation::TimePoint;
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
    let mut options = RenderRequest::new(bid);
    options.ruleset.convert = convert;
    options.ruleset.mods = mods;
    options.output.format = format;
    options.view.time_points = time_points;
    options.view.duration_seconds = duration_time;
    options.execution.no_cache = no_cache;
    options.output.fps = fps;
    options.execution.config = config;
    options.output.scale = scale;

    render_request_json(py, options)
}

#[allow(clippy::too_many_arguments)]
#[pyfunction]
#[pyo3(signature = (
    osr_file = None,
    *,
    score_id = None,
    user = None,
    bid = None,
    score_select = None,
    mode = None,
    include_fails = false,
    osu_file = None,
    osz_file = None,
    format = None,
    times = None,
    no_cache = false,
    fps = None,
    duration_time = None,
    config = None,
    scale = None,
    output_dir = None,
))]
fn generate_replay_preview_json(
    py: Python<'_>,
    osr_file: Option<String>,
    score_id: Option<String>,
    user: Option<String>,
    bid: Option<String>,
    score_select: Option<String>,
    mode: Option<String>,
    include_fails: bool,
    osu_file: Option<String>,
    osz_file: Option<String>,
    format: Option<String>,
    times: Option<String>,
    no_cache: bool,
    fps: Option<u32>,
    duration_time: Option<f64>,
    config: Option<String>,
    scale: Option<f64>,
    output_dir: Option<String>,
) -> PyResult<String> {
    let source_count = usize::from(osr_file.is_some())
        + usize::from(score_id.is_some())
        + usize::from(user.is_some());
    if source_count != 1 {
        return Err(PyValueError::new_err(
            "specify exactly one replay source: osr_file, score_id, or user",
        ));
    }
    if user.is_none() && (score_select.is_some() || mode.is_some() || include_fails) {
        return Err(PyValueError::new_err(
            "score_select, mode, and include_fails are only valid with user",
        ));
    }

    let mut request = RenderRequest::new(bid.unwrap_or_default());
    let source = match (osr_file, score_id, user) {
        (Some(path), None, None) => ReplaySource::File(path),
        (None, Some(id), None) => ReplaySource::Score(id),
        (None, None, Some(user)) => {
            let default_selection = if request.source.bid.is_empty() {
                "recent"
            } else {
                "best"
            };
            let selection = match score_select.as_deref().unwrap_or(default_selection) {
                "best" => ScoreSelection::Best,
                "recent" => ScoreSelection::Recent,
                _ => return Err(PyValueError::new_err("score_select must be best or recent")),
            };
            ReplaySource::Player {
                user,
                selection,
                mode: parse_replay_mode(mode.as_deref())?,
                include_fails,
            }
        }
        _ => unreachable!("exactly one replay source was checked above"),
    };
    request.kind = RequestKind::Osr { source };
    request.source.osu_file = osu_file;
    request.source.osz_file = osz_file;
    request.output.format = format;
    request.output.fps = fps;
    request.output.scale = scale;
    request.output.output_dir = output_dir;
    request.view.time_points = parse_time_points(times.as_deref())?;
    request.view.duration_seconds = duration_time;
    request.execution.no_cache = no_cache;
    request.execution.config = config;
    render_request_json(py, request)
}

fn parse_replay_mode(mode: Option<&str>) -> PyResult<Option<ReplayMode>> {
    match mode {
        None => Ok(None),
        Some("osu" | "std" | "standard") => Ok(Some(ReplayMode::Osu)),
        Some("taiko") => Ok(Some(ReplayMode::Taiko)),
        Some("fruits" | "fruit" | "ctb" | "catch") => Ok(Some(ReplayMode::Fruits)),
        Some("mania") => Ok(Some(ReplayMode::Mania)),
        Some(_) => Err(PyValueError::new_err(
            "mode must be osu (std, standard), taiko, fruits (fruit, ctb, catch), or mania",
        )),
    }
}

fn render_request_json(py: Python<'_>, request: RenderRequest) -> PyResult<String> {
    let result = py
        .allow_threads(move || osu_beatmap_preview_cli::generate_preview(request))
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
            "render": {"taiko": {"png": {"style": {"SPACING_PER_BPM": gap}}}}
        })
        .to_string(),
    ))
}

#[pymodule]
fn _core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add("PreviewError", module.py().get_type::<PreviewError>())?;
    module.add_function(wrap_pyfunction!(generate_preview_json, module)?)?;
    module.add_function(wrap_pyfunction!(generate_replay_preview_json, module)?)?;
    module.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
