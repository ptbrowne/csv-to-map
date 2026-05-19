# csv-to-map

Render georeferenced point maps from a CSV file. Supports Mapbox basemaps, per-column colouring, automatic label deconfliction, a distance scale bar, and PNG export.

## Installation

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv add git+https://github.com/ptbrowne/csv-to-map.git
```

This installs the `csv-to-map` command.

---

## Quick start

```bash
csv-to-map init                            # copy the example project to ./example
csv-to-map render example/config.json     # render the example map
csv-to-map schema                         # copy config.schema.json to current directory
```

---

## Commands

### `csv-to-map init`

```
csv-to-map init [directory] [--force]
```

Copies the bundled example project (CSV, bbox GeoJSON, config) into a local directory. Use this as a starting point for your own dataset.

```bash
csv-to-map init              # → ./example/
csv-to-map init my-project   # → ./my-project/
```

### `csv-to-map render`

```
csv-to-map render <config> [--token TOKEN] [--output FILE]
```

| Argument | Description |
|---|---|
| `config` | Path to a JSON config file (see format below) |
| `--token` | Mapbox access token. Overrides `MAPBOX_TOKEN` env var |
| `--output` | Output PNG path. Overrides the `output` field in the config |

### `csv-to-map schema`

```
csv-to-map schema [--force]
```

Copies `config.schema.json` from the installed package into the current directory. Point your config's `$schema` field at it for IDE autocompletion and validation. Use `--force` to overwrite an existing copy.

---

## Mapbox token

Get a free token at <https://account.mapbox.com>. Set it in your environment or in a `.env` file in your working directory:

```
MAPBOX_TOKEN=pk.eyJ1...
```

---

## CSV format

The file must have at minimum a `Latitude` and `Longitude` column (column names are configurable). All other columns are optional and can be used for labels and colouring.

```csv
name,Latitude,Longitude,vegetation
Reykjavík,64.1466,-21.9426,grassland
Akureyri,65.6835,-18.1105,grassland
Vík í Mýrdal,63.4190,-19.0056,lava field
```

---

## Config format

```json
{
  "$schema": "./config.schema.json",
  "csv":    "sites.csv",
  "bbox":   "bbox.json",
  "output": "map.png",

  "lat_col": "Latitude",
  "lon_col": "Longitude",

  "label_col": "name",

  "color_col": "vegetation",
  "color_map": {
    "grassland":  "#4caf7d",
    "lava field": "#7f8c8d",
    "__default__": "#e74c3c"
  },

  "title": "My map",
  "mapbox_style": "outdoors-v12"
}
```

All paths are relative to the config file, so configs and their data can live in any directory.

| Field | Required | Default | Description |
|---|---|---|---|
| `csv` | ✓ | — | CSV file path |
| `bbox` | | `bbox.json` next to CSV | Bounding box GeoJSON |
| `output` | | — | Output PNG path |
| `lat_col` | | `Latitude` | Latitude column name |
| `lon_col` | | `Longitude` | Longitude column name |
| `label_col` | | — | Column for point labels; numeric indices used when absent |
| `color_col` | | — | Column that drives point colour |
| `color_map` | | — | Maps `color_col` values to hex colours; `__default__` is the fallback |
| `title` | | — | Figure title |
| `mapbox_style` | | `outdoors-v12` | Mapbox style ID (`streets-v12`, `satellite-streets-v12`, …) |

---

## Bounding box

The bounding box controls the map extent. The easiest way to create one:

1. Go to **<https://geojson.io>**
2. Use the rectangle tool to draw a box around your area of interest
3. Copy the GeoJSON and save it as `bbox.json` next to your CSV (or point to it with the `bbox` config key)

If no bbox file is found, the map extent falls back to the bounding box of your data points.

---

## Interactive notebook

A [Marimo](https://marimo.io) notebook is included for interactive exploration:

```bash
uv run marimo edit island_map.py
```

The notebook reads the same config file as the CLI and re-renders the map live whenever the config path changes.

---

## Example

A bundled example with 20 Iceland locations is included in the package. Copy it locally with:

```bash
csv-to-map init
csv-to-map render example/config.json
# → example/output.png
```

The example contains:

| File | Description |
|---|---|
| `sites.csv` | 20 named locations across Iceland with vegetation type |
| `bbox.json` | Bounding box covering the whole island |
| `config.json` | Ready-to-run config |
