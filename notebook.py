import marimo

__generated_with = "0.23.6"
app = marimo.App(width="full")


@app.cell
def _():
    import os
    import marimo as mo
    from csv_to_map.utils import load_config, load_data, load_env, render_map

    load_env()

    return load_config, load_data, mo, os, render_map


@app.cell
def _(mo):
    _cli = mo.cli_args().get("config", "")
    config_path_input = mo.ui.text(
        value=_cli or "iceland_config.json",
        label="Config file",
        full_width=True,
    )
    config_path_input
    return (config_path_input,)


@app.cell
def _(config_path_input, load_config, mo):
    try:
        cfg = load_config(config_path_input.value.strip())
    except (FileNotFoundError, ValueError) as _e:
        mo.stop(True, mo.callout(mo.md(str(_e)), kind="danger"))
    cfg
    return (cfg,)


@app.cell
def _(cfg, load_data, mo):
    try:
        gdf, map_bounds = load_data(cfg)
    except FileNotFoundError as _e:
        mo.stop(True, mo.callout(mo.md(str(_e)), kind="danger"))
    return gdf, map_bounds


@app.cell
def _(mo, os):
    mapbox_token = mo.ui.text(
        value=os.environ.get("MAPBOX_TOKEN", ""),
        placeholder="pk.eyJ1...",
        label="Mapbox access token",
        kind="password",
    )
    mapbox_token
    return (mapbox_token,)


@app.cell(hide_code=True)
def _(cfg, gdf, map_bounds, mapbox_token, render_map):
    render_map(gdf, map_bounds, cfg, mapbox_token.value.strip())


if __name__ == "__main__":
    app.run()
